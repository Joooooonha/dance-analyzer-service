# tools/eval_invariance.py
"""feature가 촬영 조건 변화에 얼마나 불변인지 측정한다.

`make_variants`의 공간 변형(zoom/shift/roll)은 시간축이 항등이다 —
변형본 프레임 i는 원본 프레임 i와 정확히 같은 순간이다. 따라서 DTW 없이
프레임을 1:1로 비교하면, 두 프레임 사이에 남는 오차는 전부 **feature가
촬영 조건 차이를 걸러내지 못한 양**이다.

이상적으로는:
  zoom  — 각도 불변(0에 가까움), 좌표는 흔들림
  shift — 각도 불변, 좌표는 흔들림
  roll  — 몸통 상대 각도라면 불변 (D5), 좌표는 흔들림

실행 (프로젝트 루트에서):

    python -m tools.eval_invariance --variants data/variants/*.gt.json
"""
import argparse
import glob
import json
import os

import numpy as np

from src.features import build_features
from tools.eval_alignment import get_sequence

CACHE_DIR_DEFAULT = 'data/.seq_cache'


def measure(gt, backend, model_path, conf_thresh, cache_dir, use_cache,
            min_valid_ratio=0.3):
    src_video = gt['source_video']
    var_video = gt['variant_video']

    std_seq = get_sequence(src_video, backend, model_path, conf_thresh,
                           cache_dir, use_cache)
    user_seq = get_sequence(var_video, backend, model_path, conf_thresh,
                            cache_dir, use_cache)

    v2s = gt['variant_to_source']
    n = min(user_seq.n_frames, std_seq.n_frames, len(v2s))

    out = {}
    for kind in ('coord', 'angle'):
        uf = build_features(user_seq, kind)
        sf = build_features(std_seq, kind)
        u_gate = uf.frame_gate(min_valid_ratio)
        s_gate = sf.frame_gate(min_valid_ratio)

        errs = []
        n_gated = 0
        per_feat = [[] for _ in uf.names]
        for i in range(n):
            j = v2s[i]                       # 공간 변형이면 j == i
            if not (u_gate[i] and s_gate[j]):
                n_gated += 1
                continue
            e, _, items, _signed = uf.pairwise_error(i, sf, j)
            if e is None:
                continue
            errs.append(e)
            idx = {nm: k for k, nm in enumerate(uf.names)}
            for nm, v in items:
                per_feat[idx[nm]].append(v)
        if not errs:
            out[kind] = None
            continue
        e = np.array(errs)
        out[kind] = {
            'unit': uf.unit,
            'n': len(errs),
            'ungated': n_gated,
            'mean': float(e.mean()),
            'median': float(np.median(e)),
            'p90': float(np.percentile(e, 90)),
            'per_feature': {
                nm: {'n': len(v),
                     'median': float(np.median(v)) if v else None,
                     'p90': float(np.percentile(v, 90)) if v else None}
                for nm, v in zip(uf.names, per_feat)
            },
        }
    return out


def main():
    ap = argparse.ArgumentParser(description="feature 촬영조건 불변성 측정")
    ap.add_argument('--variants', nargs='+', required=True,
                    help='변형본 gt.json 경로들 (glob 가능)')
    ap.add_argument('--backend', default='yolo')
    ap.add_argument('--model-path', default='models/yolov8n-pose.pt')
    ap.add_argument('--conf-thresh', type=float, default=None)
    ap.add_argument('--cache-dir', default=CACHE_DIR_DEFAULT)
    ap.add_argument('--no-cache', action='store_true')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    paths = []
    for p in args.variants:
        paths.extend(sorted(glob.glob(p)) if any(c in p for c in '*?[') else [p])

    rows = []
    for p in paths:
        with open(p, 'r', encoding='utf-8') as f:
            gt = json.load(f)
        t = gt['transform']
        sp = t.get('spatial')
        label = sp['kind'] if sp else ('reencode' if t['kind'] == 'spatial'
                                       else t['kind'])
        detail = sp or {k: v for k, v in t.items()
                        if k not in ('kind', 'spatial', 'source_video')}
        print(f"\n── {os.path.basename(p)}  [{label}] {detail}")
        res = measure(gt, args.backend, args.model_path, args.conf_thresh,
                      args.cache_dir, not args.no_cache)
        rows.append({'variant': os.path.basename(p), 'kind': t['kind'],
                     'label': label, 'detail': detail, 'result': res})

    print()
    print(f"{'변형':<26} {'coord 평균':>12} {'coord 중앙':>12} "
          f"{'angle 평균':>12} {'angle 중앙':>12} {'제외':>6}")
    print("-" * 86)
    for r in rows:
        c, a = r['result']['coord'], r['result']['angle']
        if not c or not a:
            print(f"{r['variant'][:26]:<26} 측정 불가")
            continue
        print(f"{r['variant'][:26]:<26} {c['mean']:>11.4f}  {c['median']:>11.4f}  "
              f"{a['mean']:>10.2f}도 {a['median']:>10.2f}도 {a['ungated']:>6}")
    print("\ncoord 단위: 프레임 높이 대비 정규화 거리 / angle 단위: 도")

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump({'backend': args.backend, 'rows': rows}, f,
                      ensure_ascii=False, indent=2)
        print(f"저장: {args.out}")


if __name__ == '__main__':
    main()
