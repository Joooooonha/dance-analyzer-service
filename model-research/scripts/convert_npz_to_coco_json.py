NPZ_DIR = "/Users/parkjooha/Coding/Dongguk/25-1/개별연구/project/street-dance/data/gt_npz"

import os
import json
import numpy as np
import re
from tqdm import tqdm

# === 사용자 환경에 맞게 수정하세요 ===
NPZ_DIR = '/Users/parkjooha/Coding/Dongguk/25-1/개별연구/project/street-dance/data/gt_npz'  # npz들이 모여있는 폴더
OUT_JSON = '/Users/parkjooha/Coding/Dongguk/25-1/개별연구/project/street-dance/gt_annotation/gt.json'
IMAGE_PREFIX = 'img'        # 이미지 prefix, 파일명 형식: img-000433.npz
NUM_KEYPOINTS = 17          # COCO 기준 (17), 필요시 33 등으로 변경
CATEGORY_ID = 1

# BlazePose → COCO 변환을 위한 joint order 매핑(예시, 실제 값에 맞게 조정)
# 예: COCO17_JOINT_ORDER = [0,2,5,7,8,11,12,13,14,15,16,23,24,25,26,27,28]
JOINT_ORDER = list(range(NUM_KEYPOINTS))

def npz_to_coco_json(npz_dir, out_json):
    npz_files = sorted([f for f in os.listdir(npz_dir) if f.endswith('.npz')])
    images = []
    annotations = []
    candidate_keys = ['coco_joints2d', 'keypoints', 'arr_0']  # 실제 key 이름 맞게 추가

    for npz_file in tqdm(npz_files, desc="NPZ→COCO 변환"):
        # 프레임 id 추출
        m = re.search(r'img-(\d{6})\.npz', npz_file)
        if m:
            frame_id = int(m.group(1))
        else:
            frame_id = int(os.path.splitext(npz_file)[0].split('-')[-1])  # 예외 처리

        img_name = f"{IMAGE_PREFIX}-{str(frame_id).zfill(6)}.jpg"
        npz_path = os.path.join(npz_dir, npz_file)
        data = np.load(npz_path)
        # 실제 key 이름 자동 탐색
        for key in candidate_keys:
            if key in data:
                kp_data = data[key]
                break
        else:
            raise KeyError(f"{npz_path}에서 keypoints 정보가 없습니다. 실제 key: {data.files}")

        # joint order 변환 필요시(BlazePose→COCO), 아니라면 생략
        if kp_data.shape[0] != NUM_KEYPOINTS:
            kp_data = kp_data[JOINT_ORDER]

        kp_list = []
        for i in range(NUM_KEYPOINTS):
            x, y = kp_data[i][0], kp_data[i][1]
            v = kp_data[i][2] if kp_data.shape[1] > 2 else 1.0
            kp_list.extend([float(x), float(y), float(v)])

        images.append({"id": frame_id, "file_name": img_name})
        annotations.append({
            "id": frame_id,
            "image_id": frame_id,
            "category_id": CATEGORY_ID,
            "keypoints": kp_list,
            "num_keypoints": NUM_KEYPOINTS
        })

    coco_dict = {
        "info": {"description": "Converted from npz files"},
        "images": images,
        "annotations": annotations,
        "categories": [{
            "id": CATEGORY_ID,
            "name": "person",
            "supercategory": "person",
            "keypoints": [
                # COCO keypoint names(순서대로), 필요시 맞게 수정
                "nose", "left_eye", "right_eye", "left_ear", "right_ear",
                "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
                "left_wrist", "right_wrist", "left_hip", "right_hip",
                "left_knee", "right_knee", "left_ankle", "right_ankle"
            ][:NUM_KEYPOINTS],
            "skeleton": [
                [16, 14], [14, 12], [17, 15], [15, 13], [12, 13],
                [6, 12], [7, 13], [6, 7], [6, 8], [7, 9],
                [8, 10], [9, 11], [2, 3], [1, 2], [1, 3]
            ]
        }]
    }
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(coco_dict, f, ensure_ascii=False, indent=2)
    print(f"COCO-format json 저장 완료: {out_json}")

if __name__ == '__main__':
    npz_to_coco_json(NPZ_DIR, OUT_JSON)