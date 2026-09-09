# tools/eval_alignment.py
"""DTW 시간축 정렬의 품질(L2)을 측정한다.

두 종류의 정답을 모두 받는다 (TASKS.md 측정 기준).

  variant 모드 — `tools.make_variants`가 만든 dense GT.
                 모든 프레임의 대응 정답을 알고 있다.
  anchors 모드 — `tools.annotate_anchors`로 사람이 찍은 sparse GT.
                 현실 촬영본에서의 검증.

실행 (프로젝트 루트에서):

    python -m tools.eval_alignment --mode variant \
        --gt data/variants/user_dancer__offset60.gt.json --backend yolo

    python -m tools.eval_alignment --mode anchors \
        --gt data/anchors/real.json --backend yolo --windows 15 60 none

포즈 추출 결과는 캐시된다 (같은 영상/백엔드면 재추출하지 않음).
window를 여러 개 주면 추출은 한 번만 하고 정렬만 반복한다.
"""
import argparse
import hashlib
import json
import os

import numpy as np

from src.dtw_compare import align
from src.extract import extract_pose_sequence
from src.features import build_features
from src.sequence import PoseSequence

CACHE_DIR_DEFAULT = 'data/.seq_cache'


def cache_path(cache_dir, video, backend, conf_thresh, start_sec=None, end_sec=None):
    key = f"{os.path.abspath(video)}|{backend}|{conf_thresh}|{start_sec}|{end_sec}"
    try:
        key += f"|{os.path.getmtime(video)}"
    except OSError:
        pass
    h = hashlib.md5(key.encode()).hexdigest()[:12]
    stem = os.path.splitext(os.path.basename(video))[0]
    return os.path.join(cache_dir, f"{stem}_{backend}_{h}.npz")


def get_sequence(video, backend, model_path, conf_thresh, cache_dir, use_cache=True,
                 start_sec=None, end_sec=None):
    os.makedirs(cache_dir, exist_ok=True)
    cp = cache_path(cache_dir, video, backend, conf_thresh, start_sec, end_sec)
    if use_cache and os.path.exists(cp):
        print(f"  캐시 사용: {os.path.basename(video)}")
        seq = PoseSequence.load(cp)
        seq.meta.setdefault('source_start_frame',
                            int(round(start_sec * seq.fps)) if start_sec else 0)
        return seq
    seq, _ = extract_pose_sequence(video, backend, model_path=model_path,
                                   conf_thresh=conf_thresh, verbose=True,
                                   progress_every=0,
                                   start_sec=start_sec, end_sec=end_sec)
    seq.save(cp)
    return seq


def path_lookup(path, key_idx=1):
    """
    warping path를 dict로 뒤집는다.
    key_idx=1이면 {std_idx: [user_idx...]}, 0이면 {user_idx: [std_idx...]}.
    """
    out = {}
    for u, s in path:
        k, v = (s, u) if key_idx == 1 else (u, s)
        out.setdefault(int(k), []).append(int(v))
    return out


def summarize(errors_sec, errors_frames, label, extra=None):
    e = np.asarray(errors_sec, dtype=float)
    f = np.asarray(errors_frames, dtype=float)
    row = {
        'label': label,
        'n': int(e.size),
        'mean_sec': float(e.mean()),
        'median_sec': float(np.median(e)),
        'p90_sec': float(np.percentile(e, 90)),
        'max_sec': float(e.max()),
        'mean_frames': float(f.mean()),
        'median_frames': float(np.median(f)),
        'within_2f_pct': float((f <= 2).mean() * 100.0),
        'within_5f_pct': float((f <= 5).mean() * 100.0),
    }
    if extra:
        row.update(extra)
    return row


def eval_variant(gt, backend, model_path, conf_thresh, windows, cache_dir, use_cache, feature='angle', psi=None):
    src_video = gt['source_video']
    var_video = gt['variant_video']
    v2s = gt['variant_to_source']
    fps = float(gt['fps'])

    print(f"기준(원본): {src_video}")
    std_seq = get_sequence(src_video, backend, model_path, conf_thresh, cache_dir, use_cache)
    print(f"변형본:     {var_video}  [{gt['transform']['kind']}]")
    user_seq = get_sequence(var_video, backend, model_path, conf_thresh, cache_dir, use_cache)

    std_feat = build_features(std_seq, feature)
    user_feat = build_features(user_seq, feature)
    n_var = min(user_seq.n_frames, len(v2s))
    rows = []
    for w in windows:
        path = align(user_feat, std_feat, window=w, psi=psi)
        lut = path_lookup(path, key_idx=0)          # {user_idx: [std_idx...]}
        errs_f, errs_s = [], []
        for i in range(n_var):
            preds = lut.get(i)
            if not preds:
                continue
            pred_s = float(np.median(preds))
            err = abs(pred_s - v2s[i])
            errs_f.append(err)
            errs_s.append(err / fps)
        if not errs_f:
            print(f"  window={w}: 대응 없음")
            continue
        rows.append(summarize(errs_s, errs_f, f"w={w} psi={psi}",
                              {'path_len': len(path)}))
    return rows, {'kind': gt['transform']['kind'], 'fps': fps, 'feature': feature,
                  'source_video': src_video, 'variant_video': var_video}


def eval_anchors(gt, backend, model_path, conf_thresh, windows, cache_dir, use_cache, feature='angle', psi=None):
    pro_video = gt['pro_video']
    user_video = gt['user_video']
    anchors = gt.get('anchors', [])
    if not anchors:
        raise ValueError("앵커가 비어 있습니다.")
    fps_u = float(gt['user_fps'])

    print(f"기준: {pro_video}")
    std_seq = get_sequence(pro_video, backend, model_path, conf_thresh, cache_dir, use_cache)
    print(f"사용자: {user_video}")
    user_seq = get_sequence(user_video, backend, model_path, conf_thresh, cache_dir, use_cache)

    std_feat = build_features(std_seq, feature)
    user_feat = build_features(user_seq, feature)

    rows = []
    per_anchor_best = None
    for w in windows:
        path = align(user_feat, std_feat, window=w, psi=psi)
        lut = path_lookup(path, key_idx=1)          # {std_idx: [user_idx...]}
        errs_f, errs_s, per_anchor = [], [], []
        for a in anchors:
            preds = lut.get(int(a['pro_frame']))
            if not preds:
                continue
            pred_u = float(np.median(preds))
            err = abs(pred_u - a['user_frame'])
            errs_f.append(err)
            errs_s.append(err / fps_u)
            per_anchor.append({
                'id': a['id'],
                'pro_frame': a['pro_frame'],
                'user_frame_gt': a['user_frame'],
                'user_frame_pred': pred_u,
                'error_frames': err,
                'error_sec': err / fps_u,
            })
        if not errs_f:
            print(f"  window={w}: 대응 없음")
            continue
        rows.append(summarize(errs_s, errs_f, f"w={w} psi={psi}", {'path_len': len(path)}))
        if per_anchor_best is None:
            per_anchor_best = per_anchor
    return rows, {'kind': 'anchors', 'fps': fps_u, 'feature': feature, 'per_anchor': per_anchor_best,
                  'pro_video': pro_video, 'user_video': user_video}


def print_table(rows):
    if not rows:
        print("결과 없음")
        return
    print()
    print(f"{'설정':<14} {'n':>5} {'평균(초)':>9} {'중앙(초)':>9} "
          f"{'p90(초)':>9} {'최대(초)':>9} {'±2f내':>7} {'±5f내':>7}")
    print("-" * 78)
    for r in rows:
        print(f"{r['label']:<14} {r['n']:>5} {r['mean_sec']:>9.3f} "
              f"{r['median_sec']:>9.3f} {r['p90_sec']:>9.3f} {r['max_sec']:>9.3f} "
              f"{r['within_2f_pct']:>6.1f}% {r['within_5f_pct']:>6.1f}%")


def main():
    ap = argparse.ArgumentParser(description="DTW 정렬 품질(L2) 측정")
    ap.add_argument('--mode', choices=['variant', 'anchors'], required=True)
    ap.add_argument('--gt', required=True, help='GT JSON 경로')
    ap.add_argument('--backend', default='yolo', choices=['yolo', 'mediapipe', 'hybrid', 'vitpose', 'rtmpose'])
    ap.add_argument('--model-path', default='models/yolov8n-pose.pt')
    ap.add_argument('--conf-thresh', type=float, default=None)
    ap.add_argument('--feature', choices=['angle', 'coord'], default='angle')
    ap.add_argument('--psi', type=int, default=None,
                    help='끝점 완화 프레임 수. 안무 일부만 춘 경우 필요 (D19)')
    ap.add_argument('--windows', nargs='*', default=['15'],
                    help="DTW window 값들. 'none'이면 제약 없음")
    ap.add_argument('--cache-dir', default=CACHE_DIR_DEFAULT)
    ap.add_argument('--no-cache', action='store_true')
    ap.add_argument('--out', default=None, help='결과 JSON 저장 경로')
    args = ap.parse_args()

    windows = [None if str(w).lower() == 'none' else int(w) for w in args.windows]

    with open(args.gt, 'r', encoding='utf-8') as f:
        gt = json.load(f)

    fn = eval_variant if args.mode == 'variant' else eval_anchors
    rows, meta = fn(gt, args.backend, args.model_path, args.conf_thresh,
                    windows, args.cache_dir, not args.no_cache, args.feature,
                    args.psi)

    print_table(rows)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump({'mode': args.mode, 'backend': args.backend,
                       'feature': args.feature,
                       'gt': args.gt, 'meta': meta, 'rows': rows},
                      f, ensure_ascii=False, indent=2)
        print(f"\n저장: {args.out}")


if __name__ == '__main__':
    main()
