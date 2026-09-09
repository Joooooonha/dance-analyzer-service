# tools/annotate_anchors.py
"""
두 영상을 나란히 띄우고 프레임 단위로 이동하며 대응 시점(앵커)을 기록하는 도구.

동작 비교 품질(L2)의 GT를 만드는 데 사용한다. DTW가 "기준 영상 A프레임"과
"사용자 영상 B프레임"을 같은 동작으로 봤는지 채점하려면, 사람이 판단한
정답 대응쌍이 있어야 한다. (TASKS.md Phase 0)

실행 — 반드시 프로젝트 루트(model-research/)에서:

    python -m tools.annotate_anchors \
        --pro data/videos/real/pro_dancer.mp4 \
        --user data/videos/real/user_dancer.mp4 \
        --out data/anchors/real.json

조작키 (OpenCV 창에 포커스를 둔 상태에서):

    TAB       활성 영상 전환 (PRO <-> USER)
    a / d     활성 영상 -1 / +1 프레임
    A / D     활성 영상 -10 / +10 프레임   (shift)
    z / x     활성 영상 -1초 / +1초
    SPACE     현재 (pro, user) 프레임 쌍을 앵커로 기록
    u         마지막 앵커 취소
    o         겹침 구간 마킹 시작/종료 토글 (활성 영상 기준)
    s         저장
    q / ESC   저장 후 종료

앵커를 고르는 기준은 TASKS.md Phase 0 참고. 요약하면 동작이 순간적으로
멈추거나 방향이 바뀌는 지점(팔이 최대로 뻗은 순간, 착지 순간)을 고르고,
연속적으로 흐르는 구간 중간은 피한다.

주의: OpenCV의 putText는 한글을 렌더링하지 못해서 화면 표시는 영문이다.
"""
import argparse
import json
import os

import cv2
import numpy as np

from src.video_utils import apply_rotation, open_video

PANEL_H = 210          # 하단 정보 패널 높이
TARGET_H = 640         # 각 영상을 이 높이로 축소해서 표시
FONT = cv2.FONT_HERSHEY_SIMPLEX

COL_ACTIVE = (0, 220, 255)     # 활성 영상 테두리 (BGR)
COL_IDLE = (90, 90, 90)
COL_TEXT = (30, 30, 30)
COL_ACCENT = (0, 120, 220)
COL_WARN = (0, 0, 220)


def load_frames(path: str, target_h: int):
    """
    영상 전체를 축소해서 메모리에 올린다. 프레임 스크러빙을 즉각 반응하게
    하려는 목적. (cap.set으로 매번 seek하면 되감을 때 눈에 띄게 느리다)

    returns: (frames, fps)
    """
    cap, fps, rotation = open_video(path)
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = apply_rotation(frame, rotation)
        h, w = frame.shape[:2]
        scale = target_h / h
        frames.append(cv2.resize(frame, (int(w * scale), target_h)))
    cap.release()

    if not frames:
        raise ValueError(f"프레임을 하나도 읽지 못했습니다: {path}")

    mb = sum(f.nbytes for f in frames) / (1024 ** 2)
    print(f"  로드 완료: {os.path.basename(path)} "
          f"{len(frames)}프레임, fps={fps:.3f}, 메모리 {mb:.0f}MB")
    return frames, fps


def put(img, text, org, scale=0.5, color=COL_TEXT, thick=1):
    cv2.putText(img, text, org, FONT, scale, color, thick, cv2.LINE_AA)


def render(frames_p, frames_u, ip, iu, active, fps_p, fps_u,
           anchors, occ_pending, occ_ranges):
    """현재 상태를 하나의 캔버스로 그린다."""
    fp = frames_p[ip].copy()
    fu = frames_u[iu].copy()

    # 활성 영상에 테두리
    for img, is_active in ((fp, active == 'pro'), (fu, active == 'user')):
        color = COL_ACTIVE if is_active else COL_IDLE
        cv2.rectangle(img, (0, 0), (img.shape[1] - 1, img.shape[0] - 1), color, 4)

    # 각 영상 상단에 프레임/시간 표시
    for img, name, idx, total, fps in (
        (fp, 'PRO', ip, len(frames_p), fps_p),
        (fu, 'USER', iu, len(frames_u), fps_u),
    ):
        label = f"{name}  f={idx}/{total - 1}  t={idx / fps:.3f}s"
        cv2.rectangle(img, (4, 4), (4 + 9 * len(label), 32), (255, 255, 255), -1)
        put(img, label, (10, 24), 0.55, COL_TEXT, 1)

    combined = cv2.hconcat([fp, fu])
    W = combined.shape[1]

    panel = np.full((PANEL_H, W, 3), 245, dtype=np.uint8)
    cv2.line(panel, (0, 0), (W, 0), (180, 180, 180), 2)

    put(panel, f"ACTIVE: {active.upper()}", (12, 26), 0.62, COL_ACCENT, 2)
    put(panel, f"anchors: {len(anchors)}    occlusion ranges: {len(occ_ranges)}",
        (12, 50), 0.5)

    if occ_pending is not None:
        put(panel, f"[occlusion open] {occ_pending['video']} from f={occ_pending['start_frame']}"
                   f"  -- press 'o' again to close",
            (12, 72), 0.5, COL_WARN, 1)

    # 최근 앵커 3개
    put(panel, "recent anchors (pro <-> user):", (12, 98), 0.45, (110, 110, 110))
    for k, a in enumerate(anchors[-3:]):
        put(panel, f"  #{a['id']}   pro f={a['pro_frame']:<5d} <-> user f={a['user_frame']:<5d}"
                   f"   (dt={a['user_frame'] / fps_u - a['pro_frame'] / fps_p:+.2f}s)",
            (12, 118 + k * 18), 0.45)

    help1 = "TAB switch | a/d +-1 | A/D +-10 | z/x +-1sec | SPACE record"
    help2 = "u undo | o occlusion | s save | q quit(save)"
    put(panel, help1, (12, PANEL_H - 30), 0.44, (120, 120, 120))
    put(panel, help2, (12, PANEL_H - 12), 0.44, (120, 120, 120))

    return cv2.vconcat([combined, panel])


def save(out_path, pair_name, pro_path, user_path, fps_p, fps_u,
         n_p, n_u, anchors, occ_ranges, quiet=False):
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    data = {
        'pair_name': pair_name,
        'pro_video': pro_path,
        'user_video': user_path,
        'pro_fps': fps_p,
        'user_fps': fps_u,
        'pro_frame_count': n_p,
        'user_frame_count': n_u,
        'anchors': anchors,
        'occlusion_ranges': occ_ranges,
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if not quiet:
        print(f"저장됨: {out_path}  (앵커 {len(anchors)}개, 겹침 구간 {len(occ_ranges)}개)")


def load_existing(out_path):
    """이어서 작업할 수 있도록 기존 파일이 있으면 불러온다."""
    if not os.path.exists(out_path):
        return [], []
    try:
        with open(out_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        anchors = data.get('anchors', [])
        occ = data.get('occlusion_ranges', [])
        print(f"기존 파일에서 이어서 작업합니다: 앵커 {len(anchors)}개, 겹침 {len(occ)}개")
        return anchors, occ
    except Exception as e:
        print(f"기존 파일을 읽지 못해 새로 시작합니다 ({type(e).__name__}: {e})")
        return [], []


def main():
    ap = argparse.ArgumentParser(
        description="두 영상의 대응 시점(앵커)을 수동으로 기록하는 도구")
    ap.add_argument('--pro', required=True, help='기준(프로) 영상 경로')
    ap.add_argument('--user', required=True, help='연습(사용자) 영상 경로')
    ap.add_argument('--out', required=True, help='앵커 JSON 저장 경로')
    ap.add_argument('--pair-name', default=None,
                    help='쌍 이름 (기본: out 파일명)')
    ap.add_argument('--target-h', type=int, default=TARGET_H,
                    help=f'표시용 축소 높이 (기본 {TARGET_H})')
    args = ap.parse_args()

    pair_name = args.pair_name or os.path.splitext(os.path.basename(args.out))[0]

    print("영상 로드 중...")
    frames_p, fps_p = load_frames(args.pro, args.target_h)
    frames_u, fps_u = load_frames(args.user, args.target_h)

    anchors, occ_ranges = load_existing(args.out)
    next_id = max((a['id'] for a in anchors), default=0) + 1

    ip = iu = 0
    active = 'pro'
    occ_pending = None

    win = "annotate anchors"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    def step(delta):
        nonlocal ip, iu
        if active == 'pro':
            ip = int(np.clip(ip + delta, 0, len(frames_p) - 1))
        else:
            iu = int(np.clip(iu + delta, 0, len(frames_u) - 1))

    while True:
        canvas = render(frames_p, frames_u, ip, iu, active, fps_p, fps_u,
                        anchors, occ_pending, occ_ranges)
        cv2.imshow(win, canvas)
        key = cv2.waitKey(0) & 0xFF

        if key in (ord('q'), 27):
            break
        elif key == 9:                       # TAB
            active = 'user' if active == 'pro' else 'pro'
        elif key == ord('a'):
            step(-1)
        elif key == ord('d'):
            step(1)
        elif key == ord('A'):
            step(-10)
        elif key == ord('D'):
            step(10)
        elif key == ord('z'):
            step(-int(round(fps_p if active == 'pro' else fps_u)))
        elif key == ord('x'):
            step(int(round(fps_p if active == 'pro' else fps_u)))
        elif key == 32:                      # SPACE
            anchors.append({
                'id': next_id,
                'pro_frame': ip,
                'user_frame': iu,
                'pro_t': round(ip / fps_p, 4),
                'user_t': round(iu / fps_u, 4),
                'label': '',
            })
            print(f"  앵커 #{next_id} 기록: pro f={ip} ({ip / fps_p:.3f}s) "
                  f"<-> user f={iu} ({iu / fps_u:.3f}s)")
            next_id += 1
        elif key == ord('u'):
            if anchors:
                removed = anchors.pop()
                next_id = removed['id']
                print(f"  앵커 #{removed['id']} 취소")
        elif key == ord('o'):
            cur = ip if active == 'pro' else iu
            if occ_pending is None:
                occ_pending = {'video': active, 'start_frame': cur}
                print(f"  겹침 구간 시작: {active} f={cur}")
            elif occ_pending['video'] != active:
                print(f"  ! 겹침 구간은 시작한 영상({occ_pending['video']})에서 닫아야 합니다")
            else:
                start, end = sorted((occ_pending['start_frame'], cur))
                occ_ranges.append({
                    'video': active,
                    'start_frame': start,
                    'end_frame': end,
                    'note': '',
                })
                print(f"  겹침 구간 기록: {active} f={start}~{end}")
                occ_pending = None
        elif key == ord('s'):
            save(args.out, pair_name, args.pro, args.user, fps_p, fps_u,
                 len(frames_p), len(frames_u), anchors, occ_ranges)

    cv2.destroyAllWindows()
    save(args.out, pair_name, args.pro, args.user, fps_p, fps_u,
         len(frames_p), len(frames_u), anchors, occ_ranges)

    if occ_pending is not None:
        print("! 닫히지 않은 겹침 구간이 있어 저장하지 않았습니다:", occ_pending)
    if len(anchors) < 10:
        print(f"! 앵커가 {len(anchors)}개입니다. 10~15개를 권장합니다 (TASKS.md Phase 0)")


if __name__ == '__main__':
    main()
