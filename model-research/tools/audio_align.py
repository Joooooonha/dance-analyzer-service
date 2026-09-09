# tools/audio_align.py
"""오디오로 두 영상의 전역 시간 오프셋을 추정한다.

춤은 음악에 맞춰 추므로, 같은 곡이면 **오디오만으로 "기준 12.3초 = 사용자 3.7초"를
확정**할 수 있다. 그러면 DTW는 그 위에서 미세한 타이밍 차이만 다루면 되므로 탐색
공간이 크게 줄고 정렬 실패 가능성도 낮아진다.

**원파형이 아니라 온셋 포락선을 쓴다.** 두 영상은 따로 촬영되어 마이크·거리·잔향이
다르므로 파형 자체는 잘 맞지 않는다. 반면 "소리가 커지는 순간"(에너지의 양의 변화)은
녹음 조건이 달라도 같은 시점에 나타난다. 박자 정렬에서 쓰는 표준적인 방법이다.

**항상 켜면 안 된다.** 오디오가 없거나, 다른 곡이거나, 무음이면 오프셋이 무의미하다.
그래서 상관 피크의 뚜렷함을 신뢰도로 계산해 임계 미만이면 "사용 불가"를 반환한다.
호출 측은 실패 시 조용히 DTW 단독 경로로 떨어지면 된다.

실행 (프로젝트 루트에서):

    python -m tools.audio_align --a data/videos/real/pro_dancer.mp4 \
                                --b data/videos/real/user_dancer.mp4
"""
import argparse
import json
import subprocess

import numpy as np

SR = 22050          # 온셋 포락선에는 이 정도면 충분
HOP = 256           # 포락선 프레임 간격 → 약 86 fps
WIN = 1024
MIN_CONFIDENCE = 3.0    # 피크가 배경 대비 몇 σ 위여야 하는지
MIN_PEAK = 0.30         # 피크 상관값 자체의 하한
MAX_OFFSET_FRAC = 0.30  # 짧은 쪽 길이의 이 비율을 넘는 오프셋은 후보에서 제외

# 왜 두 기준을 같이 쓰는가 (실측 근거):
#   같은 오디오면 피크가 1.0000까지 올라간다. 반면 서로 다른 영상끼리도
#   **끝단 lag(겹침이 최소인 지점)** 에서 0.48~0.53의 허위 피크가 생기고,
#   z-score만 보면 9~10으로 나와 임계 3.0을 통과해버린다.
#   → 오프셋 범위를 제한하고 피크값 하한을 두어야 걸러진다.


def has_audio(path: str) -> bool:
    r = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'a',
         '-show_entries', 'stream=codec_name', '-of', 'csv=p=0', path],
        capture_output=True, text=True)
    return bool(r.stdout.strip())


def load_audio(path: str, sr: int = SR) -> np.ndarray:
    """ffmpeg으로 모노 float32 PCM을 뽑는다."""
    r = subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', path,
         '-f', 'f32le', '-ac', '1', '-ar', str(sr), '-'],
        capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"오디오 추출 실패: {path}\n{r.stderr.decode()[:300]}")
    return np.frombuffer(r.stdout, dtype=np.float32).copy()


def onset_envelope(x: np.ndarray, hop: int = HOP, win: int = WIN):
    """
    에너지의 양의 변화량 = 온셋 강도. 녹음 조건 차이에 강하다.
    returns: (envelope, envelope_fps)
    """
    if len(x) < win:
        raise ValueError("오디오가 너무 짧습니다")
    frames = np.lib.stride_tricks.sliding_window_view(x, win)[::hop]
    rms = np.sqrt((frames.astype(np.float64) ** 2).mean(axis=1))
    rms = np.log1p(rms * 1000.0)                 # 큰 소리에 덜 휘둘리게
    onset = np.maximum(np.diff(rms, prepend=rms[0]), 0.0)
    return onset, SR / hop


def xcorr(a: np.ndarray, b: np.ndarray, min_overlap_frac: float = 0.5):
    """
    정규화 상호상관. returns: (lags, corr)
    lag > 0 이면 b가 a보다 lag만큼 늦게 시작한 것.
    겹치는 구간 길이로 나눠서 짧게 겹치는 큰 lag가 과대평가되지 않게 한다.
    """
    a = (a - a.mean()) / (a.std() + 1e-12)
    b = (b - b.mean()) / (b.std() + 1e-12)
    n = len(a) + len(b) - 1
    N = 1 << int(np.ceil(np.log2(n)))
    cc = np.fft.irfft(np.fft.rfft(a, N) * np.conj(np.fft.rfft(b, N)), N)
    cc = np.concatenate([cc[-(len(b) - 1):], cc[:len(a)]])
    lags = np.arange(-(len(b) - 1), len(a))
    overlap = np.minimum.reduce([
        np.full_like(lags, min(len(a), len(b))),
        len(a) - np.maximum(lags, 0),
        len(b) + np.minimum(lags, 0),
    ]).astype(float)
    # 겹침이 적으면 몇 안 되는 표본으로 상관이 우연히 높아진다. 절반은 겹치게.
    valid = overlap >= max(20, min_overlap_frac * min(len(a), len(b)))
    return lags[valid], (cc[valid] / overlap[valid])


def estimate_offset(path_a: str, path_b: str, min_conf: float = MIN_CONFIDENCE,
                    min_peak: float = MIN_PEAK,
                    max_offset_sec: float = None):
    """
    returns: dict — offset_sec(b가 a보다 늦은 정도), confidence, peak, usable
    """
    for p in (path_a, path_b):
        if not has_audio(p):
            return {'usable': False, 'reason': f'오디오 트랙 없음: {p}'}

    ea, fps_e = onset_envelope(load_audio(path_a))
    eb, _ = onset_envelope(load_audio(path_b))
    lags, corr = xcorr(ea, eb)
    if corr.size == 0:
        return {'usable': False, 'reason': '상관 계산 실패'}

    # 현실적인 오프셋 범위로 후보를 제한한다. 13초 영상에서 10초 오프셋 같은
    # 값은 실제 사용 상황이 아니라 끝단의 허위 피크다.
    if max_offset_sec is None:
        max_offset_sec = MAX_OFFSET_FRAC * min(len(ea), len(eb)) / fps_e
    in_range = np.abs(lags) <= max_offset_sec * fps_e
    if not in_range.any():
        return {'usable': False, 'reason': '오프셋 후보 범위가 비어 있음'}
    lags, corr = lags[in_range], corr[in_range]

    k = int(np.argmax(corr))
    peak, peak_lag = float(corr[k]), int(lags[k])

    # 신뢰도: 피크가 "피크 주변을 제외한 나머지"의 표준편차 대비 몇 배인가.
    # 같은 곡이면 뾰족한 피크 하나, 다른 곡/무음이면 밋밋하다.
    guard = int(0.5 * fps_e)          # 피크 ±0.5초는 제외
    mask = np.ones_like(corr, dtype=bool)
    mask[max(0, k - guard):k + guard + 1] = False
    bg = corr[mask]
    conf = float((peak - bg.mean()) / (bg.std() + 1e-12)) if bg.size > 10 else 0.0

    ok_conf, ok_peak = conf >= min_conf, peak >= min_peak
    reason = None
    if not ok_peak:
        reason = f'피크 상관이 낮음 ({peak:.2f} < {min_peak}) — 다른 곡이거나 무음'
    elif not ok_conf:
        reason = f'피크가 뚜렷하지 않음 (신뢰도 {conf:.1f} < {min_conf})'

    return {
        'usable': bool(ok_conf and ok_peak),
        'offset_sec': peak_lag / fps_e,
        'confidence': conf,
        'peak': peak,
        'max_offset_sec': max_offset_sec,
        'envelope_fps': fps_e,
        'min_confidence': min_conf,
        'min_peak': min_peak,
        'reason': reason,
    }


def main():
    ap = argparse.ArgumentParser(description="오디오 기반 전역 시간 오프셋 추정")
    ap.add_argument('--a', required=True, help='기준 영상')
    ap.add_argument('--b', required=True, help='비교 영상')
    ap.add_argument('--min-confidence', type=float, default=MIN_CONFIDENCE)
    ap.add_argument('--min-peak', type=float, default=MIN_PEAK)
    ap.add_argument('--max-offset-sec', type=float, default=None,
                    help=f'허용 오프셋 상한(초). 기본은 짧은 쪽 길이의 {MAX_OFFSET_FRAC:.0%}')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    r = estimate_offset(args.a, args.b, args.min_confidence,
                        args.min_peak, args.max_offset_sec)
    print(f"기준: {args.a}")
    print(f"비교: {args.b}")
    if r['usable']:
        print(f"  오프셋 {r['offset_sec']:+.3f}초  "
              f"(피크 {r['peak']:.3f}, 신뢰도 {r['confidence']:.1f})")
        print(f"  → 비교 영상이 기준보다 {abs(r['offset_sec']):.3f}초 "
              f"{'늦게' if r['offset_sec'] > 0 else '일찍'} 시작")
    else:
        print(f"  사용 불가 — {r['reason']}")
        if 'offset_sec' in r:
            print(f"  (참고: 최대 피크는 {r['offset_sec']:+.3f}초였음)")

    if args.out:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump({'a': args.a, 'b': args.b, **r}, f, ensure_ascii=False, indent=2)
        print(f"저장: {args.out}")


if __name__ == '__main__':
    main()
