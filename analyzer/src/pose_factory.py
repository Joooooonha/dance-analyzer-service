from src.detection import detect
from src.pose_hybrid import extract_keypoints
from src.pose_hybrid import MediapipePose
from src.pose_yolo import YOLOPose

def make_pose_pipeline(backend:str, model_path:str=None):
    if backend.lower() in ('yolo', 'yolopose'):
        yolo = YOLOPose(model_path=model_path)
        return (None, yolo.extract_keypoints)  # detect_fn 없음, get_keypoints만
    elif backend.lower() in ('hybrid', 'yolo-mp', 'yolo+mp'):
        return (detect, extract_keypoints)
    elif backend.lower() in ('mediapipe',):
        # 전체 frame을 항상 대상으로 하는 dummy detect_fn
        def dummy_detect(frame):
            H, W = frame.shape[:2]
            return [[0, 0, W, H]]
        return (dummy_detect, extract_keypoints)
    else:
        raise ValueError(f"Unknown pose backend: {backend}")