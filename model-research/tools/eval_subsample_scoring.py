# tools/eval_subsample_scoring.py
"""서브샘플링이 **채점 품질**에 미치는 영향을 측정한다.

`tools/eval_subsample.py`는 정렬(L2)만 쟀다. 정렬이 멀쩡해도 채점은 다를 수 있다 —
프레임을 띄엄띄엄 보면 빠른 동작의 순간적인 오차를 통째로 놓칠 수 있기 때문이다.
"평균은 비슷한데 큰 오차 순간을 못 잡는" 상황이 실제로 일어나는지가 관심사다.

방법: 같은 영상 쌍을 여러 배수로 서브샘플링해 채점하고, **전체 프레임(k=1)을
기준으로** 통계가 얼마나 달라지는지 본다. 앵커가 필요 없다 — k=1 자체가 기준이다.

특히 두 가지를 본다.
  1. 평균/중앙 오차가 유지되는가 (전체적인 점수 왜곡)
  2. **p90·최대 오차가 유지되는가** — 큰 오차 순간을 놓치면 여기가 먼저 무너진다.
     사용자에게 "여기가 틀렸다"고 짚어주는 게 서비스의 핵심이므로 평균보다 중요하다.

실행 (프로젝트 루트에서):

    python -m tools.eval_subsample_scoring \
        --pro data/videos/real/pro_dancer.mp4 \
        --user data/videos/real/user_dancer.mp4 --backend yolo
"""
import argparse
import json
import os

import numpy as np

from src.dtw_compare import compare_sequences
from src.features import build_features
from tools.eval_alignment import get_sequence
from tools.eval_subsample import subsample

CACHE_DIR_DEFAULT = 'data/.seq_cache'


def main():
    ap = argparse.ArgumentParser(description="서브샘플링의 채점 품질 영향 측정")
    ap.add_argument('--pro', required=True)
    ap.add_argument('--user', required=True)
    ap.add_argument('--backend', default='yolo')
    ap.add_argument('--model-path', default='models/yolov8n-pose.pt')
    ap.add_argument('--conf-thresh', type=float, default=None)
    ap.add_argument('--feature', choices=['angle', 'coord'], default='angle')
    ap.add_argument('--rates', type=int, nargs='+', default=[1, 2, 3, 4, 6])
    ap.add_argument('--window', type=int, default=15)
    ap.add_argument('--psi-sec', type=float, default=3.0)
    ap.add_argument('--cache-dir', default=CACHE_DIR_DEFAULT)
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    std_seq = get_sequence(args.pro, args.backend, args.model_path,
                           args.conf_thresh, args.cache_dir, True)
    user_seq = get_sequence(args.user, args.backend, args.model_path,
                            args.conf_thresh, args.cache_dir, True)

    rows = []
    for k in args.rates:
        us, ss = subsample(user_seq, k), subsample(std_seq, k)
        uf, sf = build_features(us, args.feature), build_features(ss, args.feature)
        psi = int(round(args.psi_sec * us.fps)) if args.psi_sec else None
        res = compare_sequences(uf, sf, window=args.window, psi=psi,
                                max_time_diff=0.6, min_separation=0.3)
        st = res['stats']
        rows.append({
            'k': k, 'eff_fps': std_seq.fps / k,
            'score': res['score'],
            'mean_error': st['mean_error'],
            'median_error': st['median_error'],
            'p90_error': st['p90_error'],
            'max_error': st['max_error'],
            'scored_pairs': st['scored_pairs'],
            'n_details': len(res['details']),
        })

    base = rows[0]
    unit = 'deg' if args.feature == 'angle' else 'norm'
    print(f"\n기준 {os.path.basename(args.pro)} vs {os.path.basename(args.user)}  "
          f"backend={args.backend} feature={args.feature}")
    print(f"{'배수':>4}{'유효fps':>9}{'점수':>8}{'평균':>9}{'중앙':>9}"
          f"{'p90':>9}{'최대':>9}{'채점쌍':>8}")
    print("-" * 66)
    for r in rows:
        print(f"{'x' + str(r['k']):>4}{r['eff_fps']:>9.1f}{r['score']:>8.1f}"
              f"{r['mean_error']:>9.2f}{r['median_error']:>9.2f}"
              f"{r['p90_error']:>9.2f}{r['max_error']:>9.2f}{r['scored_pairs']:>8}")

    print(f"\n(단위 {unit}) — k=1 대비 변화율")
    print(f"{'배수':>4}{'평균':>10}{'중앙':>10}{'p90':>10}{'최대':>10}")
    print("-" * 46)
    for r in rows[1:]:
        def d(key):
            b = base[key]
            return (r[key] - b) / b * 100 if b else 0.0
        print(f"{'x' + str(r['k']):>4}{d('mean_error'):>9.1f}%{d('median_error'):>9.1f}%"
              f"{d('p90_error'):>9.1f}%{d('max_error'):>9.1f}%")
    print("\np90/최대가 평균보다 크게 흔들리면 = 큰 오차 순간을 놓치고 있다는 신호")

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump({'pro': args.pro, 'user': args.user,
                       'backend': args.backend, 'feature': args.feature,
                       'rows': rows}, f, ensure_ascii=False, indent=2)
        print(f"저장: {args.out}")


if __name__ == '__main__':
    main()
