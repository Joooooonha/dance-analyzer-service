"""[사용 안 함 — v3.0에서 visualize.py로 대체됨]

대체된 이유: **DTW 정렬 결과를 쓰지 않았다.**
`ref_frame = self._get_frame(ref_cap, frame_idx)` / `prac_frame =
self._get_frame(prac_cap, frame_idx)` 로 **같은 인덱스**의 프레임을 짝지어
보여준다. 두 영상의 시작 시점이 3초만 어긋나도 화면의 두 사람은 전혀 다른
동작을 하고 있게 된다. 정렬을 하는 이유 자체가 사라지는 결함이다.
"""
"""
결과 보고서 생성 모듈 (Report Generator)
상위 N개 오류 프레임에 대해 Reference vs Practice 비교 이미지 생성
"""

import cv2
import numpy as np
from typing import List, Dict, Set, Tuple, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field

from pose_extractor import FramePose, LANDMARK_NAMES, ANALYSIS_JOINTS


# MediaPipe 관절 연결 정의
POSE_CONNECTIONS = [
    (11, 12), (11, 23), (12, 24), (23, 24),  # 몸통
    (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),  # 왼팔
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),  # 오른팔
    (23, 25), (25, 27), (27, 29), (27, 31), (29, 31),  # 왼다리
    (24, 26), (26, 28), (28, 30), (28, 32), (30, 32),  # 오른다리
]


@dataclass
class FrameFeedback:
    """프레임별 피드백 정보"""
    frame_number: int
    timestamp_ms: float
    error_joints: List[str]
    avg_similarity: float
    reference_image_path: str = ""
    practice_image_path: str = ""
    comparison_image_path: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "frame_number": self.frame_number,
            "timestamp_sec": round(self.timestamp_ms / 1000, 2),
            "error_joints": self.error_joints,
            "average_similarity": round(self.avg_similarity, 2),
            "comparison_image": self.comparison_image_path
        }


@dataclass
class AnalysisReport:
    """분석 보고서"""
    overall_score: float
    total_frames: int
    top_error_frames: List[FrameFeedback]
    top_error_joints: List[Dict]  # 상위 오류 관절
    video_path: str = ""
    json_path: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "overall_score": round(self.overall_score, 2),
            "total_frames": self.total_frames,
            "top_error_frames": [f.to_dict() for f in self.top_error_frames],
            "top_error_joints": self.top_error_joints[:5],  # 상위 5개 관절만
            "video_path": self.video_path,
            "json_path": self.json_path,
            "timestamp": self.timestamp
        }


class ReportGenerator:
    """분석 결과 보고서 생성기"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
    
    def generate_report(self, 
                        reference_video: str,
                        practice_video: str,
                        reference_poses: List[FramePose],
                        practice_poses: List[FramePose],
                        analysis_result,
                        top_n: int = 10) -> AnalysisReport:
        """
        상위 N개 오류 프레임에 대한 보고서 생성
        
        Args:
            reference_video: 기준 영상 경로
            practice_video: 연습 영상 경로
            reference_poses: 기준 영상의 포즈 리스트
            practice_poses: 연습 영상의 포즈 리스트
            analysis_result: AnalysisResult 객체
            top_n: 상위 오류 프레임 수
            
        Returns:
            AnalysisReport: 보고서 객체
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 프레임별 오류 심각도 계산
        frame_errors = self._calculate_frame_errors(analysis_result)
        
        # 상위 N개 오류 프레임 선택
        sorted_frames = sorted(frame_errors.items(), key=lambda x: x[1]['severity'], reverse=True)
        top_frames = sorted_frames[:top_n]
        
        # 비교 이미지 생성
        feedbacks = []
        ref_cap = cv2.VideoCapture(reference_video)
        prac_cap = cv2.VideoCapture(practice_video)
        
        ref_pose_map = {p.frame_number: p for p in reference_poses}
        prac_pose_map = {p.frame_number: p for p in practice_poses}
        
        for frame_idx, error_info in top_frames:
            # 프레임 추출
            ref_frame = self._get_frame(ref_cap, frame_idx)
            prac_frame = self._get_frame(prac_cap, frame_idx)
            
            if ref_frame is None or prac_frame is None:
                continue
            
            # 포즈 오버레이
            ref_pose = ref_pose_map.get(frame_idx)
            prac_pose = prac_pose_map.get(frame_idx)
            
            if ref_pose is not None:
                ref_frame = self._draw_pose_on_frame(
                    ref_frame, ref_pose, set(), "Reference"
                )
            if prac_pose is not None:
                prac_frame = self._draw_pose_on_frame(
                    prac_frame, prac_pose, error_info['joints'], "Practice"
                )
            
            # 비교 이미지 생성 (좌: Reference, 우: Practice)
            comparison = self._create_comparison_image(ref_frame, prac_frame, frame_idx)
            
            # 저장
            img_filename = f"comparison_{timestamp}_frame{frame_idx}.jpg"
            img_path = self.images_dir / img_filename
            cv2.imwrite(str(img_path), comparison)
            
            # 타임스탬프 계산
            timestamp_ms = prac_pose.timestamp_ms if prac_pose else frame_idx * 33.33
            
            feedbacks.append(FrameFeedback(
                frame_number=frame_idx,
                timestamp_ms=timestamp_ms,
                error_joints=[LANDMARK_NAMES[j] for j in error_info['joints']],
                avg_similarity=error_info['severity'],
                comparison_image_path=str(img_path)
            ))
        
        ref_cap.release()
        prac_cap.release()
        
        # 상위 오류 관절 정보
        top_joints = []
        if hasattr(analysis_result, 'joint_errors'):
            for error in analysis_result.joint_errors[:5]:
                top_joints.append({
                    "joint_name": error.joint_name,
                    "joint_id": error.joint_id,
                    "average_similarity": round(error.average_similarity, 2),
                    "severity": error.error_severity
                })
        
        return AnalysisReport(
            overall_score=analysis_result.overall_score,
            total_frames=analysis_result.total_frames_practice,
            top_error_frames=feedbacks,
            top_error_joints=top_joints
        )
    
    def _calculate_frame_errors(self, analysis_result) -> Dict[int, Dict]:
        """프레임별 오류 정보 계산"""
        frame_errors = {}
        
        if hasattr(analysis_result, 'frame_details'):
            for detail in analysis_result.frame_details:
                frame_idx = detail.get('practice_frame', -1)
                if frame_idx < 0:
                    continue
                
                error_joints = set()
                similarities = []
                
                for joint_name, sim in detail.get('joint_similarities', {}).items():
                    similarities.append(sim)
                    if sim < 0.7:
                        try:
                            joint_id = LANDMARK_NAMES.index(joint_name)
                            error_joints.add(joint_id)
                        except ValueError:
                            pass
                
                if error_joints:
                    # 오류 심각도: 오류 관절 수 * (1 - 평균 유사도)
                    avg_sim = np.mean(similarities) if similarities else 1.0
                    severity = len(error_joints) * (1 - avg_sim)
                    
                    frame_errors[frame_idx] = {
                        'joints': error_joints,
                        'severity': severity,
                        'avg_similarity': avg_sim
                    }
        
        return frame_errors
    
    def _get_frame(self, cap, frame_idx: int) -> Optional[np.ndarray]:
        """비디오에서 특정 프레임 추출"""
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        return frame if ret else None
    
    def _draw_pose_on_frame(self, frame: np.ndarray, pose: FramePose, 
                            error_joints: Set[int], label: str) -> np.ndarray:
        """프레임에 포즈 그리기"""
        h, w = frame.shape[:2]
        landmarks = pose.landmarks
        
        # 연결선 그리기
        for start_idx, end_idx in POSE_CONNECTIONS:
            start = (int(landmarks[start_idx][0] * w), int(landmarks[start_idx][1] * h))
            end = (int(landmarks[end_idx][0] * w), int(landmarks[end_idx][1] * h))
            
            if start_idx in error_joints or end_idx in error_joints:
                color = (0, 0, 255)  # 빨간색
                thickness = 3
            else:
                color = (0, 255, 0)  # 초록색
                thickness = 2
            
            cv2.line(frame, start, end, color, thickness)
        
        # 관절점 그리기
        for joint_id in ANALYSIS_JOINTS:
            point = (int(landmarks[joint_id][0] * w), int(landmarks[joint_id][1] * h))
            
            if joint_id in error_joints:
                cv2.circle(frame, point, 8, (0, 0, 255), -1)
                cv2.circle(frame, point, 12, (0, 0, 200), 2)
            else:
                cv2.circle(frame, point, 5, (0, 255, 0), -1)
        
        # 라벨 추가
        cv2.rectangle(frame, (10, 10), (200, 50), (0, 0, 0), -1)
        cv2.putText(frame, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return frame
    
    def _create_comparison_image(self, ref_frame: np.ndarray, prac_frame: np.ndarray, 
                                  frame_idx: int) -> np.ndarray:
        """Reference와 Practice를 나란히 비교하는 이미지 생성"""
        # 크기 맞추기
        h1, w1 = ref_frame.shape[:2]
        h2, w2 = prac_frame.shape[:2]
        
        target_h = max(h1, h2)
        target_w = max(w1, w2)
        
        # 리사이즈
        ref_resized = cv2.resize(ref_frame, (target_w, target_h))
        prac_resized = cv2.resize(prac_frame, (target_w, target_h))
        
        # 나란히 배치
        comparison = np.hstack([ref_resized, prac_resized])
        
        # 구분선
        cv2.line(comparison, (target_w, 0), (target_w, target_h), (255, 255, 255), 3)
        
        # 프레임 번호 표시
        cv2.rectangle(comparison, (target_w - 100, target_h - 40), 
                      (target_w + 100, target_h), (0, 0, 0), -1)
        cv2.putText(comparison, f"Frame: {frame_idx}", (target_w - 80, target_h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return comparison


def generate_analysis_report(reference_video: str,
                             practice_video: str,
                             reference_poses: List[FramePose],
                             practice_poses: List[FramePose],
                             analysis_result,
                             top_n: int = 10) -> AnalysisReport:
    """편의 함수: 분석 보고서 생성"""
    generator = ReportGenerator()
    return generator.generate_report(
        reference_video, practice_video,
        reference_poses, practice_poses,
        analysis_result, top_n
    )
