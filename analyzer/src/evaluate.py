# src/evaluate.py
import argparse, os, json, numpy as np
from src.metrics import compute_map, compute_pck

def main(gt_json, gt_npy, pred_json, pred_npy, out_path):
    map_score = compute_map(gt_json, pred_json)
    gt_arr = np.load(gt_npy)
    pred_arr = np.load(pred_npy)
    pck_score = compute_pck(gt_arr, pred_arr, image_size=(480,640), alpha=0.1)

    metrics = {
        'mAP@OKS': round(map_score,3),
        'PCK@0.1': round(pck_score,3)
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved evaluation metrics to {out_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--gt-json',   required=True)
    parser.add_argument('--gt-npy',    required=True)
    parser.add_argument('--pred-json', required=True)
    parser.add_argument('--pred-npy',  required=True)
    parser.add_argument('--out',       required=True)
    args = parser.parse_args()
    main(args.gt_json, args.gt_npy, args.pred_json, args.pred_npy, args.out)