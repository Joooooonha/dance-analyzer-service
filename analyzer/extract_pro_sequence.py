import cv2
import numpy as np
from src.detection import detect

def extract_sequence(
    video_path,
    backend='yolo',
    model_path='models/yolov8n-pose.pt',
    out_path=None,
    verbose=True
):
    """
    지정한 비디오에서 백엔드 방식으로 포즈 시퀀스를 추출하여 npy로 저장하는 함수

    video_path : 입력 비디오 경로
    backend    : 'yolo' 또는 'hybrid'
    model_path : YOLO 백엔드의 경우 모델 경로
    out_path   : 저장할 npy 경로 (없으면 저장하지 않음)
    verbose    : 과정 출력 여부
    반환값: (프레임 수, 관절 수, 3) shape의 numpy array
    """
    if backend == 'yolo':
        from src.pose_yolo import YOLOPose
        pose_model = YOLOPose(model_path=model_path)
        num_keypoints = 17
        def get_kps(frame, boxes=None):
            return pose_model.extract_keypoints(frame)
    elif backend == 'hybrid':
        from src.pose_hybrid import extract_keypoints
        num_keypoints = 33
        def get_kps(frame, boxes):
            return extract_keypoints(frame, boxes)
    else:
        raise ValueError("지원하지 않는 백엔드입니다.")

    cap = cv2.VideoCapture(video_path)
    pro_seq = []
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        boxes = detect(frame)
        kps_list = get_kps(frame, boxes)

        # [안전] shape 체크 및 보정
        if not kps_list or len(kps_list) == 0 or kps_list[0] is None:
            arr = np.zeros((num_keypoints, 3), dtype=np.float32)
        else:
            arr = np.array(kps_list[0], dtype=np.float32)
            if arr.shape == (0,):
                arr = np.zeros((num_keypoints, 3), dtype=np.float32)
            elif arr.shape[0] != num_keypoints or arr.shape[-1] != 3:
                pad = np.zeros((num_keypoints, 3), dtype=np.float32)
                N = min(num_keypoints, arr.shape[0])
                pad[:N] = arr[:N]
                arr = pad
        if arr.shape != (num_keypoints, 3):
            if verbose:
                print(f"[프레임 {frame_idx}] 잘못된 shape: {arr.shape}, 강제 0패딩 처리")
            arr = np.zeros((num_keypoints, 3), dtype=np.float32)
        pro_seq.append(arr)
        frame_idx += 1

    cap.release()
    if verbose:
        print("쌓인 배열 shape 목록:", set([a.shape for a in pro_seq]))
    pro_seq = np.stack(pro_seq)
    if out_path:
        np.save(out_path, pro_seq)
        if verbose:
            print(f"Saved pro sequence: {pro_seq.shape} → {out_path}")
    return pro_seq