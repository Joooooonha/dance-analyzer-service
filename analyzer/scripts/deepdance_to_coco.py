#!/usr/bin/env python3
import os
import glob
import pickle
import json
import numpy as np

# 1) 프로젝트 루트 및 데이터 경로 설정
script_dir = os.path.dirname(os.path.abspath(__file__))
proj_root  = os.path.dirname(script_dir)
anno_dir   = os.path.join(proj_root, "data", "deepdance", "v1", "motion")  # .pkl 파일들 위치
out_json   = os.path.join(proj_root, "data", "gt_annotations.json")
out_npy    = os.path.join(proj_root, "data", "gt_keypoints.npy")

# 2) pkl 파일 목록 수집
pkl_paths = sorted(glob.glob(os.path.join(anno_dir, "*.pkl")))
if not pkl_paths:
    raise FileNotFoundError(f"No .pkl files found in {anno_dir}")

images      = []
annotations = []
all_kps     = []
img_id      = 1

# 3) 각 시퀀스(.pkl) 처리
for pkl_path in pkl_paths:
    seq_name = os.path.splitext(os.path.basename(pkl_path))[0]
    with open(pkl_path, "rb") as f:
        data = pickle.load(f)

    # DeepDance V1 pkl에는 보통 (T,17,2) numpy array 혹은 리스트 형태로 keypoints2d가 들어있습니다.
    kp_array = np.array(data)  # 또는 data["keypoints2d"] 등
    if kp_array.ndim != 3 or kp_array.shape[1] != 17 or kp_array.shape[2] < 2:
        raise ValueError(f"Unexpected shape {kp_array.shape} in {pkl_path}")

    T = kp_array.shape[0]
    for t in range(T):
        kps17 = kp_array[t, :, :2]  # (17,2)
        flat  = []
        for x, y in kps17.tolist():
            flat.extend([float(x), float(y), 2])  # visibility = 2

        # COCO images entry
        images.append({
            "id": img_id,
            "file_name": f"{seq_name}_frame{t:04d}.jpg",
            "width": 1920,
            "height": 1080
        })
        # COCO annotations entry
        annotations.append({
            "id":            img_id,
            "image_id":      img_id,
            "category_id":   1,
            "keypoints":     flat,
            "num_keypoints": 17,
            "bbox":          [0, 0, 1920, 1080],
            "area":          1920 * 1080,
            "iscrowd":       0
        })

        all_kps.append(kps17)
        img_id += 1

# 4) categories 정의 (17 COCO keypoints)
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

# 5) COCO JSON 저장
coco = {
    "images":      images,
    "annotations": annotations,
    "categories":  categories
}
os.makedirs(os.path.dirname(out_json), exist_ok=True)
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(coco, f, ensure_ascii=False, indent=2)
print(f"✅ {out_json} 생성 완료")

# 6) NumPy keypoints 배열 저장
kp_stack = np.stack(all_kps, axis=0)  # shape=(total_frames,17,2)
np.save(out_npy, kp_stack)
print(f"✅ {out_npy} 생성 완료  shape={kp_stack.shape}")