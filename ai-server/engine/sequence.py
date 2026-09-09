# src/sequence.py
"""포즈 시퀀스 컨테이너와 관절 인덱스 정의.

가려지거나 검출되지 않은 관절을 0으로 채우지 않고 **명시적 유효성 마스크**로
표현한다. 0-padding은 두 영상 모두 0이 되어 거리 0 = "완벽 일치"로 계산되는
역전을 일으킨다. (TASKS.md D2)

좌표는 등방(isotropic) 정규화로 저장한다. 백엔드들은 x를 W로, y를 H로 나눠서
넘겨주는데, 세로 영상(1080x1920)에서는 같은 픽셀 거리가 가로/세로에서 다른
값이 되어 가로 오차가 1.78배 과대평가된다. 여기서 x에 (W/H)를 곱해 "높이 단위"로
통일한다.
"""
from dataclasses import dataclass, field

import numpy as np

# 백엔드별 신뢰도 임계값.
# 잠정값이다 — 실측한 분포(TASKS.md)를 근거로 정했을 뿐, 실제로 가려진 관절을
# 정확히 걸러내는지는 아직 검증되지 않았다. 앵커 파일의 occlusion_ranges가
# 확보되면 그 구간의 신뢰도 분포를 보고 보정할 것.
DEFAULT_CONF_THRESH = {
    'yolo': 0.5,
    'mediapipe': 0.5,
    'hybrid': 0.5,
    'vitpose': 0.5,
    'rtmpose': 0.5,
}

# 관절 이름 → 인덱스. Phase 2의 각도 feature가 이 이름들을 사용한다.
JOINT_MAP = {
    17: {  # COCO17 (YOLO-pose)
        'nose': 0,
        'l_shoulder': 5, 'r_shoulder': 6,
        'l_elbow': 7, 'r_elbow': 8,
        'l_wrist': 9, 'r_wrist': 10,
        'l_hip': 11, 'r_hip': 12,
        'l_knee': 13, 'r_knee': 14,
        'l_ankle': 15, 'r_ankle': 16,
    },
    33: {  # BlazePose 33 (MediaPipe)
        'nose': 0,
        'l_shoulder': 11, 'r_shoulder': 12,
        'l_elbow': 13, 'r_elbow': 14,
        'l_wrist': 15, 'r_wrist': 16,
        'l_hip': 23, 'r_hip': 24,
        'l_knee': 25, 'r_knee': 26,
        'l_ankle': 27, 'r_ankle': 28,
    },
}

# 프레임 게이트의 필수 관절 (TASKS.md D4-a).
# 이게 없으면 몸통 상대 각도, 정면성 비율, 롤 자가보정이 전부 계산 불가다.
# 신뢰도의 문제가 아니라 계산 가능 여부의 문제라 비율 임계와 별도로 둔다.
CORE_JOINT_NAMES = ('l_shoulder', 'r_shoulder', 'l_hip', 'r_hip')


def joint_map(num_keypoints: int) -> dict:
    if num_keypoints not in JOINT_MAP:
        raise ValueError(
            f"관절 {num_keypoints}개에 대한 인덱스 정의가 없습니다. "
            f"지원: {sorted(JOINT_MAP)}")
    return JOINT_MAP[num_keypoints]


def core_indices(num_keypoints: int) -> list:
    jm = joint_map(num_keypoints)
    return [jm[n] for n in CORE_JOINT_NAMES]


@dataclass
class PoseSequence:
    """
    coords: (N, K, 2) 등방 정규화 좌표
    conf:   (N, K)    백엔드가 준 신뢰도/visibility 원본값
    valid:  (N, K)    bool. False = 이 관절은 존재하지 않는 것으로 취급
    """
    coords: np.ndarray
    conf: np.ndarray
    valid: np.ndarray
    fps: float
    num_keypoints: int
    source: str = ''
    meta: dict = field(default_factory=dict)

    @property
    def n_frames(self) -> int:
        return int(self.coords.shape[0])

    def valid_ratio_per_frame(self) -> np.ndarray:
        return self.valid.mean(axis=1)

    def core_valid_per_frame(self) -> np.ndarray:
        """필수 관절(어깨2·엉덩이2)이 전부 유효한 프레임인지."""
        idx = core_indices(self.num_keypoints)
        return self.valid[:, idx].all(axis=1)

    def frame_gate(self, min_valid_ratio: float = 0.3) -> np.ndarray:
        """TASKS.md D4의 2단 게이트. 통과한 프레임만 채점에 사용한다."""
        return self.core_valid_per_frame() & (self.valid_ratio_per_frame() >= min_valid_ratio)

    def coverage(self, min_valid_ratio: float = 0.3) -> dict:
        gate = self.frame_gate(min_valid_ratio)
        return {
            'n_frames': self.n_frames,
            'joint_valid_ratio': float(self.valid.mean()),
            'core_valid_frames': int(self.core_valid_per_frame().sum()),
            'gated_frames': int(gate.sum()),
            'ungated_frames': int((~gate).sum()),
            'ungated_pct': float((~gate).mean() * 100.0),
        }

    def save(self, path: str) -> None:
        np.savez_compressed(
            path,
            coords=self.coords, conf=self.conf, valid=self.valid,
            fps=self.fps, num_keypoints=self.num_keypoints, source=self.source)

    @staticmethod
    def load(path: str) -> 'PoseSequence':
        z = np.load(path, allow_pickle=False)
        return PoseSequence(
            coords=z['coords'], conf=z['conf'], valid=z['valid'],
            fps=float(z['fps']), num_keypoints=int(z['num_keypoints']),
            source=str(z['source']))


def build_sequence(raw_frames, num_keypoints, fps, frame_size,
                   conf_thresh=0.5, source=''):
    """
    백엔드가 뱉은 프레임별 키포인트 리스트를 PoseSequence로 변환한다.

    raw_frames: 프레임마다 None 이거나 (K,2)/(K,3) 배열류
    frame_size: (H, W) 원본 프레임 크기. x의 등방 재정규화에 사용
    conf_thresh: 이 값 미만의 신뢰도를 가진 관절은 유효하지 않은 것으로 본다
    """
    H, W = frame_size
    aspect = W / H  # x_norm(=x/W) * aspect = x/H

    n = len(raw_frames)
    coords = np.zeros((n, num_keypoints, 2), dtype=np.float32)
    conf = np.zeros((n, num_keypoints), dtype=np.float32)
    valid = np.zeros((n, num_keypoints), dtype=bool)

    for i, f in enumerate(raw_frames):
        if f is None:
            continue                      # 프레임 전체 무효 (검출 실패)
        arr = np.asarray(f, dtype=np.float32)
        if arr.size == 0 or arr.ndim != 2:
            continue
        k = min(arr.shape[0], num_keypoints)
        coords[i, :k, 0] = arr[:k, 0] * aspect
        coords[i, :k, 1] = arr[:k, 1]
        if arr.shape[1] >= 3:
            conf[i, :k] = arr[:k, 2]
        else:
            conf[i, :k] = 1.0             # 신뢰도를 안 주는 백엔드는 1로 간주
        valid[i, :k] = conf[i, :k] >= conf_thresh

    # 좌표가 정확히 (0,0)인 관절은 패딩 잔재로 보고 무효 처리.
    # 정규화 좌표에서 정확한 0.0이 나올 확률은 사실상 없다.
    valid &= ~np.all(coords == 0.0, axis=2)

    return PoseSequence(
        coords=coords, conf=conf, valid=valid, fps=float(fps),
        num_keypoints=int(num_keypoints), source=source,
        meta={'frame_size': (int(H), int(W)), 'conf_thresh': float(conf_thresh)})


def fill_short_gaps(values: np.ndarray, valid: np.ndarray,
                    max_gap_frames: int = 5):
    """
    **정렬용** 값을 만든다. 짧은 무효 구간만 선형 보간해서 DTW가 연속적인
    입력을 받게 한다. (TASKS.md D3, D9)

    긴 구간은 보간하지 않는다 — 없는 데이터를 지어내는 것이고, 겹침 중에
    실제로 빠른 동작이 있었다면 그걸 매끄럽게 덮어버린다. 대신 직전 값을
    유지해서 연속성만 확보한다.

    채점에는 이 결과를 절대 쓰지 않는다. DTW는 대응 경로(path)만 제공하고
    값은 사용하지 않으므로, 여기 들어간 보간값이 최종 점수를 오염시키지 않는다.

    values: (N, A, C) — 좌표면 C=2, 각도의 cos/sin 인코딩이면 C=2
    valid:  (N, A)
    returns: (filled_values, interpolated_mask (N,A))
    """
    out = values.copy()
    filled = np.zeros(valid.shape, dtype=bool)

    for j in range(valid.shape[1]):
        v = valid[:, j]
        if not v.any():
            continue
        idx = np.where(v)[0]

        # 양 끝의 무효 구간은 가장 가까운 유효값으로 유지 (외삽하지 않음)
        out[:idx[0], j] = out[idx[0], j]
        out[idx[-1] + 1:, j] = out[idx[-1], j]

        for a, b in zip(idx[:-1], idx[1:]):
            gap = b - a - 1
            if gap <= 0:
                continue
            if gap > max_gap_frames:
                out[a + 1:b, j] = out[a, j]
                continue
            t = np.linspace(0.0, 1.0, gap + 2)[1:-1][:, None]
            out[a + 1:b, j] = out[a, j] * (1 - t) + out[b, j] * t
            filled[a + 1:b, j] = True

    return out, filled


def interpolate_short_gaps(seq: PoseSequence, max_gap_frames: int = 5):
    """PoseSequence 좌표에 대한 fill_short_gaps 래퍼."""
    return fill_short_gaps(seq.coords, seq.valid, max_gap_frames)
