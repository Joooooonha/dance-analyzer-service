"""
포즈 추출 모듈 (Pose Extractor)
MediaPipe Tasks API (PoseLandmarker)를 사용하여 영상에서 33개 관절 랜드마크 추출
호환: MediaPipe 0.10.30+ / Python 3.13+
"""

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import urllib.request
import os
from pathlib import Path


# MediaPipe BlazePose 33개 랜드마크 이름 정의
LANDMARK_NAMES = [
    "NOSE", "LEFT_EYE_INNER", "LEFT_EYE", "LEFT_EYE_OUTER",
    "RIGHT_EYE_INNER", "RIGHT_EYE", "RIGHT_EYE_OUTER",
    "LEFT_EAR", "RIGHT_EAR", "MOUTH_LEFT", "MOUTH_RIGHT",
    "LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_ELBOW", "RIGHT_ELBOW",
    "LEFT_WRIST", "RIGHT_WRIST", "LEFT_PINKY", "RIGHT_PINKY",
    "LEFT_INDEX", "RIGHT_INDEX", "LEFT_THUMB", "RIGHT_THUMB",
    "LEFT_HIP", "RIGHT_HIP", "LEFT_KNEE", "RIGHT_KNEE",
    "LEFT_ANKLE", "RIGHT_ANKLE", "LEFT_HEEL", "RIGHT_HEEL",
    "LEFT_FOOT_INDEX", "RIGHT_FOOT_INDEX"
]

# 주요 관절 인덱스 (춤 분석에 중요한 관절)
KEY_JOINTS = {
    "shoulders": [11, 12],  # LEFT_SHOULDER, RIGHT_SHOULDER
    "elbows": [13, 14],     # LEFT_ELBOW, RIGHT_ELBOW
    "wrists": [15, 16],     # LEFT_WRIST, RIGHT_WRIST
    "hips": [23, 24],       # LEFT_HIP, RIGHT_HIP
    "knees": [25, 26],      # LEFT_KNEE, RIGHT_KNEE
    "ankles": [27, 28],     # LEFT_ANKLE, RIGHT_ANKLE
}

# 모든 분석 대상 관절 (얼굴 제외)
ANALYSIS_JOINTS = [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]

# 모델 파일 경로
MODEL_PATH = Path(__file__).parent / "models" / "pose_landmarker_full.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task"


def download_model_if_needed():
    """모델 파일이 없으면 다운로드"""
    if MODEL_PATH.exists():
        return str(MODEL_PATH)
    
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"[모델 다운로드 중...] {MODEL_URL}")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print(f"[다운로드 완료] {MODEL_PATH}")
    return str(MODEL_PATH)


@dataclass
class FramePose:
    """단일 프레임의 포즈 데이터"""
    frame_number: int
    timestamp_ms: float
    landmarks: np.ndarray  # shape: (33, 3) - x, y, z 좌표
    visibility: np.ndarray  # shape: (33,) - 각 랜드마크의 가시성
    
    def get_landmark(self, index: int) -> Tuple[float, float, float]:
        """특정 랜드마크의 좌표 반환"""
        return tuple(self.landmarks[index])
    
    def get_visibility(self, index: int) -> float:
        """특정 랜드마크의 가시성 반환"""
        return self.visibility[index]


class PoseExtractor:
    """영상에서 포즈를 추출하는 클래스 (MediaPipe Tasks API 사용)"""
    
    def __init__(self):
        """초기화 - 모델 경로 확인만 수행"""
        self.model_path = download_model_if_needed()
        self._landmarker = None
        self._last_timestamp = -1
    
    def _create_landmarker(self):
        """새로운 PoseLandmarker 인스턴스 생성"""
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        return vision.PoseLandmarker.create_from_options(options)
        
    def extract_from_video(self, video_path: str) -> List[FramePose]:
        """
        비디오 파일에서 모든 프레임의 포즈 추출
        
        Args:
            video_path: 비디오 파일 경로
            
        Returns:
            List[FramePose]: 프레임별 포즈 데이터 리스트
        """
        # 각 영상마다 새로운 landmarker 생성 (타임스탬프 리셋)
        landmarker = self._create_landmarker()
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            landmarker.close()
            raise ValueError(f"영상 파일을 열 수 없습니다: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        poses = []
        frame_number = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # BGR -> RGB 변환
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # MediaPipe Image 생성
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                
                # 타임스탬프 계산 (밀리초)
                timestamp_ms = int((frame_number / fps) * 1000)
                
                # 포즈 추출
                results = landmarker.detect_for_video(mp_image, timestamp_ms)
                
                if results.pose_landmarks and len(results.pose_landmarks) > 0:
                    pose_landmarks = results.pose_landmarks[0]
                    
                    # 랜드마크 좌표 추출 (정규화된 좌표 0~1)
                    landmarks = np.array([
                        [lm.x, lm.y, lm.z] 
                        for lm in pose_landmarks
                    ])
                    visibility = np.array([
                        lm.visibility if hasattr(lm, 'visibility') else 1.0
                        for lm in pose_landmarks
                    ])
                    
                    poses.append(FramePose(
                        frame_number=frame_number,
                        timestamp_ms=float(timestamp_ms),
                        landmarks=landmarks,
                        visibility=visibility
                    ))
                
                frame_number += 1
        finally:
            cap.release()
            landmarker.close()
        
        print(f"[포즈 추출 완료] {video_path}: {len(poses)}/{frame_number} 프레임 추출")
        return poses
    
    def extract_from_frame(self, frame: np.ndarray, frame_number: int = 0, 
                          timestamp_ms: float = 0.0) -> Optional[FramePose]:
        """
        단일 프레임에서 포즈 추출 (IMAGE 모드 사용)
        
        Args:
            frame: BGR 형식의 이미지 프레임
            frame_number: 프레임 번호
            timestamp_ms: 타임스탬프 (밀리초)
            
        Returns:
            FramePose 또는 None (포즈 검출 실패 시)
        """
        # IMAGE 모드의 landmarker 생성 (단일 프레임용)
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5
        )
        landmarker = vision.PoseLandmarker.create_from_options(options)
        
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            results = landmarker.detect(mp_image)
            
            if results.pose_landmarks and len(results.pose_landmarks) > 0:
                pose_landmarks = results.pose_landmarks[0]
                
                landmarks = np.array([
                    [lm.x, lm.y, lm.z] 
                    for lm in pose_landmarks
                ])
                visibility = np.array([
                    lm.visibility if hasattr(lm, 'visibility') else 1.0
                    for lm in pose_landmarks
                ])
                
                return FramePose(
                    frame_number=frame_number,
                    timestamp_ms=timestamp_ms,
                    landmarks=landmarks,
                    visibility=visibility
                )
            return None
        finally:
            landmarker.close()


def create_frame_extractor():
    """
    영상 렌더링용 프레임 추출기 생성 - IMAGE 모드 landmarker 반환
    타임스탬프 문제 없이 개별 프레임 처리 가능
    """
    model_path = download_model_if_needed()
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5
    )
    return vision.PoseLandmarker.create_from_options(options)


def get_joint_vectors(pose: FramePose, joint_indices: List[int] = None) -> Dict[int, np.ndarray]:
    """
    포즈에서 관절 벡터 계산 (부모 관절에서 해당 관절로의 벡터)
    
    Args:
        pose: FramePose 객체
        joint_indices: 계산할 관절 인덱스 리스트 (None이면 ANALYSIS_JOINTS 사용)
        
    Returns:
        Dict[int, np.ndarray]: 관절 인덱스 -> 벡터 매핑
    """
    if joint_indices is None:
        joint_indices = ANALYSIS_JOINTS
    
    # 관절 연결 정의 (자식 -> 부모)
    joint_connections = {
        11: 12,  # LEFT_SHOULDER -> RIGHT_SHOULDER (어깨 기준선)
        12: 11,  # RIGHT_SHOULDER -> LEFT_SHOULDER
        13: 11,  # LEFT_ELBOW -> LEFT_SHOULDER
        14: 12,  # RIGHT_ELBOW -> RIGHT_SHOULDER
        15: 13,  # LEFT_WRIST -> LEFT_ELBOW
        16: 14,  # RIGHT_WRIST -> RIGHT_ELBOW
        17: 15,  # LEFT_PINKY -> LEFT_WRIST
        18: 16,  # RIGHT_PINKY -> RIGHT_WRIST
        19: 15,  # LEFT_INDEX -> LEFT_WRIST
        20: 16,  # RIGHT_INDEX -> RIGHT_WRIST
        21: 15,  # LEFT_THUMB -> LEFT_WRIST
        22: 16,  # RIGHT_THUMB -> RIGHT_WRIST
        23: 24,  # LEFT_HIP -> RIGHT_HIP (골반 기준선)
        24: 23,  # RIGHT_HIP -> LEFT_HIP
        25: 23,  # LEFT_KNEE -> LEFT_HIP
        26: 24,  # RIGHT_KNEE -> RIGHT_HIP
        27: 25,  # LEFT_ANKLE -> LEFT_KNEE
        28: 26,  # RIGHT_ANKLE -> RIGHT_KNEE
        29: 27,  # LEFT_HEEL -> LEFT_ANKLE
        30: 28,  # RIGHT_HEEL -> RIGHT_ANKLE
        31: 27,  # LEFT_FOOT_INDEX -> LEFT_ANKLE
        32: 28,  # RIGHT_FOOT_INDEX -> RIGHT_ANKLE
    }
    
    vectors = {}
    for joint_idx in joint_indices:
        if joint_idx in joint_connections:
            parent_idx = joint_connections[joint_idx]
            child_pos = pose.landmarks[joint_idx]
            parent_pos = pose.landmarks[parent_idx]
            vectors[joint_idx] = child_pos - parent_pos
    
    return vectors


if __name__ == "__main__":
    # 테스트 코드
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python pose_extractor.py <video_path>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    extractor = PoseExtractor()
    poses = extractor.extract_from_video(video_path)
    
    print(f"\n추출된 포즈 수: {len(poses)}")
    if poses:
        print(f"첫 프레임 랜드마크 shape: {poses[0].landmarks.shape}")
        print(f"마지막 프레임 타임스탬프: {poses[-1].timestamp_ms:.2f}ms")
