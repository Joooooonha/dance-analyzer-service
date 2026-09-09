"""YOLO-pose 키포인트 추출.

`model-research/src/pose_yolo.py`를 서비스용으로 옮긴 것이다. 달라진 점은
**장치 자동 선택** 하나다 — 연구 코드는 맥에서만 돌아 `device='mps'`가 하드코딩돼
있었는데, 분석 서버는 Asahi Linux(aarch64)에서 돌기 때문에 그대로 두면 죽는다.

**왜 MediaPipe가 아니라 YOLO인가** (TASKS-SERVICE.md 포즈 모델 결정 근거):

1. MediaPipe 0.10.x에는 **linux aarch64 휠이 없다.** 분석 서버가 Asahi Linux라
   설치 자체가 안 된다.
2. 뼈 안정성 실측에서 MediaPipe Full이 5개 중 꼴찌였다
   (0.0189 vs yolov8n 0.0143, yolo11x 0.0127).
3. **정렬 정확도를 측정할 때 쓴 백엔드가 YOLO였다.** 서비스가 MediaPipe로 돌면
   문서의 검증 수치가 서비스에 해당한다고 말할 수 없다. 같은 백엔드를 쓰면
   연구에서 잰 값이 그대로 서비스의 값이 된다.
"""
import numpy as np

# COCO17 순서. engine.sequence.JOINT_MAP[17]과 같은 인덱스 체계다.
NUM_KEYPOINTS = 17

# 기본 모델. 분석 서버(Asahi Linux, CPU 전용)에서 실측해 고른 값이다.
#
# | 모델 | 프레임당 | 영상 2개 분석 | 평균 오차 | 중앙 오차 |
# |---|---|---|---|---|
# | yolov8n-pose | 0.097s | 201초 | 26.28도 | 22.05도 |
# | **yolo11n-pose** | **0.091s** | **171초** | **24.85도** | **20.17도** |
# | yolo11x-pose | 2.068s | 약 74분 | — | — |
#
# yolo11n이 v8n보다 **빠르면서 오차도 낮다.** 둘 다 2회 반복에서 재현됐다.
#
# yolo11x는 뼈 안정성 1위(0.0127)지만 CPU에서 21배 느려 쓸 수 없다.
# 맥북(MPS)에서는 4.6배 차이였는데, Asahi Linux에는 MPS도 CUDA도 없어
# 순수 CPU로 돌기 때문에 격차가 훨씬 커진다. 가속기가 생기면 재검토한다.
DEFAULT_MODEL = 'yolo11n-pose.pt'


def _pick_device():
    """
    쓸 수 있는 가속 장치를 고른다.

    연구 코드는 `device='mps'`가 하드코딩돼 있었다. 맥에서만 돌렸기 때문인데,
    분석 서버(Asahi Linux)에는 MPS도 CUDA도 없어서 그대로 두면 실행이 실패한다.
    """
    try:
        import torch
        if torch.cuda.is_available():
            return 'cuda'
        # MPS는 애플 실리콘 + macOS 조합에서만 존재한다. Asahi Linux에는 없다.
        if getattr(torch.backends, 'mps', None) and torch.backends.mps.is_available():
            return 'mps'
    except Exception:
        pass
    return 'cpu'


class YoloPoseExtractor:
    """프레임 하나에서 사람 한 명의 키포인트를 뽑는다."""

    def __init__(self, model_path: str = DEFAULT_MODEL, device: str = None):
        from ultralytics import YOLO

        self.model_path = model_path
        self.device = device or _pick_device()
        # 가중치가 없으면 ultralytics가 최초 실행 시 자동으로 받는다.
        self.model = YOLO(model_path)
        self.model.to(self.device)

    def extract(self, frame):
        """
        frame: BGR (H, W, 3)

        returns: (17, 3) 배열 [x_norm, y_norm, conf] 또는 검출 실패 시 None.
                 x/y는 0~1로 정규화한다 — `build_sequence`가 등방 정규화를
                 다시 적용하므로 여기서는 프레임 크기로만 나눈다.
        """
        H, W = frame.shape[:2]
        results = self.model(frame, device=self.device, verbose=False)[0]

        kps = getattr(results, 'keypoints', None)
        if kps is None or kps.data is None or len(kps.data) == 0:
            return None

        arr = kps.data.cpu().numpy()      # (사람 수, 17, 3)

        # **사람은 찾았는데 키포인트가 비어 있는 경우가 있다.** 그때 모양이
        # (1, 0, 3)으로 와서, 사람 수만 보는 검사(`arr.shape[0] == 0`)를 통과한 뒤
        # 대입에서 터진다:
        #   ValueError: could not broadcast input array from shape (0,) into shape (17,)
        # 실제 영상(user_dancer.MOV)에서 발생했다. 관절 수까지 확인해야 한다.
        if arr.ndim != 3 or arr.shape[0] == 0 or arr.shape[1] != NUM_KEYPOINTS:
            return None

        # 다중 인물 선택 로직은 보류 상태다(TASKS.md D10).
        # 테스트 영상에 배경 인물이 없어 첫 번째를 그대로 쓴다.
        #
        # **float64로 나눈다.** 연구 코드(`model-research/src/pose_yolo.py`)가
        # 파이썬 float(=float64)로 나눈 뒤 `build_sequence`에서 float32로 변환하는데,
        # 여기서 float32로 먼저 나누면 반올림이 달라져 결과가 미세하게 어긋난다.
        # 연구에서 잰 수치를 서비스가 그대로 재현해야 하므로 계산 순서를 맞춘다.
        person = arr[0].astype(np.float64)

        out = np.empty((NUM_KEYPOINTS, 3), dtype=np.float64)
        out[:, 0] = person[:, 0] / W
        out[:, 1] = person[:, 1] / H
        out[:, 2] = person[:, 2]
        return out
