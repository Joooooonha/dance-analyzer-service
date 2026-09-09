#!/usr/bin/env python3
import argparse
import json
import numpy as np
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval

def compute_pck(gt_kps, pred_kps, thr=0.1):
    """
    gt_kps, pred_kps: arrays of shape (F, N, 2)
    thr: fraction of image diagonal for tolerance
    """
    F, N, _ = gt_kps.shape
    diag = np.linalg.norm([1920, 1080])  # image diagonal
    tol = thr * diag

    correct = 0
    total   = F * N
    for f in range(F):
        dists = np.linalg.norm(gt_kps[f] - pred_kps[f], axis=1)
        correct += np.sum(dists <= tol)
    return correct / total

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--gt-json",   required=True, help="path to GT COCO-format JSON")
    p.add_argument("--pred-json", required=True, help="path to Pred COCO-format JSON")
    p.add_argument("--gt-npy",    required=True, help="path to GT keypoints .npy")
    p.add_argument("--pred-npy",  required=True, help="path to Pred keypoints .npy")
    p.add_argument("--out",       required=True, help="output metrics JSON")
    args = p.parse_args()

    # 1) COCO mAP
    coco_gt = COCO(args.gt_json)
    # ensure 'info' exists to satisfy loadRes
    if "info" not in coco_gt.dataset:
        coco_gt.dataset["info"] = {}

    coco_dt = coco_gt.loadRes(args.pred_json)
    cocoEval = COCOeval(coco_gt, coco_dt, iouType="keypoints")
    cocoEval.evaluate()
    cocoEval.accumulate()
    cocoEval.summarize()

    map50_95 = cocoEval.stats[0]  # AP @[.5:.95]
    map50     = cocoEval.stats[1]  # AP @ .50

    # 2) PCK
    gt_kps   = np.load(args.gt_npy)   # shape: (F, N, 2)
    pred_kps = np.load(args.pred_npy)
    pck_10   = compute_pck(gt_kps, pred_kps, thr=0.10)
    pck_05   = compute_pck(gt_kps, pred_kps, thr=0.05)

    # 3) Save metrics
    metrics = {
        "mAP50:95": float(map50_95),
        "mAP50":    float(map50),
        "PCK@0.10": pck_10,
        "PCK@0.05": pck_05
    }
    with open(args.out, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"✅ Metrics saved to {args.out}")