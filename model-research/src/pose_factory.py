import functools
import warnings

from src.detection import detect
from src.pose_hybrid import MediapipePose  # noqa: F401  (외부에서 import 함)
from src.pose_hybrid import extract_keypoints
from src.pose_yolo import YOLOPose


def make_pose_pipeline(backend: str, model_path: str = None,
                       model_complexity: int = 0):
    """
    returns: (detect_fn, extract_fn)
      detect_fn이 None이면 extract_fn(frame),
      아니면 extract_fn(frame, bboxes) 형태로 호출한다.

    model_complexity: mediapipe/hybrid 전용. 0=Lite, 1=Full, 2=Heavy.
    """
    b = backend.lower()

    if b in ('yolo', 'yolopose'):
        yolo = YOLOPose(model_path=model_path)
        return (None, yolo.extract_keypoints)

    if b in ('vitpose', 'vit'):
        # top-down이라 사람 bbox가 필요하다. hybrid와 달리 processor가
        # 종횡비를 지키며 정규화하고 원본 좌표계로 되돌려준다 (D18).
        from src.pose_vitpose import extract_keypoints as vit_extract
        kw = {} if model_path is None else {'model_id': model_path}
        return (detect, functools.partial(vit_extract, **kw))

    if b in ('rtmpose', 'rtm'):
        from src.pose_rtmpose import extract_keypoints as rtm_extract
        kw = {} if model_path is None else {'onnx_model': model_path}
        return (detect, functools.partial(rtm_extract, **kw))

    if b in ('mediapipe',):
        # 전체 프레임을 항상 대상으로 하는 dummy detect_fn
        def dummy_detect(frame):
            H, W = frame.shape[:2]
            return [[0, 0, W, H]]
        return (dummy_detect,
                functools.partial(extract_keypoints,
                                  model_complexity=model_complexity))

    if b in ('hybrid', 'yolo-mp', 'yolo+mp'):
        # [DEPRECATED] 실측에서 일관되게 나쁘다 (TASKS.md D15).
        # 같은 BlazePose 모델을 쓰는데도 관절 유효율이 mediapipe 97.2% 대비
        # 83.5%로 낮다. 차이는 입력이 전체 프레임이냐 YOLO bbox crop이냐뿐이라
        # crop 단계가 품질을 떨어뜨린다는 진단. 비교 기록으로만 남긴다.
        warnings.warn(
            "hybrid 백엔드는 폐기되었습니다 (crop 단계에서 품질 저하). "
            "mediapipe 또는 yolo를 사용하세요.",
            DeprecationWarning, stacklevel=2)
        return (detect,
                functools.partial(extract_keypoints,
                                  model_complexity=model_complexity))

    raise ValueError(f"Unknown pose backend: {backend}")
