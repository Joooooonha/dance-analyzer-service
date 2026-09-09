# src/pose_hybrid.py

import cv2
import mediapipe as mp
from .pose_backend import PoseBackend

class MediapipePose(PoseBackend):
    def __init__(self,
                 model_complexity: int = 0,
                 min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5):
        # MediaPipe 포즈 모델 초기화
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

    def get_keypoints(self, frame, bboxes):
            """
            frame: BGR 이미지 (H, W, 3)
            bboxes: [[x1, y1, x2, y2], ...]
            returns: 사람 수 만큼 [[(x,y,v), ...], ...]
            """
            out = []
            H0, W0 = frame.shape[:2]

            # ROI 리스트: 사람이 검출되지 않으면 전체 프레임 fallback 준비
            rois = bboxes if bboxes else [[0, 0, W0, H0]]

            # 1) ROI마다 BlazePose 시도
            for x1, y1, x2, y2 in rois:
                crop = frame[int(y1):int(y2), int(x1):int(x2)]
                if crop.size == 0:
                    out.append(None)
                    continue

                rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                res = self.pose.process(rgb)
                if not res.pose_landmarks:
                    out.append(None)
                    continue

                # 성공한 ROI: 전체 프레임 기준으로 정규화된 좌표 계산
                roi_h, roi_w = crop.shape[:2]
                full_coords = []
                for lm in res.pose_landmarks.landmark:
                    abs_x = x1 + lm.x * roi_w
                    abs_y = y1 + lm.y * roi_h
                    full_coords.append((abs_x / W0, abs_y / H0, lm.visibility))

                out.append(full_coords)

            # 2) 모든 ROI가 실패했으면 전체 프레임 대상으로 한 번 더 시도
            if all(o is None for o in out):
                out.clear()
                rgb_full = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res_full = self.pose.process(rgb_full)
                if res_full.pose_landmarks:
                    full_coords = [
                        (lm.x, lm.y, lm.visibility)
                        for lm in res_full.pose_landmarks.landmark
                    ]
                    out.append(full_coords)
                else:
                    out.append(None)

            return out
# ──────────────────────────────────────────────────
# complexity별 인스턴스 캐시.
# 예전에는 모듈 로드 시점에 complexity=0(가장 가벼운 모델)으로 싱글톤을 만들어서
# 모델 크기를 바꿀 방법이 없었다. 이제 지연 생성하고 complexity로 캐싱한다.

_POSE_CACHE = {}


def get_pose(model_complexity: int = 0) -> MediapipePose:
    if model_complexity not in _POSE_CACHE:
        _POSE_CACHE[model_complexity] = MediapipePose(
            model_complexity=model_complexity)
    return _POSE_CACHE[model_complexity]


def extract_keypoints(frame, bboxes, model_complexity: int = 0):
    """src.pose_factory.make_pose_pipeline에서 사용된다."""
    return get_pose(model_complexity).get_keypoints(frame, bboxes)