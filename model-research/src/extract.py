# src/extract.py
"""영상 → PoseSequence 추출. 기준 영상과 사용자 영상이 같은 경로를 쓴다.

이전에는 `extract_pro_sequence.extract_sequence`(기준용, yolo/hybrid만 지원)와
`main.extract_user_sequence_and_measure`(사용자용)로 갈라져 있었고, 그래서
backend 목록이 서로 달랐다(CLAUDE.md 알려진 문제 3). 여기로 합치면서 해소됨.
"""
import time
import tracemalloc

import cv2

from src.pose_factory import make_pose_pipeline
from src.sequence import DEFAULT_CONF_THRESH, build_sequence
from src.video_utils import apply_rotation, open_video

# 백엔드별 관절 수
NUM_KEYPOINTS = {'yolo': 17, 'mediapipe': 33, 'hybrid': 33, 'vitpose': 17, 'rtmpose': 17}


def num_keypoints_for(backend: str) -> int:
    b = backend.lower()
    if b not in NUM_KEYPOINTS:
        raise ValueError(f"알 수 없는 backend: {backend}")
    return NUM_KEYPOINTS[b]


def extract_pose_sequence(video_path, backend, model_path=None,
                          conf_thresh=None, measure=True, verbose=True,
                          progress_every=60, model_complexity=0,
                          start_sec=None, end_sec=None):
    """
    returns: (PoseSequence, metrics dict)

    conf_thresh: None이면 백엔드 기본값 사용 (src.sequence.DEFAULT_CONF_THRESH)
    model_complexity: mediapipe/hybrid 전용. 0=Lite, 1=Full, 2=Heavy

    start_sec / end_sec: 안무 구간만 잘라서 추출한다 (TASKS.md D23).
        오프셋 자동 추정은 세 방법 모두 실패했으므로(포즈 DTW·오디오·비율 가정)
        사용자에게 안무 시작 시점을 받는다. 두 영상을 각자의 시작점으로 잘라내면
        전역 오프셋이 제거되어 좁은 밴드를 쓸 수 있다.
        여백 제거는 부수 효과도 있다 — 안무 전 리듬 타는 동작이 안무 구간과
        오인 매칭되는 경로를 아예 없앤다.

        반환되는 PoseSequence의 프레임 인덱스는 **잘라낸 구간 기준(0부터)**이다.
        원본 영상 기준 인덱스가 필요하면 `meta['source_start_frame']`을 더한다.
    """
    backend = backend.lower()
    num_kp = num_keypoints_for(backend)
    if conf_thresh is None:
        conf_thresh = DEFAULT_CONF_THRESH[backend]

    detect_fn, extract_fn = make_pose_pipeline(
        backend, model_path=model_path, model_complexity=model_complexity)

    cap, fps, rotation = open_video(video_path)
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    if rotation in (90, 270):          # 회전 시 표시상 W/H가 뒤바뀜 (D20)
        H, W = W, H

    # 구간 지정. cap.set(POS_FRAMES)는 코덱에 따라 키프레임으로 붙어 부정확할 수
    # 있어 읽고 건너뛴다. 디코딩은 남지만 비싼 포즈 추정은 건너뛰므로 손해가 작다.
    start_frame = max(0, int(round(start_sec * fps))) if start_sec else 0
    end_frame = int(round(end_sec * fps)) if end_sec else None

    raw = []
    n_detect_fail = 0
    frame_idx = -1

    if measure:
        tracemalloc.start()
    t0 = time.perf_counter()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1
        if frame_idx < start_frame:
            continue
        if end_frame is not None and frame_idx >= end_frame:
            break
        frame = apply_rotation(frame, rotation)

        if detect_fn is not None:
            kps_list = extract_fn(frame, detect_fn(frame))
        else:
            kps_list = extract_fn(frame)

        # 다중 인물 중 선택 로직은 보류 상태다 (TASKS.md D10).
        # 현재 테스트 영상에는 배경 인물이 없어 인덱스 0을 그대로 쓴다.
        if kps_list and kps_list[0] is not None:
            raw.append(kps_list[0])
        else:
            raw.append(None)
            n_detect_fail += 1

        if verbose and progress_every and len(raw) % progress_every == 0:
            print(f"    {len(raw)}프레임 처리...")

    elapsed = time.perf_counter() - t0
    peak_mem = 0
    if measure:
        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    cap.release()

    n = len(raw)
    seq = build_sequence(raw, num_kp, fps, (H, W),
                         conf_thresh=conf_thresh, source=video_path)
    seq.meta['source_start_frame'] = start_frame
    seq.meta['source_start_sec'] = start_frame / fps if fps else 0.0

    metrics = {
        'video': video_path,
        'backend': backend,
        'model_path': model_path if backend in ('yolo', 'vitpose', 'rtmpose') else None,
        'model_complexity': model_complexity if backend != 'yolo' else None,
        'frame_count': n,
        'orig_fps': fps,
        'frame_size': [H, W],
        'detect_fail_frames': n_detect_fail,
        'start_sec': start_sec,
        'end_sec': end_sec,
        'source_start_frame': start_frame,
        'measured_fps': (n / elapsed) if elapsed > 0 else 0.0,
        'latency_ms': (elapsed / n * 1000.0) if n else 0.0,
        'memory_MB': peak_mem / (1024 ** 2),
    }

    if verbose:
        cov = seq.coverage()
        print(f"  {video_path}")
        print(f"    {n}프레임 fps={fps:.3f} {W}x{H} | 검출실패 {n_detect_fail}프레임")
        print(f"    관절 유효율 {cov['joint_valid_ratio'] * 100:.1f}% | "
              f"게이트 통과 {cov['gated_frames']}/{n} "
              f"(평가불가 {cov['ungated_pct']:.1f}%)")
        print(f"    처리 {metrics['measured_fps']:.1f}fps "
              f"({metrics['latency_ms']:.1f}ms/frame)")

    return seq, metrics
