# src/feedback.py
"""프레임별 각도 오차를 사용자가 읽을 수 있는 피드백으로 변환한다.

`compare_sequences`의 출력은 프레임 단위(0.27초 간격 87개 같은 형태)라
사람이 소화할 수 없다. 여기서 네 가지를 처리한다.

1. **구간 병합** — 연속 프레임에서 같은 부위가 계속 틀리면 하나의 구간으로 묶는다.
   `l_forearm`이 8.3/8.6/8.9초에 연속으로 나오는 것은 별개 사건 3개가 아니라
   한 동작에서 왼팔이 계속 틀린 것이다.

2. **부위별 정규화** — 부위마다 가동 범위가 다르다. 전완은 360도 휘두르지만
   정강이는 그렇지 않아, 같은 "잘못한 정도"라도 각도 수치가 다르게 나온다.
   실측에서도 전완이 항상 상위였다(중앙 29.9도 vs 몸통 9.1도).
   → **그 영상 자체의 부위별 분포**를 기준으로 삼는다. 사람마다 안무마다
   가동 범위가 다르므로 고정 상수보다 안전하다.

3. **방향 부여** — 오차를 절댓값으로만 주면 "더 굽혀라/펴라"를 알 수 없다.
   부호 있는 차이를 살려 방향을 문구로 만든다.

4. **신뢰도 분리** — 오차가 지나치게 크면 사용자가 틀린 것이 아니라 정렬이
   실패했을 수 있다(TASKS.md 시도 6의 되먹임 문제). 그런 구간은 지적하지 않고
   "확인 어려움"으로 따로 모은다. 틀린 피드백을 주는 것보다 낫다.
"""
from dataclasses import dataclass, field

import numpy as np

# 부위 이름 → (한국어, 방향 문구 쌍). 방향은 (양수일 때, 음수일 때).
# 부호 규약: 사용자 각도 − 기준 각도
PART_LABEL = {
    'l_upper_arm': ('왼쪽 위팔', '더 내리세요', '더 올리세요'),
    'r_upper_arm': ('오른쪽 위팔', '더 내리세요', '더 올리세요'),
    'l_forearm': ('왼쪽 팔뚝', '더 내리세요', '더 올리세요'),
    'r_forearm': ('오른쪽 팔뚝', '더 내리세요', '더 올리세요'),
    'l_thigh': ('왼쪽 허벅지', '더 내리세요', '더 올리세요'),
    'r_thigh': ('오른쪽 허벅지', '더 내리세요', '더 올리세요'),
    'l_shin': ('왼쪽 정강이', '더 내리세요', '더 올리세요'),
    'r_shin': ('오른쪽 정강이', '더 내리세요', '더 올리세요'),
    'l_elbow_bend': ('왼쪽 팔꿈치', '더 펴세요', '더 굽히세요'),
    'r_elbow_bend': ('오른쪽 팔꿈치', '더 펴세요', '더 굽히세요'),
    'l_knee_bend': ('왼쪽 무릎', '더 펴세요', '더 굽히세요'),
    'r_knee_bend': ('오른쪽 무릎', '더 굽히세요', '더 펴세요'),
    'torso_tilt': ('상체', '덜 기울이세요', '더 기울이세요'),
    'neck': ('고개', '더 내리세요', '더 드세요'),
}

# 이 각도를 넘는 오차는 "사용자가 틀렸다"보다 "정렬이 실패했다"로 본다.
# 실측 분포(natural1): 프레임 평균오차 p95=49도인데 p99에서 119도로 급격히 튀고
# 최대 178도까지 간다. 178도는 물리적으로 정반대 방향이라 같은 동작을 비교한
# 결과로 보기 어렵다. (TASKS.md 시도 6 — DTW가 포즈가 더 비슷한 엉뚱한 곳을
# 고를 수 있고, 그 경우 오차가 극단적으로 커진다)
UNRELIABLE_DEG = 90.0


def _josa(word: str) -> str:
    """받침 유무로 을/를을 고른다. '무릎을(를)' 같은 표기를 피하기 위함."""
    if not word:
        return '를'
    code = ord(word[-1])
    if not (0xAC00 <= code <= 0xD7A3):     # 한글 음절이 아니면 기본값
        return '를'
    return '을' if (code - 0xAC00) % 28 else '를'


@dataclass
class Segment:
    """같은 부위가 연속으로 틀린 하나의 구간."""
    part: str
    start_sec: float
    end_sec: float
    mean_error: float          # 원본 각도 오차(도)
    peak_error: float
    norm_score: float          # 부위별 분포로 정규화한 값 (클수록 심각)
    direction: str             # 사용자에게 보여줄 방향 문구
    n_frames: int

    @property
    def duration(self):
        return self.end_sec - self.start_sec

    def to_dict(self):
        label = PART_LABEL.get(self.part, (self.part, '', ''))[0]
        josa = _josa(label)
        return {
            'part': self.part,
            'label': label,
            'start_sec': round(self.start_sec, 2),
            'end_sec': round(self.end_sec, 2),
            'duration_sec': round(self.duration, 2),
            'mean_error_deg': round(self.mean_error, 1),
            'peak_error_deg': round(self.peak_error, 1),
            'severity': round(self.norm_score, 2),
            'message': f'{label}{josa} {self.direction}' if self.direction else label,
            'n_frames': self.n_frames,
        }


def _part_baselines(details):
    """
    부위별 정규화 기준 — **그 영상 자체의 분포**를 쓴다 (설계 결정 4-b).
    중앙값을 1.0으로 두는 스케일이라, "이 부위 치고 얼마나 심한가"를 나타낸다.
    """
    acc = {}
    for e in details:
        for name, val in e['items']:
            acc.setdefault(name, []).append(val)
    return {k: max(np.median(v), 1e-6) for k, v in acc.items()}


def build_segments(details, part_thresh_ratio=1.0, max_gap_sec=0.5,
                   min_duration_sec=0.2, unreliable_deg=UNRELIABLE_DEG):
    """
    프레임별 details → 부위별 구간 목록.

    part_thresh_ratio: 부위 기준값(중앙) 대비 이 배수를 넘는 프레임만 구간 후보
    max_gap_sec: 이보다 짧게 끊기면 같은 구간으로 이어붙인다
    min_duration_sec: 이보다 짧은 구간은 버린다 (순간적 튐 제거)

    returns: (segments, unreliable_spans)
    """
    if not details:
        return [], []

    base = _part_baselines(details)
    details = sorted(details, key=lambda e: e.get('user_t_src', e['user_t']))

    # 신뢰 불가 구간: 프레임 평균 오차가 임계를 넘는 곳
    unreliable = []
    for e in details:
        if e['frame_error'] >= unreliable_deg:
            t = e.get('user_t_src', e['user_t'])
            if unreliable and t - unreliable[-1]['end_sec'] <= max_gap_sec:
                unreliable[-1]['end_sec'] = t
                unreliable[-1]['n_frames'] += 1
            else:
                unreliable.append({'start_sec': t, 'end_sec': t, 'n_frames': 1})

    unreliable_ts = set()
    for u in unreliable:
        for e in details:
            t = e.get('user_t_src', e['user_t'])
            if u['start_sec'] <= t <= u['end_sec']:
                unreliable_ts.add(t)

    # 부위별로 시간축을 훑으며 구간 병합
    per_part = {}
    for e in details:
        t = e.get('user_t_src', e['user_t'])
        if t in unreliable_ts:          # 신뢰 불가 구간은 지적하지 않는다
            continue
        for name, val in e['items']:
            if val < base[name] * part_thresh_ratio:
                continue
            signed = dict(e.get('signed_items', [])).get(name)
            per_part.setdefault(name, []).append((t, val, signed))

    segments = []
    for name, pts in per_part.items():
        pts.sort()
        cur = [pts[0]]
        for p in pts[1:]:
            if p[0] - cur[-1][0] <= max_gap_sec:
                cur.append(p)
            else:
                segments.append(_make_segment(name, cur, base[name]))
                cur = [p]
        segments.append(_make_segment(name, cur, base[name]))

    segments = [s for s in segments
                if s.duration >= min_duration_sec or s.n_frames >= 2]
    # 심각도 × 지속시간 순 — 크게 틀렸고 오래 지속된 것이 우선
    segments.sort(key=lambda s: -(s.norm_score * max(s.duration, 0.1)))
    return segments, unreliable


def _make_segment(name, pts, baseline):
    ts = [p[0] for p in pts]
    vals = np.array([p[1] for p in pts])
    signed = [p[2] for p in pts if p[2] is not None]

    direction = ''
    if signed and name in PART_LABEL:
        _, pos_msg, neg_msg = PART_LABEL[name]
        direction = pos_msg if np.median(signed) > 0 else neg_msg

    return Segment(
        part=name, start_sec=min(ts), end_sec=max(ts),
        mean_error=float(vals.mean()), peak_error=float(vals.max()),
        norm_score=float(vals.mean() / baseline),
        direction=direction, n_frames=len(pts))


# 부위를 묶는 신체 그룹. 같은 순간에 "왼쪽 정강이·오른쪽 무릎·왼쪽 허벅지"가
# 따로 지적되면 사용자는 4번 읽어야 하지만, 실제로는 한 동작에서 다리가 틀린
# 것이다. 시간대가 겹치는 같은 그룹의 지적을 하나로 합친다.
PART_GROUP = {
    'l_upper_arm': '왼팔', 'l_forearm': '왼팔', 'l_elbow_bend': '왼팔',
    'r_upper_arm': '오른팔', 'r_forearm': '오른팔', 'r_elbow_bend': '오른팔',
    'l_thigh': '왼다리', 'l_shin': '왼다리', 'l_knee_bend': '왼다리',
    'r_thigh': '오른다리', 'r_shin': '오른다리', 'r_knee_bend': '오른다리',
    'torso_tilt': '상체', 'neck': '상체',
}


def _merge_by_group(segments, overlap_gap=0.3):
    """
    시간대가 겹치는 같은 신체 그룹의 구간을 하나로 합친다.
    대표 문구는 그룹 안에서 가장 심각한 부위의 것을 쓴다.
    """
    by_group = {}
    for s in segments:
        by_group.setdefault(PART_GROUP.get(s.part, s.part), []).append(s)

    merged = []
    for group, segs in by_group.items():
        segs.sort(key=lambda x: x.start_sec)
        cur = [segs[0]]
        for s in segs[1:]:
            if s.start_sec - max(x.end_sec for x in cur) <= overlap_gap:
                cur.append(s)
            else:
                merged.append((group, cur))
                cur = [s]
        merged.append((group, cur))

    out = []
    for group, segs in merged:
        lead = max(segs, key=lambda x: x.norm_score)   # 가장 심각한 부위가 대표
        # 같은 부위가 여러 구간으로 쪼개졌다가 합쳐지면 이름이 중복된다
        # (예: ['r_shin', 'r_knee_bend', 'r_thigh', 'r_knee_bend']).
        # 심각한 순서를 유지하면서 중복만 제거한다.
        seen, parts = set(), []
        for x in sorted(segs, key=lambda y: -y.norm_score):
            if x.part not in seen:
                seen.add(x.part)
                parts.append(x.part)
        out.append({
            'group': group,
            'start_sec': round(min(x.start_sec for x in segs), 2),
            'end_sec': round(max(x.end_sec for x in segs), 2),
            'duration_sec': round(max(x.end_sec for x in segs)
                                  - min(x.start_sec for x in segs), 2),
            'severity': round(max(x.norm_score for x in segs), 2),
            'mean_error_deg': round(float(np.mean([x.mean_error for x in segs])), 1),
            'message': lead.to_dict()['message'],
            'parts': parts,
            'detail': [x.to_dict() for x in sorted(segs, key=lambda y: -y.norm_score)],
        })
    out.sort(key=lambda g: -(g['severity'] * max(g['duration_sec'], 0.1)))
    return out


def summarize(details, top_n=10, group_overlap_gap=0.3, **kwargs):
    """
    사용자에게 보여줄 최종 피드백.

    점수 대신 **틀린 동작(구간) 개수**를 센다. 점수 환산 상수가 임의값이라
    절대값에 의미가 없기 때문이다 (TASKS.md 8.2).

    부위별 구간을 그대로 내보내면 같은 순간이 여러 번 지적된다 — 실측에서
    한 시점에 평균 5.4개, 최대 11개 부위가 동시에 걸렸고 상위 5개 중 4개가
    같은 시간대(8.3~11.8초)였다. 신체 그룹으로 합쳐서 내보낸다.
    """
    segments, unreliable = build_segments(details, **kwargs)
    groups = _merge_by_group(segments, group_overlap_gap)
    return {
        'issue_count': len(groups),
        'top_issues': groups[:top_n],
        'all_issues': groups,
        'part_segment_count': len(segments),
        'unreliable_spans': [
            {'start_sec': round(u['start_sec'], 2),
             'end_sec': round(u['end_sec'], 2),
             'n_frames': u['n_frames']} for u in unreliable],
        'unreliable_note': (
            '정렬 신뢰도가 낮아 평가에서 제외한 구간입니다. '
            '동작이 크게 달라 대응 시점을 특정하기 어렵거나, 촬영 조건 문제일 수 있습니다.'
        ) if unreliable else None,
    }
