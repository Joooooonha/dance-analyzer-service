# src/detection.py
import cv2
from ultralytics import YOLO

# YOLO 모델 로드
model = YOLO('models/yolov8n.pt')

def detect(frame):
    if frame is None:
        raise ValueError("프레임이 None입니다. 이미지가 제대로 불러와졌는지 확인하세요.")

    results = model(frame, conf=0.1, verbose=False)[0]

    bboxes = []
    # YOLO 클래스별 필터링: COCO에서 person 은 class_id 0
    if results.boxes is not None and results.boxes.xyxy is not None:
        for box, cls in zip(results.boxes.xyxy, results.boxes.cls):
            if int(cls) != 0:
                continue
            coords = box.tolist()
            if isinstance(coords, list) and len(coords) == 4:
                bboxes.append(coords)
    return bboxes