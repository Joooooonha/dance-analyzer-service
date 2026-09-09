# src/dtw_compare.py
"""DTW 시간축 정렬 + 프레임별 오차 계산.

이전 구현의 문제 두 가지를 고친 것이다 (TASKS.md 참조).

1. dtaidistance의 **1차원 전용 API**(`dtw.distance`)에 다차원 데이터를 통짜
   flatten해서 넣고 있었다. 그러면 프레임 경계가 사라져 "5번 프레임의 습도"와
   "6번 프레임의 기온"을 정렬하는 꼴이 된다. `dtw_ndim`으로 교체했다. (D7)
2. 가려진/검출 실패 관절을 0으로 채워서, 양쪽 모두 0인 관절이 거리 0 =
   "완벽 일치"로 계산됐다. 이제 유효 항목만 평균낸다. (D2)

정렬용 / 채점용 feature를 분리한다 (D3).
- 정렬용: 짧은 구멍을 보간해 연속성 확보 → DTW에 입력
- 채점용: 마스킹 그대로 → 오차 계산에 사용
DTW는 대응 경로(path)만 제공하고 값은 쓰지 않으므로, 정렬용의 보간값이
최종 점수를 오염시키지 않는다.
"""
import numpy as np
from dtaidistance import dtw_ndim

from src.features import FeatureSet

# 점수 환산 스케일. **잠정값이다.**
# angle: 평균 관절 각도 오차가 이 값(도)이면 0점.
# coord: 프레임 높이 대비 이 비율만큼 어긋나면 0점.
SCORE_SCALE = {'angle': 45.0, 'coord': 0.15}


def _robust_line(su: np.ndarray, fallback_slope: float, n_samples: int = 20000):
    """
    경로 점들에 강건하게 직선을 적합한다 (Theil-Sen 근사).

    무작위 점쌍의 기울기 중앙값을 쓴다. 최소제곱과 달리 이상치(DTW가 멀리
    도망간 구간)에 끌려가지 않는다. 점쌍 전수 계산은 O(N²)이라 표본만 쓴다.

    su: (N, 2) = (user_idx, std_idx)
    returns: (slope, offset) — user ≈ slope*std + offset
    """
    n = len(su)
    if n < 3:
        return fallback_slope, 0.0
    rng = np.random.default_rng(0)              # 재현성 고정
    i = rng.integers(0, n, n_samples)
    j = rng.integers(0, n, n_samples)
    ds = su[j, 1] - su[i, 1]
    du = su[j, 0] - su[i, 0]
    ok = np.abs(ds) > 1e-9
    if not ok.any():
        return fallback_slope, 0.0
    slope = float(np.median(du[ok] / ds[ok]))
    if not np.isfinite(slope) or slope <= 0:
        slope = fallback_slope
    offset = float(np.median(su[:, 0] - su[:, 1] * slope))
    return slope, offset


def align_two_pass(user_feat: FeatureSet, std_feat: FeatureSet,
                   window: int = 5, max_gap_frames: int = 5, psi: int = None):
    """
    2단계 정렬 (TASKS.md D22).

    **문제**: 기존 `align()`은 밴드 제약(window)이 사실상 무력화돼 있었다.
    경로 존재를 보장하려고 `window = max(요청값, |길이차|+1)`로 넓히는데,
    두 영상 길이가 크게 다르면(natural1: 882 vs 1101, 길이차 219) 요청한
    window=15가 220프레임(7.3초)으로 부풀어 제약이 사라진다.

    제약이 없으면 DTW는 멀리 떨어진 "포즈가 더 비슷한" 지점으로 도망갈 수 있다.
    실측에서 DTW는 사람이 찍은 정답보다 포즈 오차가 낮은 지점을 60~67% 비율로
    선택하고 있었다 — 알고리즘이 목적함수에 충실했을 뿐이지만, 안무 구조상의
    정답과는 어긋난다.

    **해법**: 길이차와 국소 워핑을 분리해서 처리한다.
      1단계 — 넓은 밴드로 한 번 정렬해 **전역 오프셋**(녹화 시작 시점 차이)을 추정
      2단계 — 그 오프셋과 fps 비율로 user를 재샘플해 대각선을 맞춘 뒤,
              **좁은 밴드**로 국소 워핑만 허용

    앵커 없이 1단계 결과만으로 오프셋을 구하므로 실서비스에서도 동작한다.

    returns: [(user_idx, std_idx), ...]
    """
    U_all = user_feat.alignment_matrix(max_gap_frames)
    S = std_feat.alignment_matrix(max_gap_frames)
    n_u, n_s = user_feat.n_frames, std_feat.n_frames
    fps_u, fps_s = user_feat.fps, std_feat.fps
    ratio = fps_u / fps_s

    # 1단계 — 전역 추세(기울기 + 오프셋) 추정.
    # 오프셋만 빼면 부족하다: 두 영상의 재생 속도가 다르면 대각선의 기울기 자체가
    # 1이 아니다. fps 비율만으로도 부족한데, fps가 같아도 사람이 더 빠르거나
    # 느리게 추면 기울기가 달라지기 때문이다. 경로에 직선을 적합해 둘 다 얻는다.
    p1 = dtw_ndim.warping_path(np.ascontiguousarray(U_all),
                               np.ascontiguousarray(S),
                               window=abs(n_u - n_s) + 1)
    # 최소제곱(polyfit)은 쓰지 않는다. 1단계 경로에는 DTW가 멀리 도망간 구간이
    # 섞여 있고, 최소제곱은 그런 이상치에 끌려가 기울기를 망가뜨린다
    # (실측: natural1에서 2단계 ±5프레임 내 94.9% → 15.4%로 붕괴).
    # 점쌍 기울기의 중앙값(Theil-Sen)으로 강건하게 추정한다.
    su = np.array(p1, dtype=float)              # (N, 2) = (user, std)
    slope, offset = _robust_line(su, ratio)

    # 2단계 — 전역 추세를 제거해 대각선을 맞춘 뒤 좁은 밴드
    src = np.clip(np.round(np.arange(n_s) * slope + offset), 0, n_u - 1).astype(int)
    kwargs = {'window': int(window)}
    if psi:
        kwargs['psi'] = int(min(psi, min(n_s, len(src))))
    p2 = dtw_ndim.warping_path(np.ascontiguousarray(U_all[src]),
                               np.ascontiguousarray(S), **kwargs)
    return [(int(src[u]), int(s)) for u, s in p2]


def align(user_feat: FeatureSet, std_feat: FeatureSet,
          window: int = None, max_gap_frames: int = 5, psi: int = None):
    """
    두 시퀀스의 DTW 대응 경로를 구한다.

    window: 밴드 제약(Sakoe-Chiba, 프레임 단위). 길이 차이보다 작으면 경로를
            만들 수 없으므로 최소 |길이차|+1로 넓힌다. None이면 제약 없음.
    psi:    끝점 완화(psi-relaxation). 양 끝에서 최대 psi프레임까지 대응 없이
            건너뛸 수 있게 한다. None이면 경로가 (0,0)에서 시작해
            (n-1, m-1)에서 끝나도록 강제된다.

            사용자가 안무의 일부만 췄거나 앞뒤에 여백이 있으면 끝점 강제가
            정렬을 망가뜨린다 (TASKS.md D19). 그럴 때 psi를 켠다.
            dtaidistance는 psi가 짧은 쪽 시퀀스 길이를 넘으면 IndexError로
            죽으므로 여기서 잘라낸다.

    returns: [(user_idx, std_idx), ...]
    """
    u_feat = user_feat.alignment_matrix(max_gap_frames)
    s_feat = std_feat.alignment_matrix(max_gap_frames)

    kwargs = {}
    if window is not None:
        min_needed = abs(user_feat.n_frames - std_feat.n_frames)
        kwargs['window'] = int(max(window, min_needed + 1))
    if psi:
        cap = min(user_feat.n_frames, std_feat.n_frames)
        kwargs['psi'] = int(min(psi, cap))

    return dtw_ndim.warping_path(u_feat, s_feat, **kwargs)


def compare_sequences(user_feat: FeatureSet, std_feat: FeatureSet,
                      window: int = 15,
                      max_time_diff: float = None,
                      error_thresh: float = None,
                      min_separation: float = None,
                      min_valid_ratio: float = 0.3,
                      min_frontality: float = None,
                      max_gap_frames: int = 5,
                      psi: int = None):
    """
    max_time_diff:   (초) **경로 전체의 중앙값 오프셋 기준** 이보다 벗어난
                     대응쌍만 정렬 실패로 보고 제외한다 (D21). 절대 시간차가
                     아니다 — 두 영상의 녹화 시작 시점이 몇 초씩 어긋나는 건
                     실촬영에서 흔하고 psi가 정상적으로 처리하는 상황인데,
                     절대 기준으로 필터링하면 이런 정상적인 고정 오프셋까지
                     전부 걸러져 채점 가능한 쌍이 0이 되는 문제가 있었다.
                     두 영상의 fps를 각각 사용해 초로 환산한다 (D8).
    error_thresh:    이 값 이상 어긋난 항목만 details에 담는다.
                     angle이면 도(degree), coord면 정규화 거리.
    min_separation:  (초) 이보다 가까운 리포트는 하나만 남긴다.
    min_valid_ratio: 프레임 게이트의 (b) 조건 (D4).
    psi:             끝점 완화. 사용자가 안무 일부만 췄거나 앞뒤 여백이
                     있을 때 필요 (D19). None이면 끝점을 강제한다.
    min_frontality:  정면성이 이보다 낮은 프레임은 제외 (D6).
                     None이면 게이트하지 않고 통계만 기록한다 — 적절한
                     임계값이 아직 검증되지 않았기 때문.
    """
    if user_feat.kind != std_feat.kind:
        raise ValueError(
            f"feature 종류가 다릅니다: {user_feat.kind} vs {std_feat.kind}")

    path = align(user_feat, std_feat, window=window,
                 max_gap_frames=max_gap_frames, psi=psi)

    u_gate = user_feat.frame_gate(min_valid_ratio)
    s_gate = std_feat.frame_gate(min_valid_ratio)
    fps_u, fps_s = user_feat.fps, std_feat.fps

    u_front = user_feat.meta.get('frontality')
    s_front = std_feat.meta.get('frontality')

    # 경로 전체의 중앙값 오프셋 (D21). 두 영상의 녹화 시작 시점이 몇 초씩
    # 어긋나는 것은 실촬영에서 정상이므로, 그 고정 오프셋 자체를 "정렬 실패"로
    # 걸러내면 안 된다. 이 오프셋 대비 벗어난 정도만 본다.
    global_offset = 0.0
    if max_time_diff is not None and path:
        offsets = np.array([u / fps_u - s / fps_s for u, s in path])
        global_offset = float(np.median(offsets))

    scored = []
    n_skip_gate = n_skip_time = n_skip_novalid = n_skip_front = 0

    for u_idx, s_idx in path:
        if not (u_gate[u_idx] and s_gate[s_idx]):
            n_skip_gate += 1
            continue

        if max_time_diff is not None:
            rel = (u_idx / fps_u - s_idx / fps_s) - global_offset
            if abs(rel) > max_time_diff:
                n_skip_time += 1
                continue

        if min_frontality is not None and u_front is not None and s_front is not None:
            if u_front[u_idx] < min_frontality or s_front[s_idx] < min_frontality:
                n_skip_front += 1
                continue

        mean_e, n_valid, per_item, signed_item = user_feat.pairwise_error(
            u_idx, std_feat, s_idx)
        if mean_e is None:
            n_skip_novalid += 1
            continue
        scored.append((u_idx, s_idx, mean_e, n_valid, per_item, signed_item))

    stats = {
        'feature_kind': user_feat.kind,
        'error_unit': user_feat.unit,
        'global_offset_sec': global_offset,
        'path_len': len(path),
        'scored_pairs': len(scored),
        'skipped_frame_gate': n_skip_gate,
        'skipped_time_filter': n_skip_time,
        'skipped_low_frontality': n_skip_front,
        'skipped_no_valid_item': n_skip_novalid,
        'scored_pct': (len(scored) / len(path) * 100.0) if path else 0.0,
    }

    if not scored:
        return {'score': None, 'reason': '채점 가능한 대응쌍이 없습니다',
                'details': [], 'stats': stats, 'distance': None}

    errs = np.array([s[2] for s in scored], dtype=float)
    mean_err = float(errs.mean())
    stats.update({
        'mean_error': mean_err,
        'median_error': float(np.median(errs)),
        'p90_error': float(np.percentile(errs, 90)),
        'max_error': float(errs.max()),
        'mean_valid_items': float(np.mean([s[3] for s in scored])),
    })
    if u_front is not None:
        stats['user_frontality_median'] = float(np.median(u_front[u_gate])) if u_gate.any() else None
        stats['std_frontality_median'] = float(np.median(s_front[s_gate])) if s_gate.any() else None

    scale = SCORE_SCALE[user_feat.kind]
    score = 100.0 * (1.0 - min(mean_err / scale, 1.0))

    details = []
    for u_idx, s_idx, mean_e, n_valid, per_item, signed_item in sorted(
            scored, key=lambda x: x[2], reverse=True):
        items = ([(nm, e) for nm, e in per_item if e >= error_thresh]
                 if error_thresh is not None else per_item)
        if not items:
            continue
        details.append({
            'user_frame': int(u_idx),
            'standard_frame': int(s_idx),
            'user_t': round(u_idx / fps_u, 4),
            'standard_t': round(s_idx / fps_s, 4),
            'frame_error': float(mean_e),
            'valid_items': int(n_valid),
            'items': [(nm, round(float(e), 3)) for nm, e in
                      sorted(items, key=lambda x: x[1], reverse=True)],
            'signed_items': [(nm, round(float(v), 3)) for nm, v in signed_item],
        })

    details.sort(key=lambda e: e['user_frame'])

    if min_separation is not None and details:
        sep = int(min_separation * fps_u)
        kept = [details[0]]
        last = details[0]['user_frame']
        for e in details[1:]:
            if e['user_frame'] - last >= sep:
                kept.append(e)
                last = e['user_frame']
        details = kept

    return {
        'score': float(score),
        'score_is_provisional': True,
        'distance': mean_err,
        'details': details,
        'stats': stats,
        'path': [(int(a), int(b)) for a, b in path],
    }
