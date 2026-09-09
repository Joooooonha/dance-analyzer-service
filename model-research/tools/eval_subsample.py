# tools/eval_subsample.py
"""프레임 서브샘플링이 정렬 품질을 얼마나 떨어뜨리는지 측정한다.

배포 비용에 직결되는 결정이다. 30fps를 전부 추론할 필요가 없다면 k배만큼
연산이 줄어든다 — 맥미니/EC2에서 무거운 모델을 쓸 수 있느냐가 여기서 갈린다.
문제는 시간 해상도도 같이 낮아진다는 것이고, 그 트레이드오프를 수치로 재는 게
이 도구다.

변형본의 dense GT를 쓰므로 앵커 없이 측정 가능하다. **포즈 추정은 다시 돌리지
않는다** — 캐시된 시퀀스에서 k번째 프레임만 골라내는 방식이라, 실제로 k배
띄엄띄엄 추론했을 때와 같은 입력이 된다.

주의: k로 서브샘플링하면 정렬이 표현할 수 있는 최소 단위가 k프레임이므로
오차의 하한이 대략 k/2 프레임이다. 즉 오차 증가의 일부는 알고리즘 열화가
아니라 해상도 자체의 한계다. 표에 그 하한을 같이 표시한다.

실행 (프로젝트 루트에서):

    python -m tools.eval_subsample \
        --gt data/variants/user_dancer__local0.50.gt.json --backend yolo
"""
import argparse
import json
import os

import numpy as np

from src.dtw_compare import align
from src.features import build_features
from src.sequence import PoseSequence
from tools.eval_alignment import get_sequence, path_lookup

CACHE_DIR_DEFAULT = 'data/.seq_cache'


def subsample(seq: PoseSequence, k: int) -> PoseSequence:
    """k프레임마다 하나씩 남긴다. fps도 그만큼 낮아진다."""
    if k <= 1:
        return seq
    return PoseSequence(
        coords=seq.coords[::k], conf=seq.conf[::k], valid=seq.valid[::k],
        fps=seq.fps / k, num_keypoints=seq.num_keypoints,
        source=seq.source, meta=dict(seq.meta))


def main():
    ap = argparse.ArgumentParser(description="프레임 서브샘플링 트레이드오프 측정")
    ap.add_argument('--gt', required=True, help='변형본 gt.json (dense GT)')
    ap.add_argument('--backend', default='yolo')
    ap.add_argument('--model-path', default='models/yolov8n-pose.pt')
    ap.add_argument('--conf-thresh', type=float, default=None)
    ap.add_argument('--feature', choices=['angle', 'coord'], default='angle')
    ap.add_argument('--rates', type=int, nargs='+', default=[1, 2, 3, 4, 6],
                    help='서브샘플링 배수. 1=원본(30fps), 2=15fps, 3=10fps ...')
    ap.add_argument('--window', type=int, default=15)
    ap.add_argument('--cache-dir', default=CACHE_DIR_DEFAULT)
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    with open(args.gt, 'r', encoding='utf-8') as f:
        gt = json.load(f)
    v2s = gt['variant_to_source']
    fps0 = float(gt['fps'])

    std_seq = get_sequence(gt['source_video'], args.backend, args.model_path,
                           args.conf_thresh, args.cache_dir, True)
    user_seq = get_sequence(gt['variant_video'], args.backend, args.model_path,
                            args.conf_thresh, args.cache_dir, True)

    rows = []
    for k in args.rates:
        us, ss = subsample(user_seq, k), subsample(std_seq, k)
        uf, sf = build_features(us, args.feature), build_features(ss, args.feature)
        path = align(uf, sf, window=args.window)
        lut = path_lookup(path, key_idx=0)      # {user_sub_idx: [std_sub_idx...]}

        errs = []
        n_var_sub = min(us.n_frames, (len(v2s) + k - 1) // k)
        for i in range(n_var_sub):
            preds = lut.get(i)
            if not preds:
                continue
            orig_i = i * k                       # 서브샘플 인덱스 -> 원본 프레임
            if orig_i >= len(v2s):
                continue
            pred_std_orig = float(np.median(preds)) * k
            errs.append(abs(pred_std_orig - v2s[orig_i]))
        if not errs:
            continue
        e = np.array(errs)
        rows.append({
            'k': k,
            'eff_fps': fps0 / k,
            'n': len(errs),
            'median_sec': float(np.median(e) / fps0),
            'mean_sec': float(e.mean() / fps0),
            'p90_sec': float(np.percentile(e, 90) / fps0),
            'within_2f_pct': float((e <= 2).mean() * 100),
            'within_5f_pct': float((e <= 5).mean() * 100),
            'resolution_floor_sec': (k / 2) / fps0,
            'cost_ratio': 1.0 / k,
        })

    print(f"\n변형: {os.path.basename(args.gt)}  "
          f"[{gt['transform']['kind']}]  feature={args.feature}")
    print(f"{'배수':>4}{'유효fps':>9}{'연산량':>8}{'중앙(초)':>10}{'평균(초)':>10}"
          f"{'p90(초)':>10}{'해상도하한':>11}{'±5f내':>8}")
    print("-" * 72)
    for r in rows:
        print(f"{'x' + str(r['k']):>4}{r['eff_fps']:>9.1f}"
              f"{r['cost_ratio'] * 100:>7.0f}%{r['median_sec']:>10.3f}"
              f"{r['mean_sec']:>10.3f}{r['p90_sec']:>10.3f}"
              f"{r['resolution_floor_sec']:>11.3f}{r['within_5f_pct']:>7.1f}%")
    print("\n해상도하한 = k/2 프레임. 이보다 작은 오차는 원리적으로 표현 불가하므로,")
    print("             오차가 이 값 근처면 알고리즘이 아니라 해상도의 한계다.")

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump({'gt': args.gt, 'backend': args.backend,
                       'feature': args.feature, 'rows': rows}, f,
                      ensure_ascii=False, indent=2)
        print(f"저장: {args.out}")


if __name__ == '__main__':
    main()
