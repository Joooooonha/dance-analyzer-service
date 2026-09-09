"""프레임 솎기(stride)가 분석 시간과 결과에 미치는 영향을 잰다.

**왜 재는가.** 분석 한 건이 3분 넘게 걸리고, 그중 89%가 포즈 추정이다
(실측: 다운로드 5초 / 기준 추출 89초 / 연습 추출 89초 / 정렬 5초 / 이미지 18초).
추정 프레임 수를 줄이는 것이 유일하게 의미 있는 손잡이인데, 정확도를 얼마나
잃는지 모르면 넣을 수 없다.

**무엇을 보는가.** "숫자가 얼마나 변했나"가 아니라 **"같은 순간을 짚는가"**다.
사용자에게 중요한 것은 평균 오차 수치가 아니라 어느 대목을 다시 연습하라고
말해주느냐이기 때문이다. 그래서 stride=1(기준)이 짚은 구간과 시간축에서
얼마나 겹치는지를 함께 잰다.

실행:
    ssh macmini 'cd ~/dance-ai && ./venv/bin/python experiments/stride_benchmark.py'
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.analyze import analyze

REF = 'testdata/pro_dancer.MP4'
PRAC = 'testdata/user_dancer.MOV'

# 실제 사용과 같은 조건: 양쪽 시작점을 지정한 30초 구간
TRIM = dict(ref_start_sec=3.49, ref_end_sec=33.49,
            prac_start_sec=6.54, prac_end_sec=36.54)

STRIDES = [1, 2, 3]


def issues(result, n=None):
    """지적 구간을 (그룹, 시작, 끝) 목록으로."""
    src = result['feedback']['top_issues'] if n else result['feedback']['all_issues']
    return [(g['group'], g['start_sec'], g['end_sec']) for g in (src[:n] if n else src)]


def _merge(spans):
    """겹치는 구간을 합쳐 시간축의 합집합으로 만든다.

    **이걸 빼먹으면 지표가 거짓말을 한다.** 한 순간에 여러 신체 그룹이 동시에
    걸리므로 구간들이 서로 크게 겹친다. 합치지 않고 겹침을 더하면 30초짜리
    타임라인에서 합이 100초를 넘어가고, 어떤 두 설정을 비교해도 100%가 나온다.
    """
    if not spans:
        return []
    s = sorted(spans)
    out = [list(s[0])]
    for a, b in s[1:]:
        if a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def timeline_iou(a, b):
    """두 설정이 짚은 '시간대'가 얼마나 같은가 (교집합/합집합)."""
    A, B = _merge([(s, e) for _, s, e in a]), _merge([(s, e) for _, s, e in b])
    inter = sum(max(0.0, min(e, e2) - max(s, s2)) for s, e in A for s2, e2 in B)
    total = sum(e - s for s, e in A) + sum(e - s for s, e in B) - inter
    return inter / total if total > 0 else 0.0


def top_match(base_top, other_all, slack=0.5):
    """기준의 상위 구간 각각에 대해, 다른 설정도 **같은 신체 그룹**을 그 시간대에
    짚었는지. 사용자가 실제로 보고 따라 하는 것이 상위 목록이므로 이게 핵심이다."""
    hit = 0
    for grp, s, e in base_top:
        for grp2, s2, e2 in other_all:
            if grp2 == grp and min(e, e2) - max(s, s2) > -slack:
                hit += 1
                break
    return hit / len(base_top) if base_top else 0.0


def main():
    out = {}
    for stride in STRIDES:
        print(f"\n===== stride={stride} =====", flush=True)
        t0 = time.monotonic()
        r = analyze(REF, PRAC, **TRIM, stride=stride)
        elapsed = time.monotonic() - t0

        st = r['stats']
        out[stride] = {
            'elapsed_sec': round(elapsed, 1),
            'issue_count': r['feedback']['issue_count'],
            'scored_pct': round(st.get('scored_pct', 0), 1),
            'mean_error_deg': round(st.get('mean_error', 0), 2),
            'median_error_deg': round(st.get('median_error', 0), 2),
            'p90_error_deg': round(st.get('p90_error', 0), 2),
            'prac_fps': round(r['meta']['practice_fps'], 2),
            'ref_valid': round(r['meta']['reference_coverage']['joint_valid_ratio'], 3),
            'prac_valid': round(r['meta']['practice_coverage']['joint_valid_ratio'], 3),
            'issues': issues(r),
            'top10': issues(r, 10),
            'sync_map_len': len(r['sync_map']),
            'sync_range': [r['sync_map'][0], r['sync_map'][-1]] if r['sync_map'] else None,
        }
        print(json.dumps({k: v for k, v in out[stride].items() if k != 'spans'},
                         ensure_ascii=False), flush=True)

    print("\n===== 요약 =====")
    print(f"{'stride':>6} {'시간(초)':>9} {'단축':>6} {'구간':>5} {'채점률':>7} "
          f"{'평균오차':>8} {'p90':>7} {'시간대 일치':>11} {'상위10 일치':>11}")
    for s in STRIDES:
        o = out[s]
        print(f"{s:>6} {o['elapsed_sec']:>9} "
              f"{(1 - o['elapsed_sec'] / out[1]['elapsed_sec']) * 100:>5.0f}% "
              f"{o['issue_count']:>5} {o['scored_pct']:>6}% {o['mean_error_deg']:>8} "
              f"{o['p90_error_deg']:>7} "
              f"{timeline_iou(out[1]['issues'], o['issues']) * 100:>10.0f}% "
              f"{top_match(out[1]['top10'], o['issues']) * 100:>10.0f}%")

    print("\n----- 상위 5개 구간이 어떻게 달라지는가 -----")
    for s in STRIDES:
        print(f"  stride={s}")
        for grp, a, b in out[s]['top10'][:5]:
            print(f"    {grp:<5} {a:6.2f}s ~ {b:6.2f}s")

    Path('experiments/stride_result.json').write_text(
        json.dumps(out, ensure_ascii=False, indent=2))
    print("\n저장: experiments/stride_result.json")


if __name__ == '__main__':
    main()
