"""기준(프로) 시퀀스 추출 — `src.extract`로 위임하는 얇은 래퍼.

예전에는 여기에 별도 추출 루프가 있었고 `yolo`/`hybrid`만 지원해서
`pose_factory.py`(3종 지원)와 backend 목록이 어긋나 있었다
(CLAUDE.md 알려진 문제 3). 이제 사용자 영상과 같은 경로를 쓰므로 해소됐다.

단독 실행도 가능하다 (프로젝트 루트에서):

    python -m extract_pro_sequence --video data/videos/real/pro_dancer.mp4 \
        --backend yolo --out data/pro_sequence_yolo.npz
"""
import argparse

from src.extract import extract_pose_sequence


def extract_sequence(video_path, backend='yolo',
                     model_path='models/yolov8n-pose.pt',
                     out_path=None, verbose=True, conf_thresh=None):
    """
    returns: (PoseSequence, metrics)

    주의: 예전 시그니처는 (프레임수, 관절수, 3) numpy 배열을 반환했다.
    이제는 유효성 마스크와 fps를 함께 들고 다니는 PoseSequence를 반환한다.
    """
    seq, metrics = extract_pose_sequence(
        video_path, backend, model_path=model_path,
        conf_thresh=conf_thresh, verbose=verbose)

    if out_path:
        seq.save(out_path)
        if verbose:
            print(f"  저장: {out_path}")
    return seq, metrics


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description="기준 시퀀스 추출")
    ap.add_argument('--video', required=True)
    ap.add_argument('--backend', default='yolo',
                    choices=['yolo', 'mediapipe', 'hybrid'])
    ap.add_argument('--model-path', default='models/yolov8n-pose.pt')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    extract_sequence(args.video, backend=args.backend,
                     model_path=args.model_path, out_path=args.out)
