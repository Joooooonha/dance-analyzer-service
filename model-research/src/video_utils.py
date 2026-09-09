# src/video_utils.py
"""영상 메타데이터를 안전하게 읽기 위한 유틸.

fps는 컨테이너/코덱에 따라 0, NaN, 90000 같은 비정상 값이 실제로 나온다.
파이프라인 전체가 같은 판정 기준을 쓰도록 여기 모아둔다. (TASKS.md D8)

**회전 메타데이터 처리 (TASKS.md D20).** 세로로 촬영한 iPhone 영상은 센서가
항상 가로로 찍은 원본 버퍼(예: 1920x1080)를 저장하고, "재생 시 90도 돌려서
보여줘라"는 QuickTime Display Matrix를 컨테이너에 별도로 기록한다.
`cv2.VideoCapture.read()`가 이 매트릭스를 적용하는지 여부는 **OpenCV 버전마다
다르다** (`CAP_PROP_ORIENTATION_AUTO` 기본값이 4.11에서는 0, 4.12에서는 1).
적용하지 않는 환경에서는 사람이 옆으로 누운 프레임이 그대로 포즈 모델에
들어가고, 적용하는 환경에서 우리가 또 돌리면 마찬가지로 누운 프레임이 된다.
→ `open_video`가 자동 회전을 **항상 끈 뒤** 우리가 직접 돌린다.
자세한 근거는 `_disable_backend_auto_rotation` 참조.

실측(YOLO-pose, 19프레임 샘플): 미보정 검출실패 2/19·신뢰도 중앙 0.721,
보정 후 검출실패 0/19·신뢰도 중앙 0.914. 단일 프레임 기준으로는 0.409 → 0.917.

이 프로젝트의 기존 테스트 영상(`data/videos/real/`, `candidates/`)은 우연히
raw 버퍼 자체가 이미 세로(1080x1920)로 저장돼 있어 이 문제를 겪지 않았다.
새로 촬영한 iPhone 원본에서 처음 발견됐다.
"""
import re
import subprocess

import cv2

FPS_FALLBACK = 30.0
FPS_MIN = 1.0
FPS_MAX = 240.0


def read_fps(cap, fallback: float = FPS_FALLBACK) -> float:
    """
    VideoCapture에서 fps를 읽되 범위 검사 후 비정상이면 fallback을 반환한다.

    cap: 열린 cv2.VideoCapture
    fallback: 비정상일 때 사용할 값 (기본 30.0)
    """
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS))
    except Exception:
        return fallback

    # NaN 체크 (NaN은 자기 자신과 같지 않음)
    if fps != fps:
        return fallback
    if fps < FPS_MIN or fps > FPS_MAX:
        return fallback
    return fps


_ROTATE_FN = {
    90: lambda f: cv2.rotate(f, cv2.ROTATE_90_CLOCKWISE),
    180: lambda f: cv2.rotate(f, cv2.ROTATE_180),
    270: lambda f: cv2.rotate(f, cv2.ROTATE_90_COUNTERCLOCKWISE),
}


_ffprobe_warned = False


def has_ffprobe() -> bool:
    """ffprobe를 쓸 수 있는지. 없으면 회전 보정이 불가능하다."""
    import shutil
    return shutil.which('ffprobe') is not None


def detect_rotation(path: str) -> int:
    """
    QuickTime/MP4 Display Matrix에서 재생 시 필요한 회전각을 구한다.
    returns: 0, 90, 180, 270 중 하나 (프레임에 시계방향으로 적용할 각도).
    매트릭스가 없거나 파싱에 실패하면 0을 반환한다.

    **ffprobe 자체가 없으면 경고를 남긴다.** 예전에는 조용히 0을 반환했는데,
    그러면 세로 촬영 영상이 옆으로 누운 채로 분석되고도 아무 신호가 없다.
    실제로 분석 서버(Fedora Asahi)에 ffprobe가 없어서 이 일이 일어났다 —
    관절 유효율이 0.909에서 0.809으로 떨어지고 평균 오차가 25도에서 31도로
    나빠졌는데, 원인을 알려주는 로그가 한 줄도 없었다.

    ffprobe의 텍스트 출력(`-show_streams`)은 Display Matrix side data 안에
    `rotation=-90` 형태로 이미 계산된 각도를 준다 (ffmpeg 내부 계산, 반시계
    방향이 양수인 부호 규약). 여기서는 원시 3x3 행렬을 직접 파싱하지 않고
    이 값을 그대로 읽어, 시계방향 각도로 부호만 뒤집는다.
    """
    global _ffprobe_warned
    if not has_ffprobe():
        if not _ffprobe_warned:
            _ffprobe_warned = True
            print("[경고] ffprobe가 없어 영상 회전 메타데이터를 읽을 수 없습니다. "
                  "세로로 촬영한 영상이 옆으로 누운 채 분석되어 정확도가 크게 "
                  "떨어집니다. 설치: sudo dnf install ffmpeg-free (또는 apt install ffmpeg)")
        return 0

    try:
        r = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
             '-show_streams', path],
            capture_output=True, text=True, timeout=10)
        m = re.search(r'^rotation=(-?\d+)', r.stdout, re.M)
        if not m:
            return 0
        rotation = int(m.group(1))              # ffmpeg 부호 규약(반시계 양수)
        cw = (-rotation) % 360                   # 시계방향 각도로 변환
        return cw if cw in (0, 90, 180, 270) else 0
    except Exception:
        return 0


def apply_rotation(frame, degrees: int):
    """degrees(0/90/180/270)만큼 시계방향으로 프레임을 돌린다."""
    fn = _ROTATE_FN.get(degrees)
    return fn(frame) if fn else frame


def _disable_backend_auto_rotation(cap) -> bool:
    """
    OpenCV 자체 자동 회전을 끈다. 성공하면 True.

    **이걸 명시하지 않으면 OpenCV 버전에 따라 결과가 달라진다.** 같은 영상
    (user_dancer.MOV, Display Matrix rotation=-90)을 두 환경에서 열어본 결과:

    | OpenCV | CAP_PROP_ORIENTATION_AUTO 기본값 | read()가 주는 프레임 |
    |---|---|---|
    | 4.11.0 (model-research venv) | 0 | 1080x1920 **원본 버퍼(누운 상태)** |
    | 4.12.0 (ai-server venv) | 1 | 1920x1080 **이미 세워진 상태** |

    4.12에서는 OpenCV가 이미 회전을 적용해서 주는데 `apply_rotation`이 한 번 더
    돌려서 사람이 옆으로 누운 프레임이 만들어졌다. 기본값에 의존하면 배포 환경의
    OpenCV 빌드가 바뀔 때마다 조용히 결과가 달라진다.

    → 항상 끄고 우리가 직접 돌린다. 끄지 못하면 rotation을 0으로 만들어
      이중 회전을 막는다(호출부 책임).
    """
    try:
        cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 0)
        return float(cap.get(cv2.CAP_PROP_ORIENTATION_AUTO)) == 0.0
    except Exception:
        # 속성 자체가 없는 구버전 OpenCV = 자동 회전 기능도 없음 → 끈 것과 같다
        return True


def open_video(path: str, auto_rotate: bool = True):
    """
    영상을 열고 (cap, fps, rotation)을 반환한다. 열 수 없으면 FileNotFoundError.

    rotation은 detect_rotation()의 결과(0/90/180/270)이며, auto_rotate=False면
    항상 0이다. 프레임을 직접 읽는 코드는 매 프레임에
    `apply_rotation(frame, rotation)`을 적용해야 한다.

    OpenCV의 자동 회전은 항상 끈 상태로 반환한다(위 함수 참조). 끄지 못한
    환경에서는 OpenCV가 이미 회전을 적용하므로 rotation=0을 돌려준다 —
    어느 쪽이든 호출부는 `apply_rotation(frame, rotation)`만 하면 된다.
    """
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise FileNotFoundError(f"영상을 열 수 없습니다: {path}")

    disabled = _disable_backend_auto_rotation(cap)
    rotation = detect_rotation(path) if auto_rotate else 0
    if not disabled:
        rotation = 0
    return cap, read_fps(cap), rotation


def probe_video(path: str) -> dict:
    """
    영상을 열지 않고 스펙만 확인할 때 사용.
    width/height는 회전 보정을 반영한 **실제 표시 크기**다.
    """
    cap, fps, rotation = open_video(path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if rotation in (90, 270):
        w, h = h, w
    info = {
        'path': path,
        'width': w,
        'height': h,
        'fps': fps,
        'rotation': rotation,
        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
    }
    cap.release()
    return info
