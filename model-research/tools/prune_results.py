# tools/prune_results.py
"""타임스탬프가 붙어 무한 누적되는 결과 파일을 정리한다.

실행할 때마다 `{something}_YYYYMMDD_HHMMSS.json` 형태의 파일이 새로 쌓이고
지우는 로직이 없어서 용량이 계속 증가했다 (CLAUDE.md 알려진 문제 4).

**기본은 dry-run이다.** 무엇이 지워질지 먼저 보여주고, `--apply`를 줘야 실제로
지운다. 삭제는 되돌릴 수 없으므로 기본값을 안전한 쪽에 둔다.

같은 "그룹"(디렉터리 + 타임스탬프를 뗀 접두사)마다 최신 N개만 남긴다.
타임스탬프 패턴이 없는 파일(`metrics.json`, `pose_quality/final.json` 등)은
의도적으로 이름 붙인 산출물이므로 **건드리지 않는다.**

실행 (프로젝트 루트에서):

    python -m tools.prune_results                  # 미리보기
    python -m tools.prune_results --apply          # 실제 삭제
    python -m tools.prune_results --keep 5 --apply
"""
import argparse
import os
import re
from collections import defaultdict

# 파일명 끝의 _20250615_041927 형태
TS_RE = re.compile(r'^(?P<prefix>.*?)_(?P<ts>\d{8}_\d{6})(?P<ext>\.[A-Za-z0-9]+)$')

DEFAULT_DIRS = ['analysis_result', 'evaluate_result', 'measure_result']


def human(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def collect(dirs):
    """타임스탬프가 붙은 파일을 (디렉터리, 접두사) 그룹으로 모은다."""
    groups = defaultdict(list)
    skipped = 0
    for root_dir in dirs:
        if not os.path.isdir(root_dir):
            continue
        for dirpath, _, filenames in os.walk(root_dir):
            for fn in filenames:
                m = TS_RE.match(fn)
                if not m:
                    skipped += 1
                    continue
                path = os.path.join(dirpath, fn)
                key = (dirpath, m.group('prefix'), m.group('ext'))
                groups[key].append((m.group('ts'), path, os.path.getsize(path)))
    return groups, skipped


def main():
    ap = argparse.ArgumentParser(description="타임스탬프 결과 파일 정리")
    ap.add_argument('--dirs', nargs='+', default=DEFAULT_DIRS)
    ap.add_argument('--keep', type=int, default=10,
                    help='그룹마다 남길 최신 파일 수 (기본 10)')
    ap.add_argument('--apply', action='store_true',
                    help='실제로 삭제한다. 없으면 미리보기만')
    args = ap.parse_args()

    groups, skipped = collect(args.dirs)
    if not groups:
        print("타임스탬프가 붙은 결과 파일이 없습니다.")
        return

    to_delete, kept_n, freed = [], 0, 0
    print(f"{'그룹':<52}{'전체':>6}{'유지':>6}{'삭제':>6}{'확보':>10}")
    print("-" * 80)
    for (dirpath, prefix, ext), files in sorted(groups.items()):
        files.sort(key=lambda x: x[0], reverse=True)   # 최신 우선
        keep, drop = files[:args.keep], files[args.keep:]
        kept_n += len(keep)
        size = sum(f[2] for f in drop)
        freed += size
        to_delete.extend(f[1] for f in drop)
        label = f"{dirpath}/{prefix}*{ext}"
        if drop:
            print(f"{label[:52]:<52}{len(files):>6}{len(keep):>6}{len(drop):>6}{human(size):>10}")

    print("-" * 80)
    print(f"타임스탬프 파일 {kept_n + len(to_delete)}개 중 "
          f"{kept_n}개 유지, {len(to_delete)}개 삭제 대상 ({human(freed)} 확보)")
    print(f"타임스탬프 없는 파일 {skipped}개는 건드리지 않습니다 "
          f"(의도적으로 이름 붙인 산출물).")

    if not to_delete:
        return
    if not args.apply:
        print("\n미리보기입니다. 실제로 지우려면 --apply 를 붙이세요.")
        return

    for p in to_delete:
        os.remove(p)
    print(f"\n{len(to_delete)}개 삭제 완료.")


if __name__ == '__main__':
    main()
