"""
영상 렌더링 모듈 (Video Renderer)
분석 과정을 영상으로 저장, 오류 관절은 빨간색으로 표시
"""

import cv2
import numpy as np
from typing import List, Dict, Set, Tuple, Optional
from pathlib import Path
from datetime import datetime

from pose_extractor import PoseExtractor, FramePose, LANDMARK_NAMES, ANALYSIS_JOINTS


# MediaPipe 관절 연결 정의 (선으로 연결할 관절 쌍)
POSE_CONNECTIONS = [
    # 얼굴
    (0, 1), (1, 2), (2, 3), (3, 7),  # 왼쪽 눈
    (0, 4), (4, 5), (5, 6), (6, 8),  # 오른쪽 눈
    (9, 10),  # 입
    # 몸통
    (11, 12),  # 어깨
    (11, 23), (12, 24),  # 어깨-골반
    (23, 24),  # 골반
    # 왼팔
    (11, 13), (13, 15),  # 어깨-팔꿈치-손목
    (15, 17), (15, 19), (15, 21),  # 손목-손가락
    (17, 19),  # 손
    # 오른팔
    (12, 14), (14, 16),  # 어깨-팔꿈치-손목
    (16, 18), (16, 20), (16, 22),  # 손목-손가락
    (18, 20),  # 손
    # 왼다리
    (23, 25), (25, 27),  # 골반-무릎-발목
    (27, 29), (27, 31), (29, 31),  # 발
    # 오른다리
    (24, 26), (26, 28),  # 골반-무릎-발목
    (28, 30), (28, 32), (30, 32),  # 발
]


class VideoRenderer:
    """분석 과정을 영상으로 렌더링하는 클래스"""
    
    def __init__(self, 
                 output_dir: str = "output",
                 error_color: Tuple[int, int, int] = (0, 0, 255),  # BGR: 빨간색
                 normal_color: Tuple[int, int, int] = (0, 255, 0),  # BGR: 초록색
                 reference_color: Tuple[int, int, int] = (255, 165, 0),  # BGR: 주황색
                 line_thickness: int = 2,
                 circle_radius: int = 5):
        """
        Args:
            output_dir: 출력 디렉토리
            error_color: 오류 관절 색상 (BGR)
            normal_color: 정상 관절 색상 (BGR)
            reference_color: 기준 영상 관절 색상 (BGR)
            line_thickness: 선 두께
            circle_radius: 관절점 반지름
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.error_color = error_color
        self.normal_color = normal_color
        self.reference_color = reference_color
        self.line_thickness = line_thickness
        self.circle_radius = circle_radius
    
    def render_comparison_video(self,
                                 practice_video_path: str,
                                 practice_poses: List[FramePose],
                                 reference_poses: List[FramePose],
                                 aligned_pairs: List[Tuple[int, int]],
                                 frame_errors: Dict[int, Set[int]],
                                 output_name: str = None) -> str:
        """
        연습 영상에 분석 결과를 오버레이하여 영상 생성
        
        Args:
            practice_video_path: 연습 영상 경로
            practice_poses: 연습 영상의 포즈 리스트 (미리 추출됨)
            reference_poses: 기준 영상의 포즈 리스트
            aligned_pairs: DTW 정렬된 (기준 프레임, 연습 프레임) 쌍
            frame_errors: {연습 프레임 인덱스: {오류 관절 ID 집합}}
            output_name: 출력 파일명 (None이면 자동 생성)
            
        Returns:
            str: 출력 영상 경로
        """
        cap = cv2.VideoCapture(practice_video_path)
        if not cap.isOpened():
            raise ValueError(f"영상을 열 수 없습니다: {practice_video_path}")
        
        # 영상 정보
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 출력 파일명 생성
        if output_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"analysis_{timestamp}"
        
        output_path = self.output_dir / f"{output_name}.mp4"
        
        # VideoWriter 설정
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        
        # 정렬 쌍을 연습 프레임 기준으로 딕셔너리 변환
        practice_to_reference = {}
        for ref_idx, prac_idx in aligned_pairs:
            if prac_idx not in practice_to_reference:
                practice_to_reference[prac_idx] = ref_idx
        
        # 연습 포즈를 프레임 번호로 인덱싱
        practice_pose_map = {pose.frame_number: pose for pose in practice_poses}
        
        print(f"[영상 렌더링 시작] {practice_video_path}")
        frame_idx = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 미리 추출된 포즈 사용
            current_pose = practice_pose_map.get(frame_idx)
            
            if current_pose is not None:
                # 오류 관절 확인
                error_joints = frame_errors.get(frame_idx, set())
                
                # 포즈 그리기
                self._draw_pose(frame, current_pose, error_joints, width, height)
                
                # 기준 포즈도 반투명하게 그리기 (정렬된 경우)
                if frame_idx in practice_to_reference:
                    ref_idx = practice_to_reference[frame_idx]
                    if ref_idx < len(reference_poses):
                        ref_pose = reference_poses[ref_idx]
                        self._draw_reference_pose(frame, ref_pose, width, height)
                
                # 프레임 정보 표시
                self._draw_info(frame, frame_idx, len(error_joints))
            
            out.write(frame)
            frame_idx += 1
            
            if frame_idx % 100 == 0:
                print(f"  처리 중: {frame_idx} 프레임...")
        
        cap.release()
        out.release()
        
        print(f"[렌더링 완료] 저장됨: {output_path}")
        return str(output_path)
    
    def _draw_pose(self, frame: np.ndarray, pose: FramePose, 
                   error_joints: Set[int], width: int, height: int):
        """프레임에 포즈 그리기 (오류 관절은 빨간색)"""
        landmarks = pose.landmarks
        
        # 연결선 그리기
        for start_idx, end_idx in POSE_CONNECTIONS:
            # 분석 대상이 아닌 관절은 건너뛰기
            if start_idx not in ANALYSIS_JOINTS and end_idx not in ANALYSIS_JOINTS:
                if start_idx > 10:  # 얼굴 관절 제외
                    continue
            
            start_point = self._landmark_to_pixel(landmarks[start_idx], width, height)
            end_point = self._landmark_to_pixel(landmarks[end_idx], width, height)
            
            # 연결된 관절 중 하나라도 오류면 빨간색
            if start_idx in error_joints or end_idx in error_joints:
                color = self.error_color
                thickness = self.line_thickness + 1
            else:
                color = self.normal_color
                thickness = self.line_thickness
            
            cv2.line(frame, start_point, end_point, color, thickness)
        
        # 관절점 그리기
        for joint_id in ANALYSIS_JOINTS:
            point = self._landmark_to_pixel(landmarks[joint_id], width, height)
            
            if joint_id in error_joints:
                color = self.error_color
                radius = self.circle_radius + 2
                # 오류 관절에 강조 효과
                cv2.circle(frame, point, radius + 3, (0, 0, 150), 2)
            else:
                color = self.normal_color
                radius = self.circle_radius
            
            cv2.circle(frame, point, radius, color, -1)
    
    def _draw_reference_pose(self, frame: np.ndarray, pose: FramePose,
                              width: int, height: int):
        """기준 포즈를 반투명하게 그리기"""
        landmarks = pose.landmarks
        
        # 연결선 그리기 (점선 효과)
        for start_idx, end_idx in POSE_CONNECTIONS:
            if start_idx not in ANALYSIS_JOINTS and end_idx not in ANALYSIS_JOINTS:
                if start_idx > 10:
                    continue
            
            start_point = self._landmark_to_pixel(landmarks[start_idx], width, height)
            end_point = self._landmark_to_pixel(landmarks[end_idx], width, height)
            
            cv2.line(frame, start_point, end_point, self.reference_color, 1)
    
    def _landmark_to_pixel(self, landmark: np.ndarray, 
                           width: int, height: int) -> Tuple[int, int]:
        """정규화된 랜드마크 좌표를 픽셀 좌표로 변환"""
        x = int(landmark[0] * width)
        y = int(landmark[1] * height)
        return (x, y)
    
    def _draw_info(self, frame: np.ndarray, frame_idx: int, error_count: int):
        """프레임 정보 텍스트 표시"""
        # 배경 박스
        cv2.rectangle(frame, (10, 10), (250, 70), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (250, 70), (255, 255, 255), 1)
        
        # 프레임 번호
        cv2.putText(frame, f"Frame: {frame_idx}", (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # 오류 관절 수
        if error_count > 0:
            color = (0, 0, 255)  # 빨간색
            text = f"Errors: {error_count} joints"
        else:
            color = (0, 255, 0)  # 초록색
            text = "OK"
        
        cv2.putText(frame, text, (20, 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)


def create_analysis_video(reference_video: str,
                          practice_video: str,
                          analysis_result,
                          output_name: str = None) -> str:
    """
    Reference와 Practice를 나란히 비교하는 영상 생성
    
    - 왼쪽: Reference 영상 + 포즈 (초록색)
    - 오른쪽: Practice 영상 + 포즈 (정상: 초록색, 오류: 빨간색)
    - 중앙 하단: 일치도 점수 표시
    
    Args:
        reference_video: 기준 영상 경로
        practice_video: 연습 영상 경로
        analysis_result: AnalysisResult 객체
        output_name: 출력 파일명
        
    Returns:
        str: 출력 영상 경로
    """
    from pose_extractor import PoseExtractor
    from pathlib import Path
    from datetime import datetime
    
    extractor = PoseExtractor()
    
    # 포즈 추출
    print("\n[비교 영상 생성] 기준 영상 포즈 추출 중...")
    reference_poses = extractor.extract_from_video(reference_video)
    print("[비교 영상 생성] 연습 영상 포즈 추출 중...")
    practice_poses = extractor.extract_from_video(practice_video)
    
    # 프레임별 오류 관절 맵 생성
    frame_errors: Dict[int, Set[int]] = {}
    frame_similarities: Dict[int, float] = {}  # 프레임별 평균 유사도
    
    if hasattr(analysis_result, 'frame_details'):
        for detail in analysis_result.frame_details:
            prac_frame = detail.get('practice_frame', -1)
            if prac_frame >= 0:
                error_joints = set()
                sims = list(detail.get('joint_similarities', {}).values())
                
                for joint_name, similarity in detail.get('joint_similarities', {}).items():
                    if similarity < 0.7:
                        try:
                            joint_id = LANDMARK_NAMES.index(joint_name)
                            error_joints.add(joint_id)
                        except ValueError:
                            pass
                
                if error_joints:
                    frame_errors[prac_frame] = error_joints
                if sims:
                    frame_similarities[prac_frame] = np.mean(sims) * 100
    
    # 영상 열기
    ref_cap = cv2.VideoCapture(reference_video)
    prac_cap = cv2.VideoCapture(practice_video)
    
    if not ref_cap.isOpened() or not prac_cap.isOpened():
        raise ValueError("영상을 열 수 없습니다")
    
    # 영상 정보
    fps = int(prac_cap.get(cv2.CAP_PROP_FPS))
    ref_w = int(ref_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    ref_h = int(ref_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    prac_w = int(prac_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    prac_h = int(prac_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # 출력 크기 (양쪽 영상을 나란히)
    target_h = max(ref_h, prac_h)
    target_w = max(ref_w, prac_w)
    output_w = target_w * 2  # 나란히 배치
    output_h = target_h
    
    # 출력 파일
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    if output_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"comparison_{timestamp}"
    
    output_path = output_dir / f"{output_name}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (output_w, output_h))
    
    # 포즈 맵 생성
    ref_pose_map = {p.frame_number: p for p in reference_poses}
    prac_pose_map = {p.frame_number: p for p in practice_poses}
    
    print("[비교 영상 렌더링 시작]")
    frame_idx = 0
    overall_score = analysis_result.overall_score if hasattr(analysis_result, 'overall_score') else 0
    
    while True:
        ret1, ref_frame = ref_cap.read()
        ret2, prac_frame = prac_cap.read()
        
        if not ret1 or not ret2:
            break
        
        # 크기 맞추기
        ref_frame = cv2.resize(ref_frame, (target_w, target_h))
        prac_frame = cv2.resize(prac_frame, (target_w, target_h))
        
        # Reference 포즈 그리기 (항상 초록색)
        ref_pose = ref_pose_map.get(frame_idx)
        if ref_pose is not None:
            _draw_pose_on_frame(ref_frame, ref_pose, set(), target_w, target_h, 
                               (0, 255, 0), (0, 255, 0))  # 초록색
        
        # Practice 포즈 그리기 (오류는 빨간색)
        prac_pose = prac_pose_map.get(frame_idx)
        error_joints = frame_errors.get(frame_idx, set())
        if prac_pose is not None:
            _draw_pose_on_frame(prac_frame, prac_pose, error_joints, target_w, target_h,
                               (0, 255, 0), (0, 0, 255))  # 초록/빨강
        
        # 라벨 추가
        cv2.rectangle(ref_frame, (10, 10), (180, 50), (0, 0, 0), -1)
        cv2.putText(ref_frame, "REFERENCE", (20, 38), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        cv2.rectangle(prac_frame, (10, 10), (180, 50), (0, 0, 0), -1)
        cv2.putText(prac_frame, "PRACTICE", (20, 38), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # 나란히 합치기
        combined = np.hstack([ref_frame, prac_frame])
        
        # 중앙 구분선
        cv2.line(combined, (target_w, 0), (target_w, target_h), (255, 255, 255), 3)
        
        # 하단 정보 표시
        info_y = target_h - 20
        frame_sim = frame_similarities.get(frame_idx, overall_score)
        
        # 점수에 따른 색상
        if frame_sim >= 80:
            score_color = (0, 255, 0)  # 초록
        elif frame_sim >= 60:
            score_color = (0, 255, 255)  # 노랑
        else:
            score_color = (0, 0, 255)  # 빨강
        
        # 정보 박스
        cv2.rectangle(combined, (target_w - 150, target_h - 60), 
                      (target_w + 150, target_h - 5), (0, 0, 0), -1)
        cv2.putText(combined, f"Frame: {frame_idx}", (target_w - 130, target_h - 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(combined, f"Score: {frame_sim:.1f}%", (target_w - 130, target_h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, score_color, 2)
        
        # 오류 관절 수 표시
        if error_joints:
            cv2.putText(combined, f"Errors: {len(error_joints)}", (target_w + 20, target_h - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        out.write(combined)
        frame_idx += 1
        
        if frame_idx % 100 == 0:
            print(f"  처리 중: {frame_idx} 프레임...")
    
    ref_cap.release()
    prac_cap.release()
    out.release()
    
    print(f"[비교 영상 완료] 저장됨: {output_path}")
    return str(output_path)


def _draw_pose_on_frame(frame: np.ndarray, pose: FramePose, error_joints: Set[int],
                        width: int, height: int, normal_color: Tuple, error_color: Tuple):
    """프레임에 포즈 그리기"""
    landmarks = pose.landmarks
    
    # 연결선 그리기
    for start_idx, end_idx in POSE_CONNECTIONS:
        if start_idx not in ANALYSIS_JOINTS and end_idx not in ANALYSIS_JOINTS:
            if start_idx > 10:
                continue
        
        start = (int(landmarks[start_idx][0] * width), int(landmarks[start_idx][1] * height))
        end = (int(landmarks[end_idx][0] * width), int(landmarks[end_idx][1] * height))
        
        if start_idx in error_joints or end_idx in error_joints:
            color = error_color
            thickness = 3
        else:
            color = normal_color
            thickness = 2
        
        cv2.line(frame, start, end, color, thickness)
    
    # 관절점 그리기
    for joint_id in ANALYSIS_JOINTS:
        point = (int(landmarks[joint_id][0] * width), int(landmarks[joint_id][1] * height))
        
        if joint_id in error_joints:
            cv2.circle(frame, point, 8, error_color, -1)
            cv2.circle(frame, point, 11, (255, 255, 255), 2)  # 흰색 테두리
        else:
            cv2.circle(frame, point, 5, normal_color, -1)


if __name__ == "__main__":
    print("VideoRenderer 모듈")
    print("사용법: create_analysis_video(reference_path, practice_path, analysis_result)")

