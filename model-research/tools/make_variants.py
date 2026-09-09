# tools/make_variants.py
"""원본 영상에서 시간축이 변형된 사본을 만들고, 대응 정답을 함께 저장한다.

앵커(사람이 찍은 10~15개)는 sparse GT라 정렬 품질을 거칠게밖에 못 잰다.
여기서 만드는 변형본은 **모든 프레임의 대응 정답을 알고 있는 dense GT**다.
변형이 결정적(deterministic)이기 때문이다 — 출력 프레임 i가 원본 몇 번
프레임에서 왔는지를 그대로 기록해두면 된다. (TASKS.md Phase 1)

ffmpeg 없이 OpenCV로 프레임을 직접 재배열한다. 프레임 단위 인덱스 매핑이
곧 정답이라 애매함이 없다.

실행 (프로젝트 루트에서):

    python -m tools.make_variants --video data/videos/real/user_dancer.mp4 \
        --out-dir data/variants

만들어지는 변형:
  offset  — 녹화를 늦게 시작한 경우 (앞부분 잘림)
  speed   — 전체적으로 빠르거나 느리게 춘 경우
  local   — 중간 한 구간만 느려진 경우 (DTW가 진짜 필요한 케이스)
"""
import argparse
import json
import os

import cv2
import numpy as np

from src.video_utils import apply_rotation, open_video


def read_all_frames(path):
    cap, fps, rotation = open_video(path)
    frames = []
    while True:
        ret, f = cap.read()
        if not ret:
            break
        frames.append(apply_rotation(f, rotation))
    cap.release()
    if not frames:
        raise ValueError(f"프레임을 읽지 못했습니다: {path}")
    return frames, fps


def mapping_offset(n, offset_frames):
    """녹화를 늦게 시작 — 앞 offset_frames 만큼 잘라낸다."""
    offset_frames = int(np.clip(offset_frames, 0, n - 2))
    return list(range(offset_frames, n))


def mapping_trim(n, start_frac=0.25, end_frac=0.7):
    """
    안무의 일부만 춘 경우. 앞뒤가 모두 잘려서 **양 끝이 기준 영상과 대응되지
    않는다.** 일반 DTW는 경로의 시작을 (0,0), 끝을 (n-1,m-1)로 강제하므로
    이 경우 양 끝을 억지로 이어붙이며 정렬이 망가진다. psi 완화가 필요한
    케이스다 (TASKS.md D19).
    """
    a, b = int(n * start_frac), int(n * end_frac)
    return list(range(a, b))


def mapping_speed(n, rate):
    """전역 배속. rate>1이면 빠르게(프레임 수 감소), <1이면 느리게."""
    out_n = max(2, int(round(n / rate)))
    return [int(round(v)) for v in np.linspace(0, n - 1, out_n)]


def mapping_local(n, start_frac=0.35, end_frac=0.6, factor=0.5):
    """
    중간 구간만 속도를 바꾼다. factor<1이면 그 구간이 느려진다.
    앞뒤는 원본 속도 그대로라, 전역 오프셋으로는 맞출 수 없고
    구간별 워핑이 있어야만 정렬되는 케이스다.
    """
    a = int(n * start_frac)
    b = int(n * end_frac)
    seg_out = max(2, int(round((b - a) / factor)))
    mid = [int(round(v)) for v in np.linspace(a, b - 1, seg_out)]
    return list(range(0, a)) + mid + list(range(b, n))


# ── 공간 변형 ──────────────────────────────────────────────
# 시간축은 그대로 두고(정답 대응 = 항등) 촬영 조건만 바꾼다.
# 좌표 feature는 흔들리고 각도 feature는 불변이어야 한다는 것을 측정하기 위한 것
# (TASKS.md D1, D5 검증).

def spatial_zoom(frame, factor):
    """중앙을 잘라 원래 크기로 늘린다 = 피사체가 커진다 (카메라가 가까워진 효과)."""
    h, w = frame.shape[:2]
    ch, cw = int(h / factor), int(w / factor)
    y0, x0 = (h - ch) // 2, (w - cw) // 2
    return cv2.resize(frame[y0:y0 + ch, x0:x0 + cw], (w, h))


def spatial_shift(frame, dx_frac, dy_frac):
    """화면 안에서 피사체 위치를 옮긴다 (프레이밍 차이)."""
    h, w = frame.shape[:2]
    M = np.float32([[1, 0, dx_frac * w], [0, 1, dy_frac * h]])
    return cv2.warpAffine(frame, M, (w, h), borderValue=(255, 255, 255))


def spatial_roll(frame, degrees):
    """이미지를 회전 = 폰을 기울여 촬영한 효과 (카메라 롤)."""
    h, w = frame.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), degrees, 1.0)
    return cv2.warpAffine(frame, M, (w, h), borderValue=(255, 255, 255))


_BARREL_CACHE = {}


def spatial_barrel(frame, k1, k2=0.0):
    """
    배럴(초광각) 렌즈 왜곡을 합성한다.

    좁은 공간에서 전신을 담으려면 0.5배 초광각으로 찍는 경우가 실제로 흔하다.
    각도 feature는 이동·회전·균등 스케일에는 불변이지만 **비선형 렌즈 왜곡은
    방어하지 못하므로**, 그 영향이 실제로 얼마나 되는지 측정하기 위한 변형이다.

    표준 방사 왜곡 모델: 중심에서의 거리 r에 대해 배율 (1 + k1·r² + k2·r⁴).
    k1 > 0이면 가장자리가 바깥에서 샘플링되어 배럴 형태가 된다.
    r은 이미지 대각선의 절반으로 정규화하므로 k1은 해상도와 무관하다.
    """
    h, w = frame.shape[:2]
    key = (h, w, k1, k2)
    if key not in _BARREL_CACHE:
        cx, cy = w / 2.0, h / 2.0
        norm = np.hypot(cx, cy)
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        dx, dy = (xs - cx) / norm, (ys - cy) / norm
        r2 = dx * dx + dy * dy
        s = 1.0 + k1 * r2 + k2 * r2 * r2
        _BARREL_CACHE[key] = (
            (cx + dx * s * norm).astype(np.float32),
            (cy + dy * s * norm).astype(np.float32))
    mx, my = _BARREL_CACHE[key]
    return cv2.remap(frame, mx, my, cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))


SPATIAL_FNS = {
    'zoom': lambda f, p: spatial_zoom(f, p['factor']),
    'shift': lambda f, p: spatial_shift(f, p['dx'], p['dy']),
    'roll': lambda f, p: spatial_roll(f, p['degrees']),
    'barrel': lambda f, p: spatial_barrel(f, p['k1'], p.get('k2', 0.0)),
}


def write_variant(frames, fps, src_idx, out_video, out_json, params):
    h, w = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(out_video, fourcc, fps, (w, h))
    if not writer.isOpened():
        raise RuntimeError(f"VideoWriter를 열 수 없습니다: {out_video}")

    spatial = params.get('spatial')
    fn = SPATIAL_FNS[spatial['kind']] if spatial else None
    for i in src_idx:
        f = frames[i]
        if fn is not None:
            f = fn(f, spatial)
        writer.write(f)
    writer.release()

    # 저장한 뒤 실제로 몇 프레임이 쓰였는지 확인한다.
    # 코덱에 따라 요청한 프레임 수와 달라질 수 있고, 그러면 정답 매핑이
    # 어긋나므로 반드시 검증한다.
    cap, out_fps, _rot = open_video(out_video)
    actual = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    data = {
        'variant_video': out_video,
        'source_video': params['source_video'],
        'fps': fps,
        'transform': params,
        'expected_frames': len(src_idx),
        'actual_frames': actual,
        # variant_frame i -> source_frame src_to[i]
        'variant_to_source': [int(v) for v in src_idx],
    }
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

    ok = "OK" if actual == len(src_idx) else f"!! 불일치 (요청 {len(src_idx)})"
    print(f"  {os.path.basename(out_video)}: {actual}프레임 fps={out_fps:.3f}  {ok}")
    return actual == len(src_idx)


def main():
    ap = argparse.ArgumentParser(description="시간축 변형본 + dense GT 생성")
    ap.add_argument('--video', required=True, help='원본 영상 (기준이 됨)')
    ap.add_argument('--out-dir', default='data/variants')
    ap.add_argument('--offset-sec', type=float, default=2.0)
    ap.add_argument('--speeds', type=float, nargs='*', default=[0.9, 1.1])
    ap.add_argument('--local-factor', type=float, default=0.5)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    print(f"원본 로드: {args.video}")
    frames, fps = read_all_frames(args.video)
    n = len(frames)
    print(f"  {n}프레임 fps={fps:.3f} {frames[0].shape[1]}x{frames[0].shape[0]}")

    stem = os.path.splitext(os.path.basename(args.video))[0]
    variants = []

    off = int(round(args.offset_sec * fps))
    variants.append((f'{stem}__offset{off}', mapping_offset(n, off),
                     {'kind': 'offset', 'offset_frames': off,
                      'offset_sec': args.offset_sec}))

    variants.append((f'{stem}__trim', mapping_trim(n),
                     {'kind': 'trim', 'start_frac': 0.25, 'end_frac': 0.7}))

    for r in args.speeds:
        variants.append((f'{stem}__speed{r:.2f}', mapping_speed(n, r),
                         {'kind': 'speed', 'rate': r}))

    variants.append((f'{stem}__local{args.local_factor:.2f}',
                     mapping_local(n, factor=args.local_factor),
                     {'kind': 'local', 'factor': args.local_factor,
                      'start_frac': 0.35, 'end_frac': 0.6}))

    # 공간 변형 — 시간축은 항등(프레임 i ↔ i)이라 정렬 정답이 자명하다.
    # 여기서 재려는 것은 정렬이 아니라 **feature의 촬영조건 불변성**이다.
    identity = list(range(n))
    # 대조군: 아무 변형 없이 재인코딩만 한 것. 여기서 나오는 오차가
    # "포즈 추정 + 코덱 노이즈 바닥"이며, 다른 변형의 오차는 이 값과 비교해야
    # 의미가 있다.
    variants.append((f'{stem}__reencode', identity,
                     {'kind': 'spatial', 'spatial': None}))
    variants.append((f'{stem}__zoom1.30', identity,
                     {'kind': 'spatial',
                      'spatial': {'kind': 'zoom', 'factor': 1.30}}))
    variants.append((f'{stem}__shift', identity,
                     {'kind': 'spatial',
                      'spatial': {'kind': 'shift', 'dx': 0.12, 'dy': -0.08}}))
    variants.append((f'{stem}__roll8', identity,
                     {'kind': 'spatial',
                      'spatial': {'kind': 'roll', 'degrees': 8.0}}))
    # 0.5배 초광각 왜곡 강도를 모르므로 약/중/강을 스윕한다.
    for name, k1 in [('barrelL', 0.15), ('barrelM', 0.35), ('barrelS', 0.60)]:
        variants.append((f'{stem}__{name}', identity,
                         {'kind': 'spatial',
                          'spatial': {'kind': 'barrel', 'k1': k1}}))

    print(f"변형본 {len(variants)}개 생성")
    all_ok = True
    for name, src_idx, params in variants:
        params['source_video'] = args.video
        out_video = os.path.join(args.out_dir, name + '.mp4')
        out_json = os.path.join(args.out_dir, name + '.gt.json')
        all_ok &= write_variant(frames, fps, src_idx, out_video, out_json, params)

    if not all_ok:
        print("! 일부 변형본의 프레임 수가 요청과 다릅니다. 정답 매핑이 어긋나므로 사용하지 마세요.")


if __name__ == '__main__':
    main()
