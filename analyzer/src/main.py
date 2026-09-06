# src/main.py
import os
import time
import datetime
import json
import argparse
import tracemalloc
import cv2
import numpy as np
import psutil
from src.detection import detect
from src.dtw_compare import compare_sequences
from src.dtw_compare import flatten_keypoints
from src.metrics import compute_map, compute_pck, COCO17_JOINT_ORDER
from src.metrics import COCO17_SKELETON
from src.pose_factory import make_pose_pipeline
from scipy.spatial.distance import euclidean
from extract_pro_sequence import extract_sequence
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import mediapipe as mp

#coco joint 변환
COCO17_JOINT_ORDER = [0,2,5,7,8,11,12,13,14,15,16,23,24,25,26,27,28]
def to_coco_kp_list(frame, num_keypoints=17):
    kp_list = []
    for j in COCO17_JOINT_ORDER:
        if frame is not None and 0 <= j < len(frame):
            x, y, v = frame[j]
        else:
            x, y, v = 0.0, 0.0, 0.0
        kp_list.extend([float(x), float(y), float(v)])
    return kp_list  # 길이 51
def to_coco_xy_array(seq, joint_order=COCO17_JOINT_ORDER):
    """
    seq: (N, K, 2 or 3) 또는 list of (K, 2 or 3)
    joint_order: COCO17_JOINT_ORDER (필요한 17개 인덱스)
    반환: (N, 17, 2) numpy array
    """
    arr = []
    for frame in seq:
        # frame이 None이면 0으로 패딩
        if frame is None:
            arr.append(np.zeros((17, 2)))
            continue
        frame = np.array(frame)
        # 2차원: (K,2) or (K,3)
        if frame.shape[1] == 3:
            frame = frame[:, :2]
        # joint_order 순서로 17개만 뽑기, 부족하면 0패딩
        joints = []
        for j in joint_order:
            if j < len(frame):
                joints.append(frame[j])
            else:
                joints.append([0.0, 0.0])
        arr.append(joints)
    return np.array(arr)

# 고정 캔버스 크기 정의
CANVAS_W, CANVAS_H = 1280, 900
TABLE_H = 200  # 하단 테이블 영역 높이
def draw_pose_cv2(img, kps, err_joints, sx=1.0, sy=1.0):
    """
    img: 리사이즈된 프레임
    kps: 원본 프레임 기준 키포인트 [(x_pixel, y_pixel, v), ...]
    sx, sy: x,y 방향 스케일 팩터
    """
    if kps is None:
        return
    H1, W1=img.shape[:2]

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale=0.5
    thickness=1

    # 1) 스켈레톤 연결선
    pts = [(int(x * W1), int(y * H1)) for x, y, _ in kps]
    for i, j in COCO17_SKELETON:
        cv2.line(img, pts[i-1], pts[j-1], (0,255,0), 2)

    # 2) 관절 점 + 번호 그리기
    for idx, (x_pt, y_pt) in enumerate(pts):
        # 색상 결정 (에러 관절은 빨강, 정상은 초록)
        clr = (0,0,255) if idx in err_joints else (0,255,0)
        # 2-1) 점
        cv2.circle(img, (x_pt, y_pt), 5, clr, -1)
        # 2-2) 번호 텍스트 (점 오른쪽 위에)
        text = str(idx)
        # 배경용 외곽선
        cv2.putText(img, text, (x_pt+4, y_pt-4),
                    font, font_scale, (0,0,0), thickness+2, cv2.LINE_AA)
        # 실제 번호
        cv2.putText(img, text, (x_pt+4, y_pt-4),
                    font, font_scale, (255,255,255), thickness, cv2.LINE_AA)
        
def visualize_results(json_path, detect_fn, extract_fn):
    auto_play=False
    # 1) JSON 불러오기
    with open(json_path, 'r', encoding='utf-8') as f:
        analysis = json.load(f)

    proj_root = os.path.dirname(os.path.dirname(__file__))
    cap_u = cv2.VideoCapture(os.path.join(proj_root, 'data', 'user_dancer.mp4'))
    cap_s = cv2.VideoCapture(os.path.join(proj_root, 'data', 'pro_dancer.mp4'))
    fps = cap_u.get(cv2.CAP_PROP_FPS)

    # 2) 윈도우 설정
    cv2.namedWindow("Result", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Result", CANVAS_W, CANVAS_H)

    for entry in analysis['details']:
        u_frame, s_frame = entry['user_frame'], entry['standard_frame']
        err_joints = [j for j, _ in entry['joints']]

        # 3) 프레임 읽기
        cap_u.set(cv2.CAP_PROP_POS_FRAMES, u_frame)
        cap_s.set(cv2.CAP_PROP_POS_FRAMES, s_frame)
        ret_u, f_u = cap_u.read()
        ret_s, f_s = cap_s.read()
        if not (ret_u and ret_s):
            continue

        # 4) 키포인트 재추출
        if detect_fn is not None:
            kps_u = extract_fn(f_u, detect_fn(f_u))[0]
            kps_s = extract_fn(f_s, detect_fn(f_s))[0]
        else:
            kps_u = extract_fn(f_u)[0]
            kps_s = extract_fn(f_s)[0]

        # 5) BGR→RGB → 다시 BGR (imshow할 때 색깔 유지하기 위함)
        #    OpenCV 창에선 BGR 그대로 쓰셔도 됩니다.
        #    만약 matplotlib 대신 순수 BGR을 쓰신다면 이 부분 제거하세요.
        u_bgr = f_u.copy()
        s_bgr = f_s.copy()

        # 6) 리사이즈
        h = CANVAS_H - TABLE_H
        u_resized = cv2.resize(u_bgr, (CANVAS_W//2, h))
        s_resized = cv2.resize(s_bgr, (CANVAS_W//2, h))

        # 원본 프레임 크기
        H0_u, W0_u = f_u.shape[:2]
        H0_s, W0_s = f_s.shape[:2]
        # 리사이즈된 크기
        H1, W1 = u_resized.shape[:2]
        # x,y 스케일
        sx_u, sy_u = W1 / W0_u, H1 / H0_u
        sx_s, sy_s = W1 / W0_s, H1 / H0_s

        # 6.1) 타임스탬프 계산
        t_u = u_frame / fps
        t_s = s_frame / fps

        # 6.2) 텍스트 오버레이 (상단 좌측)
        text_u = f"User: {t_u:.2f}s"
        text_s = f"Std : {t_s:.2f}s"
        font      = cv2.FONT_HERSHEY_SIMPLEX
        scale     = 0.7
        thickness = 2
        color_bg  = (255,255,255)
        color_fg  = (0,0,0)

        # (1) 배경 박스 그리기
        cv2.rectangle(u_resized, (0,0), (200, 30), color_bg, -1)
        cv2.rectangle(s_resized, (0,0), (200, 30), color_bg, -1)
        # (2) 텍스트 그리기 (약간의 테두리 효과)
        cv2.putText(u_resized, text_u, (10, 22), font, scale, color_fg, thickness, cv2.LINE_AA)
        cv2.putText(s_resized, text_s, (10, 22), font, scale, color_fg, thickness, cv2.LINE_AA)



        # 7) 포즈 오버레이 (정규화된 coords → 리사이즈된 크기로 자동 변환)
        draw_pose_cv2(u_resized, kps_u, err_joints)
        draw_pose_cv2(s_resized, kps_s, err_joints)
    

        # 8) 가로 결합
        combined = cv2.hconcat([u_resized, s_resized])

        # 9) 하단 테이블 영역 생성 및 표 그리기
        table = np.full((TABLE_H, CANVAS_W, 3), 255, dtype=np.uint8)

        # 관절 정보 정리 ([(joint_id, err), …] 오름차순)
        joint_info = sorted(entry['joints'], key=lambda x: x[0])
        n = len(joint_info)

        # 행(row)과 열(col) 개수
        rows = 3               # No. / Joint ID. / Error Rate
        cols = n + 1           # 헤더 포함 총 열 수

        # 셀 크기
        cell_h = TABLE_H / rows
        cell_w = CANVAS_W / cols

        # 1) 격자선 그리기
        # 가로선 (rows+1 개)
        for r in range(rows+1):
            y = int(r * cell_h)
            cv2.line(table, (0, y), (CANVAS_W, y), (0,0,0), 1)
        # 세로선 (cols+1 개)
        for c in range(cols+1):
            x = int(c * cell_w)
            cv2.line(table, (x, 0), (x, TABLE_H), (0,0,0), 1)

        # 2) 텍스트 출력
        font       = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        th         = 1
        color      = (0,0,0)

        # 헤더 텍스트
        headers = ["No.", "Joint ID.", "Error Rate"]
        for r, htxt in enumerate(headers):
            x = int(cell_w * 0 + 5)
            y = int((r + 0.7) * cell_h)
            cv2.putText(table, htxt, (x, y), font, font_scale, color, th, cv2.LINE_AA)

        # 각 관절 데이터
        for idx, (joint_id, err) in enumerate(joint_info, start=1):
            x = int(idx * cell_w + 5)
            # No.
            y_no = int((0 + 0.7) * cell_h)
            cv2.putText(table, str(idx), (x, y_no), font, font_scale, color, th, cv2.LINE_AA)
            # Joint ID.
            y_jid = int((1 + 0.7) * cell_h)
            cv2.putText(table, str(joint_id), (x, y_jid), font, font_scale, color, th, cv2.LINE_AA)
            # Error Rate
            y_err = int((2 + 0.7) * cell_h)
            cv2.putText(table, f"{err:.2f}", (x, y_err), font, font_scale, color, th, cv2.LINE_AA)

        # 10) 최종 캔버스 결합
        final_canvas = cv2.vconcat([combined, table])
        cv2.imshow("Result", final_canvas)

        # 11) 화면 표시 & 키 제어 (auto-play 제거)
        cv2.imshow("Result", final_canvas)

        # 스페이스바 누를 때까지 대기
        while True:
            key = cv2.waitKey(0) & 0xFF
            if key == ord(' '):
                # 스페이스바: 다음 엔트리(프레임)로
                break
            elif key == ord('q'):
                # q: 즉시 종료
                cap_u.release()
                cap_s.release()
                cv2.destroyAllWindows()
                return
            # 그 외 키는 무시하고 계속 대기

# === 사용자 시퀀스 추출 및 성능 측정 ===
def extract_user_sequence_and_measure(video_path, detect_fn, extract_fn):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")
    orig_fps = cap.get(cv2.CAP_PROP_FPS)
    seq = []
    frame_count = 0
    total_detected=0

    tracemalloc.start()
    start_time = time.perf_counter()
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if detect_fn is not None:
            bboxes = detect_fn(frame)
            print(f"[Frame {frame_count}] YOLO bboxes:", bboxes)
            kps_list = extract_fn(frame, bboxes)
        else:
            kps_list = extract_fn(frame)
            print(f"[Frame {frame_count}] YOLO(no bboxes): 추론")
        if kps_list and kps_list[0] is not None:
            print(f"  → Pose detected, appending to seq.")
            seq.append(kps_list[0])
            total_detected += 1
            print(f"Frame{frame_count}: Pose added.")
        else:
            seq.append(None)
            print(f"Frame{frame_count}: Pose not found.")
        frame_count += 1
    print(f"Total frames: {frame_count}, Pose-detected frames: {total_detected}")
    elapsed = time.perf_counter() - start_time
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    cap.release()

    measured_fps   = frame_count / elapsed if elapsed > 0 else 0
    latency_avg_ms = (elapsed / frame_count * 1000) if frame_count > 0 else 0
    peak_mem_mb    = peak_mem / (1024**2)
    return seq, orig_fps, measured_fps, latency_avg_ms, peak_mem_mb

def safe_pad_kp(arr, num_keypoints):
    """
    arr: (num_keypoints, 3) 또는 None 또는 (0,)
    항상 (num_keypoints, 3) shape의 np.array로 반환
    """
    # None 또는 빈 배열이면 0패딩
    if arr is None:
        return np.zeros((num_keypoints, 3), dtype=np.float32)
    arr = np.array(arr)  # ←★★ 리스트 등도 numpy 배열로 변환
    if arr.shape == (0,):
        return np.zeros((num_keypoints, 3), dtype=np.float32)
    if arr.shape == (num_keypoints, 3):
        return arr
    if arr.ndim == 2 and arr.shape[1] == 2:
        v = np.ones((arr.shape[0], 1), dtype=arr.dtype)
        arr = np.concatenate([arr, v], axis=1)
    pad = np.zeros((num_keypoints, 3), dtype=np.float32)
    N = min(arr.shape[0], num_keypoints)
    pad[:N] = arr[:N]
    return pad

# === 메인 실행부 ===
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Dance Analysis with selectable pose backend")
    parser.add_argument('--pose-backend', choices=['yolo','mediapipe', 'hybrid'], default='hybird',
                        help="Which pose pipeline to use")
    parser.add_argument('--model-path',
                        default='models/yolov8n-pose.pt',
                        help='YOLO-Pose 가중치 파일 경로')
    args = parser.parse_args()

    # 파이프라인 결정
    detect_fn, extract_fn = make_pose_pipeline(args.pose_backend, model_path=args.model_path)

    proj_root    = os.path.dirname(os.path.dirname(__file__))
    data_dir     = os.path.join(proj_root, 'data')
    analysis_dir = os.path.join(proj_root, 'analysis_result', args.pose_backend)
    evaluate_dir = os.path.join(proj_root, 'evaluate_result', args.pose_backend)
    measure_dir  = os.path.join(proj_root, 'measure_result', args.pose_backend)
    os.makedirs(analysis_dir, exist_ok=True)
    os.makedirs(evaluate_dir, exist_ok=True)

    #기준 시퀀스 생성
    pro_seq = extract_sequence(
        video_path=os.path.join(data_dir, 'pro_dancer.mp4'),
        backend=args.pose_backend,
        model_path=args.model_path,   # hybrid도 무시해도 무방(에러 안 남)
        out_path=os.path.join(data_dir, 'pro_dancer_sequence.npy'),
        verbose=True
    )
    # 기준 시퀀스 로드
    standard_seq = pro_seq
    user_video   = os.path.join(data_dir, 'user_dancer.mp4')

    # 시퀀스 추출 + 성능 측정
    user_seq, orig_fps, measured_fps, latency_avg_ms, peak_mem_mb = extract_user_sequence_and_measure(user_video, detect_fn, extract_fn)
    # 프레임 크기 기반 image_size 산출
    cap = cv2.VideoCapture(user_video)
    ret, frame = cap.read()
    if not ret:
        raise FileNotFoundError("user_video에서 프레임을 읽을 수 없습니다.")
    h, w = frame.shape[:2]
    image_size = (h,w)
    cap.release()

    # 1) num_keypoints 지정
    # 백엔드에 따라 num_keypoints 자동 설정
    if args.pose_backend == 'yolo':
        num_keypoints = 17   # YOLO-pose 기준(COCO)
    else:
        num_keypoints = 33   # 보통 hybrid도 BlazePose 중심
     # 안전패딩 적용 
    user_seq = [safe_pad_kp(f, num_keypoints) for f in user_seq]
    standard_seq = [safe_pad_kp(f, num_keypoints) for f in standard_seq]

    # 2) compare_sequences에 인자로 추가
    score, details = compare_sequences(
        user_seq, 
        standard_seq, 
        fps=orig_fps, 
        max_time_diff=0.6,
        joint_error_thresh=0.33,
        min_separation=0.3,
        num_keypoints=num_keypoints,
        window=7
    )

    # 분석 결과 저장
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    analysis_path = os.path.join(
        analysis_dir,
        f'{args.pose_backend}_result_{timestamp}.json'
    )
    with open(analysis_path, 'w', encoding='utf-8') as f:
        json.dump({'timestamp': timestamp,
                   'backend': args.pose_backend,
                   'score': score,
                   'details': details},
                  f, ensure_ascii=False, indent=2)
    print(f"Analysis saved to: {analysis_path}")

    '''
    # COCO-format 예측 JSON 생성
    preds = []
    for idx, frame_kps in enumerate(user_seq):
        kp_list = to_coco_kp_list(frame_kps, num_keypoints=num_keypoints)
        preds.append({
            'image_id': idx+1,
            'category_id': 1,
            'keypoints': kp_list,
            'score': 1.0
        })  

    pred_json = os.path.join(
        measure_dir,
        f'{args.pose_backend}_pred_{timestamp}.json'
    )
    with open(pred_json, 'w', encoding='utf-8') as f:
        json.dump(preds, f, ensure_ascii=False, indent=2)
    '''
    
    # --- MAP, PCK 계산 ---
    # 아래 인자는 실제 함수 정의에 따라 맞춰야 합니다.
    # user_seq, standard_seq를 frame별로 전달하거나,
    # 또는 예측 keypoints와 정답 keypoints를 전달합니다.
    #annotation_dir = os.path.join(proj_root, 'gt_annotation')
    #pro_dancer_gt_json_path = os.path.join(annotation_dir, 'gt.json') # 데이터셋에 맞게 이름 수정
    #map_value = compute_map(gt_json=pro_dancer_gt_json_path, pred_json=pred_json)
    user_xy = to_coco_xy_array(user_seq, joint_order=COCO17_JOINT_ORDER)
    std_xy  = to_coco_xy_array(standard_seq, joint_order=COCO17_JOINT_ORDER)
    #pck_value = compute_pck(user_xy, std_xy, image_size=image_size)

    # --- 성능 지표 result dict 구성 ---
    result = {
        "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "pipeline": args.pose_backend,
        #"MAP": float(map_value),         # numpy.float일 경우 float()로 변환
        #"PCK": float(pck_value),
        "FPS": float(measured_fps),
        "latency_ms": float(latency_avg_ms),
        "memory_MB": float(peak_mem_mb)
    }

    # --- 저장 경로 및 파일명 생성 ---
    evaluate_dir = os.path.join(proj_root, 'evaluate_result', args.pose_backend)
    os.makedirs(evaluate_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    json_path = os.path.join(evaluate_dir, f'{args.pose_backend}_metrics_{timestamp}.json')

    # --- JSON 파일로 저장 ---
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"평가 결과가 {json_path}에 저장되었습니다.")

    visualize_results(analysis_path, detect_fn, extract_fn)
    print("시각화 성공!")