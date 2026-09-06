#!/usr/bin/env python3
import os
import cv2
import json
import pickle
import numpy as np
from src.detection import detect
from src.pose      import extract_keypoints

def main():
    # 1) GT 키포인트 .pkl 파일 목록
    anno_dir = 'data/aistplusplus/annotations'
    pkl_list = sorted([
        os.path.join(anno_dir, f)
        for f in os.listdir(anno_dir)
        if f.endswith('.pkl')
    ])

    pred_kps, images, annotations = [], [], []
    img_id = 1

    # 2) COCO categories 정의
    categories = [{
        "id": 1,
        "name": "person",
        "keypoints": [
            "nose","left_eye","right_eye","left_ear","right_ear",
            "left_shoulder","right_shoulder","left_elbow","right_elbow",
            "left_wrist","right_wrist","left_hip","right_hip",
            "left_knee","right_knee","left_ankle","right_ankle"
        ],
        "skeleton": [
            [16,14],[14,12],[17,15],[15,13],[12,13],
            [6,12],[7,13],[6,7],[6,8],[7,9],
            [8,10],[9,11],[2,3],[1,2],[1,3]
        ]
    }]

    for pkl_path in pkl_list:
        seq = os.path.splitext(os.path.basename(pkl_path))[0]

        # 3) .pkl 로드 → 2D 키포인트 배열 (T,17,2)
        with open(pkl_path, 'rb') as f:
            raw = pickle.load(f)
        arr = np.array(raw.get('keypoints2d', raw.get('keypoints', [])))
        T = arr.shape[0]

        # 4) 대응하는 비디오 열기
        video_path = f'data/aist_videos/{seq}.mp4'
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")
        cap = cv2.VideoCapture(video_path)

        # 5) 프레임 단위로 예측 및 COCO 엔트리 작성
        for t in range(T):
            ret, frame = cap.read()
            if not ret:
                break  # 프레임 부족 시 중단

            # 5-1) 모델 예측 → (17,2) keypoints
            kps17 = extract_keypoints(detect(frame))
            pred_kps.append(kps17)

            # 5-2) COCO images 항목
            filename = f"{seq}_frame{t:04d}.jpg"
            images.append({
                "id": img_id,
                "file_name": filename,
                "width": frame.shape[1],
                "height": frame.shape[0]
            })

            # 5-3) COCO annotations 항목
            flat = []
            for x, y in kps17:
                flat.extend([float(x), float(y), 2])  # visibility=2
            annotations.append({
                "id": img_id,
                "image_id": img_id,
                "category_id": 1,
                "keypoints": flat,
                "num_keypoints": len(kps17),
                "bbox": [0, 0, frame.shape[1], frame.shape[0]],
                "area": frame.shape[1] * frame.shape[0],
                "iscrowd": 0
            })

            img_id += 1

        cap.release()

    # 6) 예측 keypoints 저장 (.npy)
    os.makedirs('data', exist_ok=True)
    np.save('data/pred_keypoints.npy', np.stack(pred_kps, axis=0))

    # 7) COCO 형식의 pred_annotations.json 저장
    coco_pred = {
        "images": images,
        "annotations": annotations,
        "categories": categories
    }
    with open('data/pred_annotations.json', 'w') as f:
        json.dump(coco_pred, f, indent=2)

    print("✅ Prediction JSON/NPY 생성 완료")

if __name__ == '__main__':
    main()