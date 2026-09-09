# src/pose_vitpose.py
"""ViTPose 백엔드 (HuggingFace transformers 경로).

top-down 방식이라 사람 bbox가 먼저 필요하다. `src.detection.detect`(YOLO)를
1단계로 쓴다는 점에서 폐기된 hybrid와 구조가 같아 보이지만, 결정적인 차이가
있다 — hybrid는 프레임을 **직접 잘라서**(`frame[y1:y2, x1:x2]`) 포즈 모델에
넘겼고, 그 과정에서 종횡비가 깨지고 경계에서 신체가 잘려 품질이 떨어졌다
(TASKS.md D15). ViTPose의 processor는 bbox를 받아 종횡비를 유지한 채 패딩과
아핀 변환으로 정규화하고, 출력 좌표를 원본 프레임 좌표계로 되돌려준다.
즉 top-down이 문제였던 게 아니라 hybrid의 crop 구현이 문제였다.

모델 가중치는 최초 실행 시 HuggingFace에서 자동 다운로드된다 (~340MB).
"""
import cv2
import numpy as np

DEFAULT_MODEL = 'usyd-community/vitpose-base-simple'


class ViTPose:
    def __init__(self, model_id: str = DEFAULT_MODEL, device: str = None):
        import torch
        from transformers import AutoProcessor, VitPoseForPoseEstimation

        self.torch = torch
        if device is None:
            device = 'mps' if torch.backends.mps.is_available() else 'cpu'
        self.device = device
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = VitPoseForPoseEstimation.from_pretrained(model_id)
        self.model.to(device).eval()

    def extract_keypoints(self, frame, bboxes=None):
        """
        frame:  BGR (H, W, 3)
        bboxes: [[x1, y1, x2, y2], ...] (xyxy). 비어 있으면 전체 프레임을 사용.
        returns: 사람 수만큼 [(x_norm, y_norm, score), ...]
                 좌표는 프레임 크기로 나눈 값 (다른 백엔드와 동일한 규약)
        """
        H, W = frame.shape[:2]
        if not bboxes:
            bboxes = [[0, 0, W, H]]

        # processor는 COCO 형식(x, y, w, h)을 받는다
        coco_boxes = [[float(x1), float(y1), float(x2 - x1), float(y2 - y1)]
                      for x1, y1, x2, y2 in bboxes]

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        inputs = self.processor(rgb, boxes=[coco_boxes], return_tensors='pt')
        inputs = inputs.to(self.device)

        with self.torch.no_grad():
            outputs = self.model(**inputs)

        results = self.processor.post_process_pose_estimation(
            outputs, boxes=[coco_boxes])

        out = []
        for person in results[0]:
            kp = person['keypoints'].cpu().numpy()          # (17, 2) 픽셀 좌표
            sc = person['scores'].cpu().numpy()             # (17,)
            out.append([(float(x) / W, float(y) / H, float(s))
                        for (x, y), s in zip(kp[:, :2], sc)])
        return out


_CACHE = {}


def get_model(model_id: str = DEFAULT_MODEL, device: str = None) -> ViTPose:
    key = (model_id, device)
    if key not in _CACHE:
        _CACHE[key] = ViTPose(model_id=model_id, device=device)
    return _CACHE[key]


def extract_keypoints(frame, bboxes, model_id: str = DEFAULT_MODEL):
    return get_model(model_id).extract_keypoints(frame, bboxes)
