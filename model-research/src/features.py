# src/features.py
"""비교에 쓸 feature 생성. 좌표(coord) 또는 관절 각도(angle).

각도를 쓰는 이유 (TASKS.md D1): 각도는 정의상 이동·스케일 불변이라 카메라
거리·화면 내 위치 차이가 동작 차이로 오인되지 않는다. 게다가 팔·다리 각도를
**몸통 축 기준**으로 재면 카메라 롤(폰을 기울여 촬영)까지 상쇄된다 —
몸통과 팔이 같이 회전하므로 상대 각도는 변하지 않기 때문이다.

각도는 순환량(circular)이다. -179도와 +179도는 2도 차이지 358도 차이가 아니다.
그래서 DTW 입력으로는 각 각도를 (cos, sin)으로 인코딩해서 넣고, 오차는
atan2 기반 순환 차이로 계산한다.

좌표 축 약속: 이미지 x는 오른쪽, y는 아래. 벡터 v의 각도는
atan2(v_x, -v_y)로 정의해서 0도=위, +90도=오른쪽, ±180도=아래가 되게 한다.
"""
from dataclasses import dataclass, field

import numpy as np

from src.sequence import PoseSequence, fill_short_gaps, joint_map

# 팔·다리 분절. (이름, 시작 관절, 끝 관절) — 몸통 상대 방향각으로 쓰인다.
# 굽힘 각도(팔꿈치 90도 등)는 인접 분절 각도의 차이로 유도되므로,
# 분절 방향각이 굽힘 각도보다 정보량이 많다.
SEGMENTS = [
    ('l_upper_arm', 'l_shoulder', 'l_elbow'),
    ('l_forearm', 'l_elbow', 'l_wrist'),
    ('r_upper_arm', 'r_shoulder', 'r_elbow'),
    ('r_forearm', 'r_elbow', 'r_wrist'),
    ('l_thigh', 'l_hip', 'l_knee'),
    ('l_shin', 'l_knee', 'l_ankle'),
    ('r_thigh', 'r_hip', 'r_knee'),
    ('r_shin', 'r_knee', 'r_ankle'),
]

# 굽힘 각도 (a-b-c의 b에서의 내각). 사용자 피드백 문구용으로 함께 계산한다.
# "오른쪽 팔꿈치가 기준보다 20도 덜 굽혀졌습니다" 같은 표현이 가능해진다.
BENDS = [
    ('l_elbow_bend', 'l_shoulder', 'l_elbow', 'l_wrist'),
    ('r_elbow_bend', 'r_shoulder', 'r_elbow', 'r_wrist'),
    ('l_knee_bend', 'l_hip', 'l_knee', 'l_ankle'),
    ('r_knee_bend', 'r_hip', 'r_knee', 'r_ankle'),
]


def wrap(a):
    """각도를 (-pi, pi]로 정규화."""
    return np.arctan2(np.sin(a), np.cos(a))


def vec_angle(v):
    """벡터 (…,2)의 각도. 0=위, +=오른쪽."""
    return np.arctan2(v[..., 0], -v[..., 1])


@dataclass
class FeatureSet:
    """
    values: (N, A, C) — 각도면 C=1(라디안), 좌표면 C=2
    valid:  (N, A)
    circular: 각도 여부. True면 오차를 순환 차이(도)로, 정렬 입력을 cos/sin으로.
    """
    values: np.ndarray
    valid: np.ndarray
    names: list
    circular: bool
    fps: float
    kind: str
    meta: dict = field(default_factory=dict)

    @property
    def n_frames(self):
        return int(self.values.shape[0])

    @property
    def unit(self):
        return 'deg' if self.circular else 'norm'

    def alignment_matrix(self, max_gap_frames=5, velocity_weight=0.5):
        """
        DTW에 넣을 (N, D) 연속 행렬. 짧은 구멍은 보간된다.
        각도는 (cos, sin)으로 인코딩해서 -180/+180 경계에서 튀지 않게 한다.

        velocity_weight > 0이면 **각속도**를 보조 성분으로 덧붙인다 (TASKS.md D24).

        근거: DTW가 자세만 보면 "포즈가 비슷한 곳"을 고르는데, 사용자가 동작을
        틀리게 하면 그 기준이 안무 구조와 어긋난다(시도 6의 원리적 한계).
        반면 **움직임의 타이밍**(언제 치고 멈추고 방향을 바꾸는가)은 포즈가
        틀려도 음악에 맞춰 유지되는 경향이 있어 보완 정보가 된다.

        가중치는 실측으로 정했다 — 0.5에서 두 쌍 모두 최선이고, 속도만
        쓰면(자세 제외) 오히려 나빠진다. 자세가 주 신호, 속도는 보조다.
        """
        if self.circular:
            a = self.values[..., 0]
            enc = np.stack([np.cos(a), np.sin(a)], axis=-1)   # (N, A, 2)
        else:
            enc = self.values
        filled, _ = fill_short_gaps(enc, self.valid, max_gap_frames)
        pos = filled.reshape(self.n_frames, -1)

        if not velocity_weight or not self.circular:
            return np.ascontiguousarray(pos, dtype=np.double)

        # 각속도: 프레임 간 순환 차이. 각도별 표준편차로 정규화해 자세 성분과
        # 스케일을 맞춘 뒤 가중치를 곱한다.
        a = self.values[..., 0]
        d = np.diff(a, axis=0, prepend=a[:1])
        vel = np.arctan2(np.sin(d), np.cos(d))
        vel = vel / (vel.std(axis=0, keepdims=True) + 1e-9)
        return np.ascontiguousarray(
            np.concatenate([pos, vel * velocity_weight], axis=1), dtype=np.double)

    def pairwise_error(self, i, other, j):
        """
        두 프레임의 feature 오차. 양쪽 모두 유효한 항목만 사용한다
        (pairwise 판정 — TASKS.md D2).

        returns: (mean_error, n_valid, [(name, error), ...], [(name, signed), ...])

        각도면 도(degree), 좌표면 정규화 거리 단위.
        네 번째 값은 **부호 있는 차이**(사용자 − 기준)다. 피드백에서 "더 굽혀라 /
        더 펴라" 같은 방향을 만들려면 절댓값만으로는 부족하기 때문이다.
        좌표 feature는 방향이 정의되지 않으므로 빈 리스트를 반환한다.
        """
        both = self.valid[i] & other.valid[j]
        n = int(both.sum())
        if n == 0:
            return None, 0, [], []

        a = self.values[i][both]
        b = other.values[j][both]
        if self.circular:
            signed = wrap(a[:, 0] - b[:, 0]) * 180.0 / np.pi
            d = np.abs(signed)
        else:
            signed = None
            d = np.linalg.norm(a - b, axis=-1)

        names = [self.names[k] for k in np.where(both)[0]]
        sg = ([(nm, float(v)) for nm, v in zip(names, signed)]
              if signed is not None else [])
        return float(d.mean()), n, [(nm, float(v)) for nm, v in zip(names, d)], sg

    def frame_gate(self, min_valid_ratio=0.3):
        """
        2단 프레임 게이트 (TASKS.md D4).
        (a) 몸통 기준 4점이 유효한가 — 신뢰도가 아니라 계산 가능 여부의 문제
        (b) 유효 feature 비율이 임계 이상인가
        """
        gate = self.valid.mean(axis=1) >= min_valid_ratio
        core = self.meta.get('core_valid')
        if core is not None:
            gate = gate & core
        return gate

    def coverage(self, min_valid_ratio=0.3):
        gate = self.frame_gate(min_valid_ratio)
        core = self.meta.get('core_valid')
        return {
            'n_frames': self.n_frames,
            'feature_valid_ratio': float(self.valid.mean()),
            'core_valid_frames': int(core.sum()) if core is not None else None,
            'gated_frames': int(gate.sum()),
            'ungated_pct': float((~gate).mean() * 100.0),
        }


def _torso(seq: PoseSequence):
    """
    몸통 축과 정면성 지표를 계산한다.

    returns: (torso_angle (N,), torso_valid (N,), frontality (N,), torso_len (N,))
    """
    jm = joint_map(seq.num_keypoints)
    ls, rs = seq.coords[:, jm['l_shoulder']], seq.coords[:, jm['r_shoulder']]
    lh, rh = seq.coords[:, jm['l_hip']], seq.coords[:, jm['r_hip']]
    v = (seq.valid[:, jm['l_shoulder']] & seq.valid[:, jm['r_shoulder']]
         & seq.valid[:, jm['l_hip']] & seq.valid[:, jm['r_hip']])

    sh_c = (ls + rs) / 2.0
    hip_c = (lh + rh) / 2.0
    torso_vec = sh_c - hip_c
    torso_len = np.linalg.norm(torso_vec, axis=1)
    angle = vec_angle(torso_vec)

    # 정면성 (D6): 어깨너비 / 몸통길이. 정면일 때 최대, 옆으로 돌수록 작아진다.
    # 회전 자체를 보정하지는 않고, 2D 각도를 얼마나 믿을 수 있는지의 지표로 쓴다.
    shoulder_w = np.linalg.norm(ls - rs, axis=1)
    with np.errstate(divide='ignore', invalid='ignore'):
        frontality = np.where(torso_len > 1e-6, shoulder_w / torso_len, 0.0)

    v &= torso_len > 1e-6
    return angle, v, frontality, torso_len


def build_angle_features(seq: PoseSequence) -> FeatureSet:
    """
    관절 각도 feature. 팔·다리는 몸통 상대 방향각, 몸통 기울기는 영상별
    중앙값 기준 편차 (D5 자가 보정).
    """
    jm = joint_map(seq.num_keypoints)
    n = seq.n_frames
    torso_angle, torso_valid, frontality, torso_len = _torso(seq)

    names, vals, valids = [], [], []

    # 1) 분절 방향각 — 몸통 상대. 몸통과 팔이 같이 회전하므로 카메라 롤이 상쇄된다.
    for name, a, b in SEGMENTS:
        ia, ib = jm[a], jm[b]
        seg = seq.coords[:, ib] - seq.coords[:, ia]
        ok = seq.valid[:, ia] & seq.valid[:, ib] & torso_valid
        ok &= np.linalg.norm(seg, axis=1) > 1e-6
        names.append(name)
        vals.append(wrap(vec_angle(seg) - torso_angle))
        valids.append(ok)

    # 2) 몸통 기울기 — 이것만은 절대 기준이 필요하다.
    #    카메라 롤을 없애기 위해 "이 영상의 몸통 축 중앙값"을 수직으로 삼는다 (D5).
    #    롤은 분포 전체를 일정하게 shift시키는 상수 오프셋이라 중앙값을 빼면 상쇄된다.
    #    절대 수직을 복원하는 게 목적이 아니라 두 영상의 기준을 맞추는 게 목적이다.
    if torso_valid.any():
        ref = float(np.median(torso_angle[torso_valid]))
    else:
        ref = 0.0
    names.append('torso_tilt')
    vals.append(wrap(torso_angle - ref))
    valids.append(torso_valid.copy())

    # 3) 목 방향 (어깨중점 -> 코), 몸통 상대
    if 'nose' in jm:
        sh_c = (seq.coords[:, jm['l_shoulder']] + seq.coords[:, jm['r_shoulder']]) / 2.0
        neck = seq.coords[:, jm['nose']] - sh_c
        ok = (seq.valid[:, jm['nose']] & torso_valid
              & (np.linalg.norm(neck, axis=1) > 1e-6))
        names.append('neck')
        vals.append(wrap(vec_angle(neck) - torso_angle))
        valids.append(ok)

    # 4) 굽힘 각도 — 피드백 문구용
    for name, a, b, c in BENDS:
        ia, ib, ic = jm[a], jm[b], jm[c]
        v1 = seq.coords[:, ia] - seq.coords[:, ib]
        v2 = seq.coords[:, ic] - seq.coords[:, ib]
        ok = seq.valid[:, ia] & seq.valid[:, ib] & seq.valid[:, ic]
        ok &= (np.linalg.norm(v1, axis=1) > 1e-6) & (np.linalg.norm(v2, axis=1) > 1e-6)
        names.append(name)
        vals.append(wrap(vec_angle(v1) - vec_angle(v2)))
        valids.append(ok)

    values = np.stack(vals, axis=1)[:, :, None].astype(np.float32)   # (N, A, 1)
    valid = np.stack(valids, axis=1)

    return FeatureSet(
        values=values, valid=valid, names=names, circular=True,
        fps=seq.fps, kind='angle',
        meta={
            'core_valid': torso_valid,
            'torso_ref_rad': ref,
            'torso_ref_deg': float(np.degrees(ref)),
            'frontality': frontality.astype(np.float32),
            'frontality_median': float(np.median(frontality[torso_valid]))
                                 if torso_valid.any() else 0.0,
            'torso_valid_pct': float(torso_valid.mean() * 100.0),
            'source': seq.source,
        })


def build_coord_features(seq: PoseSequence) -> FeatureSet:
    """
    좌표 feature. 각도 도입 전의 방식이며, A/B 비교용으로 남긴다.
    등방 정규화는 되어 있지만 카메라 거리·위치·롤에는 여전히 취약하다.
    """
    return FeatureSet(
        values=seq.coords.astype(np.float32), valid=seq.valid.copy(),
        names=[f'kp{i}' for i in range(seq.num_keypoints)],
        circular=False, fps=seq.fps, kind='coord',
        meta={'source': seq.source,
              'core_valid': seq.core_valid_per_frame()})


def feature_joint_indices(name: str, num_keypoints: int) -> list:
    """feature 이름 → 관련 관절 인덱스. 시각화에서 오차 부위를 표시할 때 쓴다."""
    jm = joint_map(num_keypoints)
    for n, a, b in SEGMENTS:
        if n == name:
            return [jm[a], jm[b]]
    for n, a, b, c in BENDS:
        if n == name:
            return [jm[a], jm[b], jm[c]]
    if name == 'torso_tilt':
        return [jm['l_shoulder'], jm['r_shoulder'], jm['l_hip'], jm['r_hip']]
    if name == 'neck' and 'nose' in jm:
        return [jm['nose']]
    if name.startswith('kp'):          # coord feature
        try:
            return [int(name[2:])]
        except ValueError:
            return []
    return []


def build_features(seq: PoseSequence, kind: str = 'angle') -> FeatureSet:
    if kind == 'angle':
        return build_angle_features(seq)
    if kind == 'coord':
        return build_coord_features(seq)
    raise ValueError(f"알 수 없는 feature 종류: {kind}")
