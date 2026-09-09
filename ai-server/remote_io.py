"""서명된 URL로 영상을 받아오고 결과물을 올린다.

**이 서버는 저장소 자격증명을 갖지 않는다.** Spring이 요청마다 짧은 수명의
presigned URL을 발급해서 넘겨주고, 여기서는 그 URL로만 읽고 쓴다.

맥미니는 집에 있는 홈서버라 EC2보다 물리적 통제가 약하다. 여기에 R2 쓰기 키를
두면 기기가 뚫렸을 때 버킷 전체가 위험해지지만, 지금 구조에서는 얻을 수 있는
것이 곧 만료될 URL 몇 개뿐이다.
"""
import os
import tempfile
import urllib.error
import urllib.request


class RemoteIOError(RuntimeError):
    """다운로드/업로드 실패. 호출부가 분석을 중단하고 보고하도록."""


# 영상 한 편 받는 데 걸리는 시간. R2에서 수십 MB를 받으므로 넉넉히 잡는다.
DOWNLOAD_TIMEOUT_SEC = 300
UPLOAD_TIMEOUT_SEC = 120

# 받을 수 있는 최대 크기. 서명 URL이 가리키는 대상이 예상 밖으로 클 때
# 디스크를 채우지 않도록 막는다.
MAX_DOWNLOAD_BYTES = 500 * 1024 * 1024


def download_to_temp(url, suffix='.mp4'):
    """
    URL의 내용을 임시 파일로 내려받고 경로를 돌려준다.

    OpenCV가 파일 경로를 요구하므로 메모리에 두지 않고 파일로 떨어뜨린다.
    호출부가 다 쓴 뒤 반드시 지워야 한다(`cleanup` 참고).
    """
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT_SEC) as res, \
                open(path, 'wb') as out:
            total = 0
            while True:
                chunk = res.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise RemoteIOError(
                        f'영상이 너무 큽니다 (>{MAX_DOWNLOAD_BYTES // (1024*1024)}MB)')
                out.write(chunk)
        if total == 0:
            raise RemoteIOError('빈 파일을 받았습니다.')
        return path
    except RemoteIOError:
        cleanup(path)
        raise
    except (urllib.error.URLError, OSError) as e:
        cleanup(path)
        raise RemoteIOError(f'영상을 받지 못했습니다: {e}') from e


def upload_file(url, path, content_type):
    """
    파일을 서명된 URL로 PUT한다.

    **Content-Type이 서명에 포함**되므로 발급 때와 정확히 같은 값을 보내야 한다.
    다르면 저장소가 403으로 거부한다.

    returns: 성공하면 True. 실패해도 예외를 던지지 않는다 — 이미지 하나를 못
             올렸다고 분석 결과 전체를 버릴 이유는 없다.
    """
    try:
        with open(path, 'rb') as f:
            data = f.read()
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', content_type)
        req.add_header('Content-Length', str(len(data)))
        with urllib.request.urlopen(req, timeout=UPLOAD_TIMEOUT_SEC) as res:
            return 200 <= res.status < 300
    except (urllib.error.URLError, OSError) as e:
        print(f'[경고] 업로드 실패 ({content_type}): {e}')
        return False


def cleanup(*paths):
    """임시 파일을 지운다. 없으면 조용히 넘어간다."""
    for p in paths:
        if not p:
            continue
        try:
            os.unlink(p)
        except OSError:
            pass
