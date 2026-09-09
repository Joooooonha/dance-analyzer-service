# src/pose_rtmpose.py
"""RTMPose 백엔드 (rtmlib + onnxruntime 경로).

RTMPose는 보통 MMPose 위에서 쓰지만, **mmcv는 Apple Silicon에서 빌드가
까다롭기로 악명 높다.** rtmlib은 공개된 ONNX 가중치를 onnxruntime으로 직접
돌리는 경량 래퍼라 mmcv 없이 동작한다 (TASKS.md D11).

ViTPose와 마찬가지로 top-down이라 사람 bbox가 먼저 필요하다. 폐기된 hybrid와
달리 crop을 직접 하지 않고 라이브러리가 종횡비를 지키며 정규화한다.

가중치는 최초 실행 시 자동 다운로드된다 (~99MB).
"""
import numpy as np

# rtmlib이 제공하는 RTMPose-l (COCO17, body7 학습, 384x288 입력)
DEFAULT_ONNX = (
    'https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/'
    'rtmpose-l_simcc-body7_pt-body7_420e-384x288-3f5a1437_20230504.zip'
)
DEFAULT_INPUT_SIZE = (288, 384)   # (w, h)


class RTMPoseBackend:
    def __init__(self, onnx_model: str = DEFAULT_ONNX,
                 model_input_size=DEFAULT_INPUT_SIZE, device: str = 'cpu'):
        from rtmlib import RTMPose
        # onnxruntime의 CoreML/MPS 경로는 환경에 따라 불안정해서 기본은 cpu.
        self.model = RTMPose(onnx_model=onnx_model,
                             model_input_size=model_input_size,
                             backend='onnxruntime', device=device)

    def extract_keypoints(self, frame, bboxes=None):
        """
        frame:  BGR (H, W, 3)
        bboxes: [[x1, y1, x2, y2], ...]. 비어 있으면 전체 프레임.
        returns: [(x_norm, y_norm, score), ...] 를 사람 수만큼
        """
        H, W = frame.shape[:2]
        if not bboxes:
            bboxes = [[0, 0, W, H]]
        bb = np.asarray(bboxes, dtype=np.float32)

        kps, scores = self.model(frame, bboxes=bb)
        kps = np.asarray(kps)
        scores = np.asarray(scores)

        out = []
        for person_kp, person_sc in zip(kps, scores):
            out.append([(float(x) / W, float(y) / H, float(s))
                        for (x, y), s in zip(person_kp[:, :2], person_sc)])
        return out


_CACHE = {}


def get_model(onnx_model: str = DEFAULT_ONNX) -> RTMPoseBackend:
    if onnx_model not in _CACHE:
        _CACHE[onnx_model] = RTMPoseBackend(onnx_model=onnx_model)
    return _CACHE[onnx_model]


def extract_keypoints(frame, bboxes, onnx_model: str = DEFAULT_ONNX):
    return get_model(onnx_model).extract_keypoints(frame, bboxes)
