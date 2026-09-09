from ultralytics import YOLO

class YOLOPose:
    def __init__(self,
                 model_path: str = 'models/yolov8n-pose.pt',
                 device: str = 'mps'):
        self.model = YOLO(model_path)
        self.model.to(device)
        self.device = device

    def detect(self, frame):
        """
        YOLO-pose 모델은 bboxes만 따로 추출하는 게 의미가 없으므로
        프레임마다 빈 리스트를 반환
        """
        return []

    def extract_keypoints(self, frame, bboxes=None):
        """
        frame: BGR image (H, W, 3)
        returns: [
            [ (x_norm, y_norm, v), … ]  # x_norm, y_norm in [0,1]
            for each detected person
        ]
        """
        H, W = frame.shape[:2]
        results = self.model(frame, device=self.device, verbose=False)[0]
        kp_tensor = results.keypoints.data     # (num_people, 17, 3)
        arr       = kp_tensor.cpu().numpy()    # numpy array

        normalized = []
        for person_kp in arr:
            xs, ys, vs = person_kp[:,0], person_kp[:,1], person_kp[:,2]
            xs_norm = xs / W
            ys_norm = ys / H
            normalized.append([
                (float(xn), float(yn), float(v))
                for xn, yn, v in zip(xs_norm, ys_norm, vs)
            ])
        return normalized