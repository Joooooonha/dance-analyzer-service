# src/pose_backend.py
from abc import ABC, abstractmethod

class PoseBackend(ABC):
    @abstractmethod
    def get_keypoints(self, frame, bboxes):
        """
        frame: BGR 이미지
        bboxes: [[x1,y1,x2,y2],…]
        returns: list of 키포인트 리스트, e.g. [ [(x,y,v),…], … ]
        """
        pass
    