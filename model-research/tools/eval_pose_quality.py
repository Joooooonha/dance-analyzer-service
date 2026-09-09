# tools/eval_pose_quality.py
"""정답 라벨 없이 포즈 추정 품질을 비교한다.

L1 GT(사람이 찍은 키포인트)가 없으면 "어느 모델이 정확한가"의 순위는 매길 수
없다. 하지만 라벨 없이도 잴 수 있는 **품질의 필요조건**들이 있다.

1. **뼈 길이 안정성** — 사람 몸은 강체다. 전완 길이가 프레임 사이에 갑자기
   튀면 그건 동작이 아니라 추정 오류다. 특히 겹침 구간에서 모델이 가려진
   관절을 지어내면 뼈 길이가 깨진다. 즉 이 지표는 **라벨 없는 겹침 오류
   탐지기**다 (CLAUDE.md 알려진 문제 2를 정면으로 겨냥).
   투영 단축(limb이 카메라를 향할 때 짧아 보임)은 부드럽게 변하므로,
   프레임 간 **급변**만 보면 단축과 오류를 구분할 수 있다.

2. **시간적 흔들림(jitter)** — 같은 영상을 여러 모델로 돌리면 실제 움직임은
   동일하다. 따라서 프레임 간 키포인트 변위의 차이는 모델의 흔들림 차이다.

3. **모델 간 불일치** — 두 모델이 다르게 답하는 프레임은 어려운 프레임이다.
   정답을 몰라도 "여기가 어렵다"는 것은 알 수 있다. 나중에 L1 GT를 만들 때
   **라벨링할 프레임을 무작위가 아니라 여기서 고르면** 겹침 서브셋을 원리적으로
   구성할 수 있다.

4. **비용** — fps / latency / memory. 라벨과 무관.

모든 지표는 몸통 길이로 정규화해서 카메라 거리에 무관하게 만든다.

**주의 — 모델 간 "유효율"은 비교하면 안 된다.** 신뢰도 캘리브레이션이 모델마다
다르기 때문이다. 실측에서 yolov8x가 yolov8n보다 유효율이 낮게 나왔는데
(91.8% vs 93.3%), 이는 큰 모델이 나쁜 게 아니라 과신하지 않는다는 뜻일 수 있다.
그래서 품질 지표는 낮은 임계값(`--conf-thresh`, 기본 0.1)으로 계산한다 —
모델이 내놓은 추정을 **거의 다 포함시켜서 그 추정들이 기하학적으로 얼마나
일관적인지**를 보는 것이 목적이기 때문이다. 걸러낸 뒤의 품질이 아니라
걸러내기 전의 품질을 재야 모델끼리 공정하다.

실행 (프로젝트 루트에서):

    python -m tools.eval_pose_quality --video data/videos/real/user_dancer.mp4 \
        --models yolo:models/yolov8n-pose.pt mediapipe:0 mediapipe:2
"""
import argparse
import json
import os

import numpy as np

from src.extract import extract_pose_sequence
from src.sequence import JOINT_MAP, joint_map

# 길이가 일정해야 하는 뼈 (강체 가정이 성립하는 것들)
BONES = [
    ('l_upper_arm', 'l_shoulder', 'l_elbow'),
    ('l_forearm', 'l_elbow', 'l_wrist'),
    ('r_upper_arm', 'r_shoulder', 'r_elbow'),
    ('r_forearm', 'r_elbow', 'r_wrist'),
    ('l_thigh', 'l_hip', 'l_knee'),
    ('l_shin', 'l_knee', 'l_ankle'),
    ('r_thigh', 'r_hip', 'r_knee'),
    ('r_shin', 'r_knee', 'r_ankle'),
    ('shoulders', 'l_shoulder', 'r_shoulder'),
    ('hips', 'l_hip', 'r_hip'),
]


def parse_model_spec(spec: str):
    """'yolo:models/yolo11x-pose.pt' 또는 'mediapipe:2' 형식."""
    if ':' not in spec:
        raise ValueError(f"모델 지정 형식이 잘못됐습니다: {spec}")
    backend, rest = spec.split(':', 1)
    backend = backend.lower()
    if backend == 'yolo':
        return {'label': spec, 'backend': 'yolo', 'model_path': rest,
                'model_complexity': 0}
    if backend == 'rtmpose':
        return {'label': spec, 'backend': 'rtmpose',
                'model_path': rest or None, 'model_complexity': 0}
    if backend == 'vitpose':
        return {'label': spec, 'backend': 'vitpose',
                'model_path': rest or None, 'model_complexity': 0}
    if backend in ('mediapipe', 'hybrid'):
        return {'label': spec, 'backend': backend, 'model_path': None,
                'model_complexity': int(rest)}
    raise ValueError(f"알 수 없는 backend: {backend}")


def torso_length(seq):
    """프레임별 몸통 길이 (정규화 기준). 무효 프레임은 nan."""
    jm = joint_map(seq.num_keypoints)
    sh = (seq.coords[:, jm['l_shoulder']] + seq.coords[:, jm['r_shoulder']]) / 2
    hp = (seq.coords[:, jm['l_hip']] + seq.coords[:, jm['r_hip']]) / 2
    ok = (seq.valid[:, jm['l_shoulder']] & seq.valid[:, jm['r_shoulder']]
          & seq.valid[:, jm['l_hip']] & seq.valid[:, jm['r_hip']])
    L = np.linalg.norm(sh - hp, axis=1)
    return np.where(ok & (L > 1e-6), L, np.nan)


def bone_stability(seq):
    """
    뼈 길이의 프레임 간 급변량. 몸통 길이로 정규화한 뒤 중앙값을 취한다.
    낮을수록 안정적 = 추정이 일관적.

    투영 단축은 부드럽게 변하므로 프레임 간 차분에는 거의 안 잡히고,
    관절을 잘못 찍은 순간만 크게 잡힌다.
    """
    jm = joint_map(seq.num_keypoints)
    T = torso_length(seq)
    out = {}
    for name, a, b in BONES:
        ia, ib = jm[a], jm[b]
        ok = seq.valid[:, ia] & seq.valid[:, ib] & ~np.isnan(T)
        L = np.linalg.norm(seq.coords[:, ia] - seq.coords[:, ib], axis=1)
        Ln = np.where(ok, L / T, np.nan)
        # 양쪽 프레임 모두 유효할 때만 차분
        d = np.abs(np.diff(Ln))
        d = d[~np.isnan(d)]
        out[name] = float(np.median(d)) if d.size else None
    vals = [v for v in out.values() if v is not None]
    return out, (float(np.median(vals)) if vals else None)


def temporal_jitter(seq):
    """
    키포인트의 프레임 간 변위 중앙값 (몸통 길이 정규화).
    같은 영상을 여러 모델로 비교할 때만 의미가 있다 — 실제 움직임이 동일하므로
    차이는 모델의 흔들림 차이다.
    """
    T = torso_length(seq)
    ok = seq.valid[:-1] & seq.valid[1:] & (~np.isnan(T))[:-1, None]
    d = np.linalg.norm(seq.coords[1:] - seq.coords[:-1], axis=2)
    dn = d / T[:-1, None]
    vals = dn[ok]
    vals = vals[np.isfinite(vals)]
    return float(np.median(vals)) if vals.size else None


def cross_model_disagreement(seq_a, seq_b):
    """
    두 모델의 프레임별 불일치 (공통 관절만, 몸통 길이 정규화).
    관절 정의가 다르면(COCO17 vs BlazePose33) 이름으로 공통 관절을 맞춘다.

    returns: (per_frame (N,), median, common_joint_names)
    """
    jm_a, jm_b = joint_map(seq_a.num_keypoints), joint_map(seq_b.num_keypoints)
    common = [n for n in jm_a if n in jm_b]
    ia = [jm_a[n] for n in common]
    ib = [jm_b[n] for n in common]

    n = min(seq_a.n_frames, seq_b.n_frames)
    Ta, Tb = torso_length(seq_a)[:n], torso_length(seq_b)[:n]
    scale = np.nanmean(np.stack([Ta, Tb]), axis=0)

    d = np.linalg.norm(seq_a.coords[:n][:, ia] - seq_b.coords[:n][:, ib], axis=2)
    ok = seq_a.valid[:n][:, ia] & seq_b.valid[:n][:, ib]
    dn = d / scale[:, None]

    per_frame = np.full(n, np.nan)
    for i in range(n):
        v = dn[i][ok[i]]
        v = v[np.isfinite(v)]
        if v.size:
            per_frame[i] = v.mean()
    finite = per_frame[np.isfinite(per_frame)]
    return per_frame, (float(np.median(finite)) if finite.size else None), common


def main():
    ap = argparse.ArgumentParser(description="라벨 없는 포즈 품질 비교")
    ap.add_argument('--video', required=True)
    ap.add_argument('--models', nargs='+', required=True,
                    help="예: yolo:models/yolov8n-pose.pt mediapipe:0 mediapipe:2")
    ap.add_argument('--conf-thresh', type=float, default=0.1,
                    help='품질 비교용 낮은 임계값. 모델 간 신뢰도 캘리브레이션 '
                         '차이를 배제하기 위해 기본 0.1 (모듈 docstring 참조)')
    ap.add_argument('--out', default=None)
    ap.add_argument('--hard-frames', type=int, default=30,
                    help='불일치 상위 N개 프레임을 저장 (L1 라벨링 대상 후보)')
    args = ap.parse_args()

    specs = [parse_model_spec(s) for s in args.models]
    seqs, metrics = {}, {}

    for sp in specs:
        print(f"\n── {sp['label']}")
        seq, m = extract_pose_sequence(
            args.video, sp['backend'], model_path=sp['model_path'],
            conf_thresh=args.conf_thresh, verbose=True, progress_every=0,
            model_complexity=sp['model_complexity'])
        seqs[sp['label']] = seq
        metrics[sp['label']] = m

    rows = []
    for sp in specs:
        lbl = sp['label']
        seq = seqs[lbl]
        per_bone, bone_med = bone_stability(seq)
        rows.append({
            'label': lbl,
            'num_keypoints': seq.num_keypoints,
            'joint_valid_pct': float(seq.valid.mean() * 100),
            'detect_fail': metrics[lbl]['detect_fail_frames'],
            'bone_instability': bone_med,
            'bone_per_bone': per_bone,
            'jitter': temporal_jitter(seq),
            'fps': metrics[lbl]['measured_fps'],
            'latency_ms': metrics[lbl]['latency_ms'],
            'memory_MB': metrics[lbl]['memory_MB'],
        })

    print()
    print(f"{'모델':<30}{'유효율':>8}{'뼈불안정':>10}{'흔들림':>9}"
          f"{'fps':>8}{'지연ms':>8}{'메모리MB':>10}")
    print("-" * 84)
    for r in rows:
        print(f"{r['label'][:30]:<30}{r['joint_valid_pct']:>7.1f}%"
              f"{r['bone_instability']:>10.4f}{r['jitter']:>9.4f}"
              f"{r['fps']:>8.1f}{r['latency_ms']:>8.1f}{r['memory_MB']:>10.1f}")
    print("\n뼈불안정 = 프레임 간 뼈 길이 급변 중앙값 (몸통길이 정규화, 낮을수록 좋음)")
    print("흔들림   = 프레임 간 키포인트 변위 중앙값 (같은 영상이므로 모델 비교에만 유효)")

    # 모델 쌍별 불일치
    pairs = []
    hard = {}
    for i in range(len(specs)):
        for j in range(i + 1, len(specs)):
            a, b = specs[i]['label'], specs[j]['label']
            pf, med, common = cross_model_disagreement(seqs[a], seqs[b])
            pairs.append({'a': a, 'b': b, 'median': med,
                          'common_joints': len(common)})
            order = np.argsort(-np.nan_to_num(pf, nan=-1))
            hard[f"{a} vs {b}"] = [int(k) for k in order[:args.hard_frames]]

    if pairs:
        print(f"\n{'모델 쌍':<58}{'공통관절':>9}{'불일치중앙':>11}")
        print("-" * 80)
        for p in pairs:
            print(f"{(p['a'] + '  vs  ' + p['b'])[:58]:<58}"
                  f"{p['common_joints']:>9}{p['median']:>11.4f}")
        print("\n불일치 = 두 모델의 키포인트 거리 중앙값 (몸통길이 정규화)")
        print("       큰 프레임 = 어려운 프레임. L1 GT 라벨링 대상으로 우선 선정할 것")

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump({'video': args.video, 'rows': rows, 'pairs': pairs,
                       'hard_frames': hard}, f, ensure_ascii=False, indent=2)
        print(f"\n저장: {args.out}")


if __name__ == '__main__':
    main()
