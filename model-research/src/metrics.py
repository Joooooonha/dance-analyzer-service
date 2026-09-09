# src/metrics.py
import numpy as np
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval

# COCO 17 키포인트 인덱스 매핑 (MediaPipe BlazePose 33 랜드마크 기준)
# 0: nose, 2: left eye, 5: right eye, 7: left ear, 8: right ear,
# 11: left shoulder, 12: right shoulder, 13: left elbow, 14: right elbow,
# 15: left wrist, 16: right wrist, 23: left hip, 24: right hip,
# 25: left knee, 26: right knee, 27: left ankle, 28: right ankle

COCO17_JOINT_ORDER = [0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]

COCO17_SKELETON = [
    [16, 14], [14, 12], [17, 15], [15, 13], [12, 13],
    [6, 12],  [7, 13],  [6, 7],   [6, 8],   [7, 9],
    [8, 10],  [9, 11],  [2, 3],   [1, 2],   [1, 3]
]

def compute_map(gt_json, pred_json):
    coco_gt   = COCO(gt_json)
    coco_dt   = coco_gt.loadRes(pred_json)
    coco_eval = COCOeval(coco_gt, coco_dt, iouType='keypoints')
    coco_eval.evaluate()
    coco_eval.accumulate()
    coco_eval.summarize()
    return coco_eval.stats[0]  # mAP@OKS=0.50:0.05:0.95


def compute_pck(gt_kps, pred_kps, image_size, alpha=0.1):
    h, w    = image_size
    thresh  = alpha * np.hypot(h, w)
    # gt_kps, pred_kps: (N,17,2)
    dists   = np.linalg.norm(gt_kps - pred_kps, axis=2)  # (N,17)
    correct = (dists <= thresh)
    return correct.sum() / correct.size  # PCK@alpha
