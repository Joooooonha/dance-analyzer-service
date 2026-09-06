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
# 모듈 레벨 래퍼: 싱글톤으로 만들어 두고, 
# make_pose_pipeline에서 바로 import 할 수 있게 합니다.

_mediapipe_pose = MediapipePose()

def extract_keypoints(frame, bboxes):
    """
    모듈 레벨 extract_keypoints 함수.
    src.main 의 make_pose_pipeline 에서 import 됩니다.
    """
    return _mediapipe_pose.get_keypoints(frame, bboxes)