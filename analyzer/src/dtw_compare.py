# src/dtw_compare.py
import numpy as np
from dtaidistance import dtw
from tqdm import tqdm

def flatten_keypoints(keypoints, num_keypoints=33):
    """
'''
    Convert a single frame's keypoints into a 1D numpy array.
    - keypoints: list of (x, y, visibility) tuples, OR numpy array of shape (N,2) or (N,3), OR None.
    Returns a numpy array of shape (num_keypoints*3,), where num_keypoints is the number of joints.
'''
    """
    if keypoints is None or (isinstance(keypoints, np.ndarray) and keypoints.shape == (0,)):
        return np.zeros(num_keypoints * 3)
    
    keypoints = np.array(keypoints)
    # (N,2)라면 visibility=1로 채워서 (N,3)으로 확장
    if keypoints.ndim == 2 and keypoints.shape[1] == 2:
        v = np.ones((keypoints.shape[0], 1), dtype=float)
        keypoints = np.concatenate([keypoints, v], axis=1)
    # (N,3)인지 체크 (N은 num_keypoints와 일치해야 안정적)
    if keypoints.ndim != 2 or keypoints.shape[1] != 3:
        raise ValueError(f"키포인트 배열 형식이 잘못되었습니다: expected (N,2) or (N,3), got {keypoints.shape}")
    # 부족하면 패딩 (예: 17개만 있는 경우 33개로 맞추기)
    N = keypoints.shape[0]
    if N < num_keypoints:
        padded = np.zeros((num_keypoints, 3), dtype=keypoints.dtype)
        padded[:N] = keypoints
        keypoints = padded
    # 너무 많으면 자르기 (예: 34개라면 33개만)
    elif N > num_keypoints:
        keypoints = keypoints[:num_keypoints]
    return keypoints.flatten()

def compare_sequences(
    user_seq,
    standard_seq,
    fps: float = 60.0,
    max_time_diff: float | None = None,
    joint_error_thresh: float | None = None,
    min_separation: float | None = None,
    num_keypoints: int=33,
    window: int=10
):
    """
    
    '''두 시퀀스를 DTW로 비교하여 mismatch 정보를 리턴.

    Args:
      user_seq, standard_seq: 키포인트 프레임 리스트
      fps: 초당 프레임 수
      max_time_diff: (초) 이 이상 차이나는 프레임쌍은 무시
      joint_error_thresh: (픽셀 또는 정규화 거리) 이 값 이상 오차난 관절만 리포트
      min_separation: (초) 이보다 가까운 연속 프레임쌍은 하나만 리포트

    Returns:
      score: 전체 유사도 (0–100)
      details: [
        {
          'user_frame': int,
          'standard_frame': int,
          'frame_distance': float,
          'joints': [(joint_idx, distance), …]
        }, …
      ]'''
    """
    # 1) flatten
    user_flat = np.vstack([flatten_keypoints(f, num_keypoints=num_keypoints) for f in user_seq])
    std_flat  = np.vstack([flatten_keypoints(f, num_keypoints=num_keypoints) for f in standard_seq])

    # 2D → 1D 변환
    user_1d = user_flat.flatten()
    std_1d  = std_flat.flatten()

    print("user_1d shape:", user_1d.shape)  # (n_frames,)
    print("std_1d shape :", std_1d.shape)   # (n_frames,)

    # dtaidistance 적용
    distance = dtw.distance(user_1d, std_1d, window=window)
    path = dtw.warping_path(user_1d, std_1d, window=window)
    
    # 4) per-frame 거리 및 시간 필터링
    per_frame = []
    for u_idx, s_idx in tqdm(path, desc="프레임별 거리 계산 진행중"):
        if u_idx >= user_flat.shape[0] or s_idx >= std_flat.shape[0]:
            continue
        frame_dist = np.linalg.norm(user_flat[u_idx]- std_flat[s_idx])
        # 1) 너무 멀리 떨어진 프레임쌍 제외
        if max_time_diff is not None and abs(u_idx - s_idx)/fps > max_time_diff:
            continue
        per_frame.append((u_idx, s_idx, frame_dist))

    # 5) 거리 내림차순 정렬
    per_frame.sort(key=lambda x: x[2], reverse=True)

    # 6) 중복 제거 및 관절 필터링
    details = []
    sep_frames = int(min_separation * fps) if min_separation is not None else None
    last_u = last_s = None

    # 검증 코드 추가
    violated = False
    for u_idx, s_idx in path:
        diff = abs(u_idx - s_idx)
        if diff > window:
            print(f"[VIOLATION] user_idx: {u_idx}, std_idx: {s_idx}, diff: {diff} > window({window})")
            violated = True
        else:
            print(f"user_idx: {u_idx}, std_idx: {s_idx}, diff: {diff}")

    if not violated:
        print("모든 경로에서 |user_idx - std_idx| <= radius 만족!")
    else:
        print("window 조건을 위반하는 경로가 있습니다!")

    for u_idx, s_idx, frame_dist in per_frame:
        # 원본 키포인트
        u_pts = user_seq[u_idx]
        s_pts = standard_seq[s_idx]
        if u_pts is None:
            u_pts = np.zeros((num_keypoints, 3))
        if s_pts is None:
            s_pts = np.zeros((num_keypoints, 3))
        u_list = u_pts.tolist() if isinstance(u_pts, np.ndarray) else u_pts
        s_list = s_pts.tolist() if isinstance(s_pts, np.ndarray) else s_pts

        joint_diffs = []
        for j, (ux, uy, _) in enumerate(u_list):
            sx, sy, _ = s_list[j]
            d = float(np.hypot(ux - sx, uy - sy))
            # joint_error_thresh 이상인 관절만 추가
            if joint_error_thresh is None or d >= joint_error_thresh:
                joint_diffs.append((j, d))
        if not joint_diffs:
            continue

        details.append({
            'user_frame': int(u_idx),
            'standard_frame': int(s_idx),
            'frame_distance': float(frame_dist),
            'joints': joint_diffs
        })
        last_u, last_s = u_idx, s_idx

    # 7) 전체 스코어 정규화
    max_dist = len(path) * user_flat.shape[1]
    score = max(0, 100 - (distance / max_dist) * 100)

    # 시간 순으로 정렬 (user_frame 기준 오름차순)
    details.sort(key=lambda e: e['user_frame'])

    # 9) min_separation 기준 후처리
    if min_separation is not None and details:
        kept = [details[0]]
        sep_frames = int(min_separation * fps)
        last_u = details[0]['user_frame']
        for entry in details[1:]:
            if entry['user_frame'] - last_u >= sep_frames:
                kept.append(entry)
                last_u = entry['user_frame']
        details = kept

    return score, details
