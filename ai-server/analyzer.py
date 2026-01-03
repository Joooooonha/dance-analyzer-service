"""
동작 비교 분석기 (Dance Movement Analyzer)
DTW로 프레임 정렬 후 관절별 코사인 유사도 계산
"""

import numpy as np
from scipy.spatial.distance import cosine
from fastdtw import fastdtw
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

from pose_extractor import (
    PoseExtractor, FramePose, LANDMARK_NAMES, ANALYSIS_JOINTS, get_joint_vectors
)


@dataclass
class JointError:
    """관절 오류 정보"""
    joint_name: str
    joint_id: int
    average_similarity: float
    error_frames: List[int]
    error_severity: str  # "low", "medium", "high"
    
    def to_dict(self) -> Dict:
        return {
            "joint_name": self.joint_name,
            "joint_id": self.joint_id,
            "average_similarity": round(self.average_similarity, 4),
            "error_frames": self.error_frames,
            "error_severity": self.error_severity
        }


@dataclass
class AnalysisResult:
    """분석 결과"""
    overall_score: float
    total_frames_reference: int
    total_frames_practice: int
    aligned_frames: int
    joint_errors: List[JointError]
    frame_details: List[Dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "overall_score": round(self.overall_score, 2),
            "analysis_details": {
                "total_frames_reference": self.total_frames_reference,
                "total_frames_practice": self.total_frames_practice,
                "aligned_frames": self.aligned_frames
            },
            "joint_errors": [e.to_dict() for e in self.joint_errors],
            "frame_details": self.frame_details,
            "timestamp": self.timestamp
        }


class DanceAnalyzer:
    """춤 동작 비교 분석기"""
    
    def __init__(self, 
                 similarity_threshold: float = 0.7,
                 include_frame_details: bool = True):
        """
        Args:
            similarity_threshold: 오류로 판단할 유사도 임계값 (이 값 미만이면 오류)
            include_frame_details: 프레임별 상세 정보 포함 여부
        """
        self.similarity_threshold = similarity_threshold
        self.include_frame_details = include_frame_details
        self.extractor = PoseExtractor()
    
    def analyze(self, reference_video: str, practice_video: str) -> AnalysisResult:
        """
        두 영상 비교 분석
        
        Args:
            reference_video: 기준 영상 경로
            practice_video: 연습 영상 경로
            
        Returns:
            AnalysisResult: 분석 결과
        """
        print(f"\n[분석 시작]")
        print(f"기준 영상: {reference_video}")
        print(f"연습 영상: {practice_video}")
        
        # 1. 포즈 추출
        print("\n[1단계] 포즈 추출 중...")
        ref_poses = self.extractor.extract_from_video(reference_video)
        prac_poses = self.extractor.extract_from_video(practice_video)
        
        if not ref_poses or not prac_poses:
            raise ValueError("포즈 추출에 실패했습니다. 영상에서 사람이 감지되지 않았습니다.")
        
        # 2. DTW로 프레임 정렬
        print("\n[2단계] DTW 프레임 정렬 중...")
        aligned_pairs = self._align_frames_dtw(ref_poses, prac_poses)
        print(f"정렬된 프레임 쌍: {len(aligned_pairs)}")
        
        # 3. 관절별 유사도 계산
        print("\n[3단계] 관절별 유사도 계산 중...")
        joint_similarities, frame_details = self._calculate_joint_similarities(
            ref_poses, prac_poses, aligned_pairs
        )
        
        # 4. 오류 관절 검출
        print("\n[4단계] 오류 관절 검출 중...")
        joint_errors = self._detect_joint_errors(joint_similarities)
        
        # 5. 전체 점수 계산
        overall_score = self._calculate_overall_score(joint_similarities)
        print(f"\n[분석 완료] 전체 일치도: {overall_score:.2f}%")
        
        return AnalysisResult(
            overall_score=overall_score,
            total_frames_reference=len(ref_poses),
            total_frames_practice=len(prac_poses),
            aligned_frames=len(aligned_pairs),
            joint_errors=joint_errors,
            frame_details=frame_details if self.include_frame_details else []
        )
    
    def _align_frames_dtw(self, ref_poses: List[FramePose], 
                          prac_poses: List[FramePose]) -> List[Tuple[int, int]]:
        """
        DTW를 사용하여 두 포즈 시퀀스 정렬
        
        Returns:
            List[Tuple[int, int]]: (기준 프레임 인덱스, 연습 프레임 인덱스) 쌍
        """
        # 각 프레임의 주요 관절 좌표를 벡터로 변환
        ref_vectors = [self._pose_to_vector(p) for p in ref_poses]
        prac_vectors = [self._pose_to_vector(p) for p in prac_poses]
        
        # FastDTW로 정렬
        distance, path = fastdtw(ref_vectors, prac_vectors, dist=self._vector_distance)
        
        return path
    
    def _pose_to_vector(self, pose: FramePose) -> np.ndarray:
        """포즈를 1D 벡터로 변환 (분석 대상 관절만)"""
        selected_landmarks = pose.landmarks[ANALYSIS_JOINTS]
        return selected_landmarks.flatten()
    
    def _vector_distance(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """두 벡터 간의 거리 (DTW 거리 함수)"""
        return np.linalg.norm(v1 - v2)
    
    def _calculate_joint_similarities(self, ref_poses: List[FramePose],
                                       prac_poses: List[FramePose],
                                       aligned_pairs: List[Tuple[int, int]]) -> Tuple[Dict, List]:
        """
        정렬된 프레임 쌍에 대해 관절별 유사도 계산
        
        Returns:
            Tuple[Dict, List]: 
                - 관절별 프레임별 유사도 {joint_id: [similarities]}
                - 프레임별 상세 정보 [{frame_idx, similarities, ...}]
        """
        joint_similarities = {joint_id: [] for joint_id in ANALYSIS_JOINTS}
        frame_details = []
        
        for ref_idx, prac_idx in aligned_pairs:
            ref_pose = ref_poses[ref_idx]
            prac_pose = prac_poses[prac_idx]
            
            # 관절 벡터 계산
            ref_vectors = get_joint_vectors(ref_pose, ANALYSIS_JOINTS)
            prac_vectors = get_joint_vectors(prac_pose, ANALYSIS_JOINTS)
            
            frame_sims = {}
            
            for joint_id in ANALYSIS_JOINTS:
                if joint_id in ref_vectors and joint_id in prac_vectors:
                    ref_vec = ref_vectors[joint_id]
                    prac_vec = prac_vectors[joint_id]
                    
                    # 코사인 유사도 계산 (1 - 코사인 거리)
                    # 제로 벡터 체크
                    if np.linalg.norm(ref_vec) > 1e-6 and np.linalg.norm(prac_vec) > 1e-6:
                        similarity = 1 - cosine(ref_vec, prac_vec)
                    else:
                        similarity = 1.0  # 둘 다 거의 움직임 없으면 일치로 간주
                    
                    # NaN 체크
                    if np.isnan(similarity):
                        similarity = 1.0
                    
                    joint_similarities[joint_id].append(similarity)
                    frame_sims[LANDMARK_NAMES[joint_id]] = round(similarity, 4)
            
            if self.include_frame_details:
                frame_details.append({
                    "reference_frame": ref_idx,
                    "practice_frame": prac_idx,
                    "joint_similarities": frame_sims
                })
        
        return joint_similarities, frame_details
    
    def _detect_joint_errors(self, joint_similarities: Dict) -> List[JointError]:
        """
        유사도가 임계값 미만인 관절 검출
        
        Returns:
            List[JointError]: 오류 관절 리스트 (오류 정도 높은 순)
        """
        errors = []
        
        for joint_id, similarities in joint_similarities.items():
            if not similarities:
                continue
            
            avg_sim = np.mean(similarities)
            
            # 오류 프레임 검출 (임계값 미만인 프레임들)
            error_frames = [
                i for i, sim in enumerate(similarities) 
                if sim < self.similarity_threshold
            ]
            
            if error_frames:
                # 오류 심각도 판단
                error_ratio = len(error_frames) / len(similarities)
                if error_ratio > 0.5 or avg_sim < 0.5:
                    severity = "high"
                elif error_ratio > 0.2 or avg_sim < 0.7:
                    severity = "medium"
                else:
                    severity = "low"
                
                errors.append(JointError(
                    joint_name=LANDMARK_NAMES[joint_id],
                    joint_id=joint_id,
                    average_similarity=avg_sim,
                    error_frames=error_frames[:20],  # 최대 20개 프레임만 표시
                    error_severity=severity
                ))
        
        # 오류 정도 높은 순으로 정렬
        errors.sort(key=lambda e: e.average_similarity)
        
        return errors
    
    def _calculate_overall_score(self, joint_similarities: Dict) -> float:
        """
        전체 일치도 점수 계산 (0~100)
        주요 관절에 더 높은 가중치 부여
        """
        # 주요 관절 가중치 정의
        weights = {
            11: 1.5, 12: 1.5,  # 어깨
            13: 1.5, 14: 1.5,  # 팔꿈치
            15: 1.2, 16: 1.2,  # 손목
            23: 1.5, 24: 1.5,  # 골반
            25: 1.5, 26: 1.5,  # 무릎
            27: 1.2, 28: 1.2,  # 발목
        }
        
        total_weighted_sim = 0
        total_weight = 0
        
        for joint_id, similarities in joint_similarities.items():
            if similarities:
                weight = weights.get(joint_id, 1.0)
                avg_sim = np.mean(similarities)
                total_weighted_sim += avg_sim * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        # 0~100 스케일로 변환
        return (total_weighted_sim / total_weight) * 100


def analyze_videos(reference_path: str, practice_path: str, 
                   threshold: float = 0.7,
                   generate_video: bool = False) -> Tuple[AnalysisResult, str]:
    """
    편의 함수: 두 영상 분석
    
    Args:
        reference_path: 기준 영상 경로
        practice_path: 연습 영상 경로
        threshold: 오류 판단 임계값
        generate_video: 분석 영상 생성 여부
        
    Returns:
        Tuple[AnalysisResult, str]: (분석 결과, 영상 경로 또는 None)
    """
    analyzer = DanceAnalyzer(similarity_threshold=threshold, include_frame_details=True)
    result = analyzer.analyze(reference_path, practice_path)
    
    video_path = None
    if generate_video:
        from video_renderer import create_analysis_video
        print("\n[5단계] 분석 영상 생성 중...")
        video_path = create_analysis_video(reference_path, practice_path, result)
    
    return result, video_path


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="춤 동작 비교 분석기")
    parser.add_argument("reference", help="기준 영상 경로")
    parser.add_argument("practice", help="연습 영상 경로")
    parser.add_argument("--threshold", "-t", type=float, default=0.7, 
                        help="오류 판단 임계값 (기본값: 0.7)")
    parser.add_argument("--video", "-v", action="store_true",
                        help="분석 과정 영상 생성 (오류 관절 빨간색 표시)")
    
    args = parser.parse_args()
    
    result, video_path = analyze_videos(
        args.reference, 
        args.practice, 
        args.threshold,
        args.video
    )
    
    # 콘솔에 결과 출력
    print("\n" + "="*50)
    print("분석 결과 요약")
    print("="*50)
    print(f"전체 일치도: {result.overall_score:.2f}%")
    print(f"오류 관절 수: {len(result.joint_errors)}")
    
    if result.joint_errors:
        print("\n주요 오류 관절:")
        for error in result.joint_errors[:5]:
            print(f"  - {error.joint_name}: 유사도 {error.average_similarity:.2f} ({error.error_severity})")
    
    # JSON으로 저장
    from result_writer import save_result
    output_path = save_result(result, "analysis")
    print(f"\n결과 저장됨: {output_path}")
    
    if video_path:
        print(f"분석 영상: {video_path}")

