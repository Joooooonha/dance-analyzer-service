"""영상 → `PoseSequence`. 포즈 추출과 분석 엔진을 잇는다.

**백엔드는 YOLO-pose다.** 이전에는 MediaPipe였는데 두 가지 이유로 바꿨다:

1. MediaPipe 0.10.x에 **linux aarch64 휠이 없다.** 분석 서버(Asahi Linux)에
   설치 자체가 안 된다.
2. 뼈 안정성 실측에서 MediaPipe Full이 5개 중 꼴찌였고(0.0189),
   무엇보다 **정렬 정확도를 측정할 때 쓴 백엔드가 YOLO였다.** 서비스가 다른
   백엔드로 돌면 검증 수치가 서비스에 해당한다고 말할 수 없다.

여기서 함께 처리하는 것:

- **회전 메타데이터** (TASKS.md D20) — iPhone 세로 촬영본은 가로 버퍼 + "재생 시
  90도 회전" 메타데이터로 저장된다. OpenCV 버전에 따라 이를 적용하기도 하고
  안 하기도 해서, `open_video`가 자동 회전을 끄고 우리가 직접 돌린다.
- **구간 지정** (D23) — 사용자가 지정한 안무 시작 시점으로 잘라내면 전역
  오프셋이 제거되어 좁은 밴드를 쓸 수 있다.
- **프로세스 격리** — 아래 참조.
"""
import multiprocessing
import os
import sys

import cv2
import numpy as np

from engine.pose_yolo import NUM_KEYPOINTS, YoloPoseExtractor
from engine.sequence import PoseSequence, build_sequence
from engine.video_utils import apply_rotation, open_video


def extract_sequence(video_path, model_path=None, conf_thresh=0.5,
                     start_sec=None, end_sec=None):
    """
    영상에서 포즈 시퀀스를 뽑는다.

    start_sec / end_sec: 안무 구간 (TASKS.md D23).
        반환 시퀀스의 프레임 인덱스는 **잘라낸 구간 기준(0부터)**이며,
        원본 기준 인덱스는 `meta['source_start_frame']`을 더해 얻는다.
    """
    cap, fps, rotation = open_video(video_path)
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    if rotation in (90, 270):
        H, W = W, H

    start_frame = max(0, int(round(start_sec * fps))) if start_sec else 0
    end_frame = int(round(end_sec * fps)) if end_sec else None

    extractor = YoloPoseExtractor(model_path or None) if model_path \
        else YoloPoseExtractor()

    raw = []
    idx = -1
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            idx += 1
            # cap.set(POS_FRAMES)로 건너뛰지 않는다. 코덱에 따라 키프레임으로
            # 붙어 부정확할 수 있는데, 프레임이 하나만 밀려도 다른 동작이 된다.
            # 디코딩 비용은 남지만 비싼 포즈 추정은 건너뛰므로 손해가 작다.
            if idx < start_frame:
                continue
            if end_frame is not None and idx >= end_frame:
                break

            frame = apply_rotation(frame, rotation)
            raw.append(extractor.extract(frame))
    finally:
        cap.release()

    seq = build_sequence(raw, NUM_KEYPOINTS, fps, (H, W),
                         conf_thresh=conf_thresh, source=video_path)
    seq.meta['source_start_frame'] = start_frame
    seq.meta['source_start_sec'] = start_frame / fps if fps else 0.0
    seq.meta['rotation'] = rotation
    seq.meta['backend'] = 'yolo'
    return seq


# ---------------------------------------------------------------------------
# 프로세스 격리 추출
# ---------------------------------------------------------------------------
#
# **문제**: 한 프로세스에서 해상도가 다른 영상을 이어서 처리하면, 뒤에 처리한
# 영상의 추출 결과가 **매 실행마다 달라진다.**
#
# 새 프로세스 3회 반복 실측 (natural1, 기준 1920x1080 → 연습 1080x1920):
#
#   | 처리 순서            | 기준 영상 해시 | 연습 영상 해시        |
#   |---------------------|--------------|---------------------|
#   | 기준 → 연습 (1회차)   | 626ef14a...  | c4499a27...         |
#   | 기준 → 연습 (2회차)   | 626ef14a...  | 9244b72c... (다름)   |
#   | 기준 → 연습 (3회차)   | 626ef14a...  | cdd4b630... (다름)   |
#   | 연습만 (2회)         | —            | 9949adf0... (동일)   |
#
# 즉 **단독으로 처리하면 완전히 결정적인데, 다른 해상도의 영상을 앞에서 처리하면
# 비결정적이 된다.** 차이는 반올림 수준이 아니다 — 868프레임 전부가 달라지고
# 최대 121.9픽셀(프레임 높이의 6.4%)이었다.
#
# 그 결과 사용자가 같은 영상을 다시 분석하면 "틀린 동작 45개"가 "52개"가 됐다.
#
# 시도했으나 효과 없었던 것: OMP_NUM_THREADS 등 스레드 수 제한 환경변수.
#
# **해법**: 영상마다 별도 프로세스에서 추출한다. 프로세스 안에서 영상을 하나만
# 처리하면 위 표대로 결정적이다. 추출 자체가 영상당 수십 초 걸리므로 프로세스
# 생성 비용(1~2초)은 무시할 수 있고, 주고받는 배열도 수백 KB 수준이다.
#
# 이 현상은 MediaPipe에서 측정한 것이다. 백엔드를 YOLO로 바꾼 뒤에도 격리를
# 유지하는 이유는, 같은 종류의 상태 공유가 없다고 확인한 것이 아니기 때문이다.
# 비용이 거의 없으므로 안전한 쪽을 택한다.


def _extract_entry(video_path, model_path, conf_thresh, start_sec, end_sec, cwd):
    """자식 프로세스 진입점. `PoseSequence`를 만들 재료만 돌려준다.

    spawn 방식이라 자식은 모듈을 새로 import한다. 그래서 부모의 작업 디렉터리와
    import 경로를 명시적으로 맞춰준다.
    """
    os.chdir(cwd)
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    seq = extract_sequence(video_path, model_path, conf_thresh, start_sec, end_sec)
    # PoseSequence를 통째로 피클하지 않고 배열만 넘긴다(의존성 최소화).
    return seq.coords, seq.conf, seq.valid, seq.fps, seq.num_keypoints, seq.meta


def extract_sequence_isolated(video_path, model_path=None, conf_thresh=0.5,
                              start_sec=None, end_sec=None):
    """
    `extract_sequence`를 **별도 프로세스에서** 실행한다. 결과는 동일하되
    재현 가능하다(위 주석 참조).

    프로세스를 못 띄우는 환경에서는 같은 프로세스에서 처리하고 넘어간다 —
    재현성은 잃지만 분석 자체는 되는 편이 낫다.
    """
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    args = (video_path, model_path, conf_thresh, start_sec, end_sec, cwd)

    try:
        # fork가 아니라 spawn을 쓴다. 이미 초기화된 torch 상태를 물려받으면
        # 교착하거나 죽는 경우가 있고, 애초에 "깨끗한 프로세스"를 얻는 것이
        # 이 함수의 목적이다.
        ctx = multiprocessing.get_context('spawn')
        with ctx.Pool(processes=1) as pool:
            coords, conf, valid, fps, k, meta = pool.apply(_extract_entry, args)
    except Exception as e:
        print(f"[경고] 프로세스 격리 추출 실패 → 같은 프로세스에서 처리합니다 "
              f"(재현성이 보장되지 않습니다): {e}")
        return extract_sequence(video_path, model_path, conf_thresh, start_sec, end_sec)

    return PoseSequence(coords=coords, conf=conf, valid=valid, fps=fps,
                        num_keypoints=k, source=video_path, meta=meta)
