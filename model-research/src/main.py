# src/main.py
"""기준 영상 vs 사용자 영상 비교 실행부.

실행은 반드시 프로젝트 루트(model-research/)에서:

    python -m src.main --pose-backend yolo
    python -m src.main --pose-backend yolo --visualize

`python src/main.py`처럼 파일 경로로 직접 실행하면 `from src.xxx import`가
깨진다 (CLAUDE.md 참조).
"""
import argparse
import datetime
import json
import os

import cv2
import numpy as np

from src.dtw_compare import compare_sequences
from src.extract import extract_pose_sequence
from src.feedback import summarize
from src.features import build_features, feature_joint_indices
from src.metrics import COCO17_SKELETON
from src.pose_factory import make_pose_pipeline
from src.video_utils import apply_rotation, open_video

CANVAS_W, CANVAS_H = 1280, 900
TABLE_H = 200


# ──────────────────────────── 시각화 ────────────────────────────

def draw_pose_cv2(img, kps, err_joints, draw_skeleton=True):
    """
    kps: [(x_norm, y_norm, v), ...] — 백엔드가 준 원본 정규화 좌표
         (등방 재정규화 전 값이므로 x는 W로, y는 H로 곱해서 그린다)
    """
    if kps is None:
        return
    H1, W1 = img.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX

    pts = [(int(x * W1), int(y * H1)) for x, y, _ in kps]

    # COCO17_SKELETON은 1-indexed COCO17 전용이라 관절 수가 다르면 건너뛴다
    if draw_skeleton and len(pts) == 17:
        for i, j in COCO17_SKELETON:
            cv2.line(img, pts[i - 1], pts[j - 1], (0, 255, 0), 2)

    for idx, (x_pt, y_pt) in enumerate(pts):
        clr = (0, 0, 255) if idx in err_joints else (0, 255, 0)
        cv2.circle(img, (x_pt, y_pt), 5, clr, -1)
        text = str(idx)
        cv2.putText(img, text, (x_pt + 4, y_pt - 4), font, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(img, text, (x_pt + 4, y_pt - 4), font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)


def visualize_results(analysis, user_video, pro_video, detect_fn, extract_fn):
    """오차가 큰 프레임들을 하나씩 넘겨보며 확인한다 (스페이스=다음, q=종료)."""
    details = analysis.get('details', [])
    if not details:
        print("시각화할 details가 없습니다.")
        return

    cap_u, _, rot_u = open_video(user_video)
    cap_s, _, rot_s = open_video(pro_video)
    fps_u = analysis['meta']['user_fps']
    fps_s = analysis['meta']['pro_fps']

    cv2.namedWindow("Result", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Result", CANVAS_W, CANVAS_H)

    num_kp = analysis['meta']['num_keypoints']

    for entry in details:
        # 원본 영상에서 프레임을 읽으므로 원본 기준 인덱스를 쓴다 (구간 지정 시 필수)
        u_frame = entry.get('user_frame_src', entry['user_frame'])
        s_frame = entry.get('standard_frame_src', entry['standard_frame'])
        # items는 feature 이름 단위라 관절 인덱스로 되돌려 표시한다
        err_joints = set()
        for name, _ in entry['items']:
            err_joints.update(feature_joint_indices(name, num_kp))

        cap_u.set(cv2.CAP_PROP_POS_FRAMES, u_frame)
        cap_s.set(cv2.CAP_PROP_POS_FRAMES, s_frame)
        ret_u, f_u = cap_u.read()
        ret_s, f_s = cap_s.read()
        if not (ret_u and ret_s):
            continue
        f_u, f_s = apply_rotation(f_u, rot_u), apply_rotation(f_s, rot_s)

        if detect_fn is not None:
            ku = extract_fn(f_u, detect_fn(f_u))
            ks = extract_fn(f_s, detect_fn(f_s))
        else:
            ku = extract_fn(f_u)
            ks = extract_fn(f_s)
        kps_u = ku[0] if ku else None
        kps_s = ks[0] if ks else None

        h = CANVAS_H - TABLE_H
        u_resized = cv2.resize(f_u, (CANVAS_W // 2, h))
        s_resized = cv2.resize(f_s, (CANVAS_W // 2, h))

        for img, label in ((u_resized, f"User: {u_frame / fps_u:.2f}s"),
                           (s_resized, f"Std : {s_frame / fps_s:.2f}s")):
            cv2.rectangle(img, (0, 0), (200, 30), (255, 255, 255), -1)
            cv2.putText(img, label, (10, 22), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 0, 0), 2, cv2.LINE_AA)

        draw_pose_cv2(u_resized, kps_u, err_joints)
        draw_pose_cv2(s_resized, kps_s, err_joints)
        combined = cv2.hconcat([u_resized, s_resized])

        # 하단 오차 표 — 오차 큰 순 상위 8개
        table = np.full((TABLE_H, CANVAS_W, 3), 255, dtype=np.uint8)
        items = entry['items'][:8]
        unit = analysis['stats']['error_unit']
        rows, cols = 3, len(items) + 1
        cell_h, cell_w = TABLE_H / rows, CANVAS_W / cols

        for r in range(rows + 1):
            cv2.line(table, (0, int(r * cell_h)), (CANVAS_W, int(r * cell_h)), (0, 0, 0), 1)
        for c in range(cols + 1):
            cv2.line(table, (int(c * cell_w), 0), (int(c * cell_w), TABLE_H), (0, 0, 0), 1)

        font = cv2.FONT_HERSHEY_SIMPLEX
        for r, htxt in enumerate(["No.", "Feature", f"Error({unit})"]):
            cv2.putText(table, htxt, (5, int((r + 0.7) * cell_h)),
                        font, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
        for idx, (name, err) in enumerate(items, start=1):
            x = int(idx * cell_w + 5)
            for r, txt in enumerate([str(idx), name[:16], f"{err:.1f}"]):
                cv2.putText(table, txt, (x, int((r + 0.7) * cell_h)),
                            font, 0.42, (0, 0, 0), 1, cv2.LINE_AA)

        cv2.imshow("Result", cv2.vconcat([combined, table]))
        while True:
            key = cv2.waitKey(0) & 0xFF
            if key == ord(' '):
                break
            if key in (ord('q'), 27):
                cap_u.release()
                cap_s.release()
                cv2.destroyAllWindows()
                return

    cap_u.release()
    cap_s.release()
    cv2.destroyAllWindows()


# ──────────────────────────── 메인 ────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Dance analysis with selectable pose backend")
    ap.add_argument('--pose-backend', choices=['yolo', 'mediapipe', 'hybrid', 'vitpose', 'rtmpose'],
                    default='yolo')
    ap.add_argument('--model-path', default='models/yolov8n-pose.pt')
    ap.add_argument('--pro-video', default=None, help='기준 영상 (기본: data/pro_dancer.mp4)')
    ap.add_argument('--user-video', default=None, help='사용자 영상 (기본: data/user_dancer.mp4)')
    ap.add_argument('--feature', choices=['angle', 'coord'], default='angle',
                    help='비교 표현. angle=관절 각도(권장), coord=좌표(A/B 비교용)')
    ap.add_argument('--pro-start-sec', type=float, default=None,
                    help='기준 영상에서 안무가 시작하는 시점(초). 지정하면 앞 여백을 잘라낸다')
    ap.add_argument('--user-start-sec', type=float, default=None,
                    help='사용자 영상에서 안무가 시작하는 시점(초)')
    ap.add_argument('--pro-end-sec', type=float, default=None,
                    help='기준 영상에서 안무가 끝나는 시점(초). 뒤 여백도 잘라낸다')
    ap.add_argument('--user-end-sec', type=float, default=None,
                    help='사용자 영상에서 안무가 끝나는 시점(초)')
    ap.add_argument('--band-sec', type=float, default=None,
                    help='DTW 밴드 폭(초). 시작 시점을 지정하면 기본 0.5초가 적용된다. '
                         '앵커 잔차 분석 기준 3σ 수준 (TASKS.md 시도 7)')
    ap.add_argument('--window', type=int, default=15,
                    help='DTW 밴드 제약 (프레임). --band-sec이 있으면 무시됨')
    ap.add_argument('--keep-psi-on-trim', action='store_true', default=False,
                    help='구간 지정 시에도 psi를 유지한다. 기본은 끄는 것 — 구간을 '
                         '확정했으면 psi가 그 양 끝을 다시 잘라내 손해다 (TASKS.md D23)')
    ap.add_argument('--psi-sec', type=float, default=3.0,
                    help='끝점 완화 길이(초). 사용자가 안무 일부만 췄거나 앞뒤 '
                         '여백이 있을 때 필요 (TASKS.md D19). 0이면 끔')
    ap.add_argument('--max-time-diff', type=float, default=0.6)
    ap.add_argument('--error-thresh', type=float, default=None,
                    help='이 값 이상 어긋난 항목만 리포트 (angle=도, coord=정규화거리)')
    ap.add_argument('--min-separation', type=float, default=0.3)
    ap.add_argument('--min-valid-ratio', type=float, default=0.3)
    ap.add_argument('--min-frontality', type=float, default=None,
                    help='정면성이 이보다 낮은 프레임 제외 (기본: 게이트하지 않고 통계만)')
    ap.add_argument('--conf-thresh', type=float, default=None,
                    help='관절 신뢰도 임계 (기본: 백엔드별 값)')
    ap.add_argument('--top-issues', type=int, default=10,
                    help='사용자에게 보여줄 상위 지적 개수')
    ap.add_argument('--out', default=None, help='결과 JSON 경로')
    ap.add_argument('--keep', type=int, default=20,
                    help='같은 backend/feature 결과를 최신 N개만 유지 (0이면 정리 안 함). '
                         '실행할 때마다 타임스탬프 파일이 무한 누적되던 문제 대응')
    ap.add_argument('--visualize', action='store_true',
                    help='오차 큰 프레임을 하나씩 확인 (키 입력 필요)')
    args = ap.parse_args()

    proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(proj_root, 'data')
    pro_video = args.pro_video or os.path.join(data_dir, 'pro_dancer.mp4')
    user_video = args.user_video or os.path.join(data_dir, 'user_dancer.mp4')

    print(f"[{args.pose_backend}] 기준 시퀀스 추출")
    std_seq, std_metrics = extract_pose_sequence(
        pro_video, args.pose_backend, model_path=args.model_path,
        conf_thresh=args.conf_thresh,
        start_sec=args.pro_start_sec, end_sec=args.pro_end_sec)

    print(f"[{args.pose_backend}] 사용자 시퀀스 추출")
    user_seq, user_metrics = extract_pose_sequence(
        user_video, args.pose_backend, model_path=args.model_path,
        conf_thresh=args.conf_thresh,
        start_sec=args.user_start_sec, end_sec=args.user_end_sec)

    std_feat = build_features(std_seq, args.feature)
    user_feat = build_features(user_seq, args.feature)

    if args.feature == 'angle':
        print(f"각도 feature {len(user_feat.names)}종 | "
              f"몸통 기준각 보정 기준(사용자) {user_feat.meta['torso_ref_deg']:+.1f}도, "
              f"(기준) {std_feat.meta['torso_ref_deg']:+.1f}도")
        print(f"정면성 중앙값 — 사용자 {user_feat.meta['frontality_median']:.3f}, "
              f"기준 {std_feat.meta['frontality_median']:.3f}")

    # **시작 시점만 지정해도 구간 지정으로 본다 (D23).** 끝점의 추가 이득은
    # 작았다 — natural1 ±5프레임 내 76.9%(시작만) vs 81.6%(시작+끝).
    # 시작점이 전역 오프셋을 제거하는 핵심이고 끝점은 보너스다.
    trimmed = args.pro_start_sec is not None and args.user_start_sec is not None

    # psi는 프레임 단위지만 인자는 초로 받는다 (fps가 영상마다 다르므로).
    # **구간을 지정했으면 psi를 끈다.** 끝점을 안 받았을 때도 마찬가지다 —
    # 처음엔 "끝이 불확실하니 psi가 필요하다"고 봤으나 실측이 반대였다:
    #   natural1 시작만 → psi끔 ±5f 76.9%·최대 0.73초 / psi=3초 72.2%·최대 3.23초
    #   natural2 시작만 → psi끔 86.7%·최대 0.23초 / psi=3초 75.0%·최대 0.87초
    # 시작점이 확정되면 좁은 밴드가 대각선을 잡아주는데, psi가 그 위에서 양 끝을
    # 또 건너뛰게 해 경로를 흐트러뜨린다. 밴드와 psi가 같은 역할을 중복 수행하며
    # 서로 방해하는 셈이다.
    if trimmed and args.psi_sec and args.keep_psi_on_trim is False:
        psi_frames = None
    else:
        psi_frames = int(round(args.psi_sec * user_seq.fps)) if args.psi_sec else None

    # 밴드 폭. 시작 시점을 받았으면 전역 오프셋이 제거된 상태이므로 좁게 잡는다.
    band_sec = args.band_sec if args.band_sec is not None else (0.5 if trimmed else None)
    if band_sec is not None:
        window = max(2, int(round(band_sec * std_seq.fps)))
        band_desc = f"밴드 ±{band_sec}초({window}프레임)"
    else:
        window = args.window
        band_desc = f"window {window}프레임"

    print(f"DTW 정렬 및 비교 ({band_desc}, psi={psi_frames}프레임)")
    result = compare_sequences(
        user_feat, std_feat,
        window=window,
        max_time_diff=args.max_time_diff,
        error_thresh=args.error_thresh,
        min_separation=args.min_separation,
        min_valid_ratio=args.min_valid_ratio,
        min_frontality=args.min_frontality,
        psi=psi_frames,
    )

    # 잘라낸 구간 기준 인덱스는 사용자에게 의미가 없으므로 원본 기준도 같이 남긴다
    u_off = user_seq.meta.get('source_start_frame', 0)
    s_off = std_seq.meta.get('source_start_frame', 0)
    for e in result.get('details', []):
        e['user_frame_src'] = e['user_frame'] + u_off
        e['standard_frame_src'] = e['standard_frame'] + s_off
        e['user_t_src'] = round(e['user_frame_src'] / user_seq.fps, 4)
        e['standard_t_src'] = round(e['standard_frame_src'] / std_seq.fps, 4)

    # 프레임별 오차 → 사용자용 구간 피드백
    if args.feature == 'angle':
        result['feedback'] = summarize(result.get('details', []),
                                       top_n=args.top_issues)

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    result['meta'] = {
        'timestamp': timestamp,
        'backend': args.pose_backend,
        'feature': args.feature,
        'feature_names': user_feat.names,
        'pro_video': pro_video,
        'user_video': user_video,
        'pro_fps': std_seq.fps,
        'user_fps': user_seq.fps,
        'trim': {
            'pro_start_sec': args.pro_start_sec, 'pro_end_sec': args.pro_end_sec,
            'user_start_sec': args.user_start_sec, 'user_end_sec': args.user_end_sec,
            'pro_start_frame': s_off, 'user_start_frame': u_off,
            'band_sec': band_sec, 'window_frames': window,
        },
        'num_keypoints': user_seq.num_keypoints,
        'params': {
            'window': args.window,
            'psi_sec': args.psi_sec,
            'psi_frames': psi_frames,
            'max_time_diff': args.max_time_diff,
            'error_thresh': args.error_thresh,
            'min_separation': args.min_separation,
            'min_valid_ratio': args.min_valid_ratio,
            'min_frontality': args.min_frontality,
            'conf_thresh': user_seq.meta.get('conf_thresh'),
        },
        'pro_metrics': std_metrics,
        'user_metrics': user_metrics,
        'pro_pose_coverage': std_seq.coverage(args.min_valid_ratio),
        'user_pose_coverage': user_seq.coverage(args.min_valid_ratio),
        'pro_feature_coverage': std_feat.coverage(args.min_valid_ratio),
        'user_feature_coverage': user_feat.coverage(args.min_valid_ratio),
        'torso_ref_deg': {'pro': std_feat.meta.get('torso_ref_deg'),
                          'user': user_feat.meta.get('torso_ref_deg')},
    }

    out_path = args.out or os.path.join(
        proj_root, 'analysis_result', args.pose_backend,
        f'{args.pose_backend}_{args.feature}_result_{timestamp}.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 같은 조합의 오래된 결과 정리 — 무한 누적 방지 (CLAUDE.md 알려진 문제 4).
    # --out을 직접 지정했으면 사용자가 관리하는 경로이므로 건드리지 않는다.
    if args.keep and not args.out:
        prefix = f'{args.pose_backend}_{args.feature}_result_'
        d = os.path.dirname(out_path)
        olds = sorted(f for f in os.listdir(d)
                      if f.startswith(prefix) and f.endswith('.json'))
        drop = olds[:-args.keep] if len(olds) > args.keep else []
        for f in drop:
            os.remove(os.path.join(d, f))
        if drop:
            print(f"  오래된 결과 {len(drop)}개 정리 (최신 {args.keep}개 유지)")

    st = result['stats']
    print()
    if result['score'] is None:
        print(f"  ⚠ {result.get('reason', '채점 가능한 대응쌍이 없습니다')}")
        print(f"  대응쌍 {st['path_len']}개 중 채점 0개")
        print(f"    제외 — 프레임게이트 {st['skipped_frame_gate']}, "
              f"시간필터 {st['skipped_time_filter']}, "
              f"정면성 {st['skipped_low_frontality']}, "
              f"유효항목없음 {st['skipped_no_valid_item']}")
        if st['skipped_time_filter'] > 0.5 * st['path_len']:
            print(f"    → 대부분 시간필터에서 걸림. --max-time-diff를 늘리거나 "
                  f"--psi-sec을 늘려보세요 (두 영상의 시작 여백 차이가 클 수 있음)")
    else:
        unit = st['error_unit']
        print(f"  두 영상 간 고정 오프셋(중앙값) {st['global_offset_sec']:+.2f}초")
        print(f"  점수 {result['score']:.1f} (잠정 환산) | "
              f"평균 오차 {st['mean_error']:.2f}{unit} "
              f"(중앙 {st['median_error']:.2f}, p90 {st['p90_error']:.2f})")
        print(f"  대응쌍 {st['path_len']}개 중 채점 {st['scored_pairs']}개 "
              f"({st['scored_pct']:.1f}%)")
        print(f"    제외 — 프레임게이트 {st['skipped_frame_gate']}, "
              f"시간필터 {st['skipped_time_filter']}, "
              f"정면성 {st['skipped_low_frontality']}, "
              f"유효항목없음 {st['skipped_no_valid_item']}")
        print(f"  리포트 프레임 {len(result['details'])}개")
        fb = result.get('feedback')
        if fb:
            print()
            print(f"  ── 피드백 ── 틀린 동작 {fb['issue_count']}개 "
                  f"(부위별 {fb['part_segment_count']}개를 묶음)")
            for i, s_ in enumerate(fb['top_issues'], 1):
                print(f"   {i}. [{s_['start_sec']:5.1f}~{s_['end_sec']:5.1f}s] "
                      f"{s_['group']} — {s_['message']}")
                print(f"      평균 {s_['mean_error_deg']:.0f}도, 심각도 {s_['severity']:.1f}, "
                      f"관련 부위 {len(s_['parts'])}개")
            if fb['unreliable_spans']:
                tot = sum(u['end_sec'] - u['start_sec'] for u in fb['unreliable_spans'])
                print(f"   확인 어려움 {len(fb['unreliable_spans'])}구간 (총 {tot:.1f}초) — 평가 제외")
    print(f"  저장: {out_path}")

    if args.visualize:
        detect_fn, extract_fn = make_pose_pipeline(
            args.pose_backend, model_path=args.model_path)
        visualize_results(result, user_video, pro_video, detect_fn, extract_fn)


if __name__ == '__main__':
    main()
