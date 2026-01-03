"""
결과 저장 모듈 (Result Writer)
분석 결과를 JSON 형식으로 output 폴더에 저장
"""

import os
import json
from datetime import datetime
from typing import Union
from pathlib import Path


def get_output_dir() -> Path:
    """output 디렉토리 경로 반환 (없으면 생성)"""
    # 현재 스크립트 위치 기준
    base_dir = Path(__file__).parent
    output_dir = base_dir / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


def save_result(result, prefix: str = "result", output_dir: Path = None) -> str:
    """
    분석 결과를 JSON 파일로 저장
    
    Args:
        result: AnalysisResult 객체 또는 dict
        prefix: 파일명 접두사
        output_dir: 저장 디렉토리 (None이면 기본 output 폴더)
        
    Returns:
        str: 저장된 파일 경로
    """
    if output_dir is None:
        output_dir = get_output_dir()
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
    
    # 타임스탬프 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.json"
    filepath = output_dir / filename
    
    # dict로 변환
    if hasattr(result, 'to_dict'):
        data = result.to_dict()
    elif isinstance(result, dict):
        data = result
    else:
        raise ValueError("result는 to_dict() 메서드가 있거나 dict여야 합니다.")
    
    # JSON 저장
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"[결과 저장] {filepath}")
    return str(filepath)


def load_result(filepath: str) -> dict:
    """
    JSON 결과 파일 로드
    
    Args:
        filepath: JSON 파일 경로
        
    Returns:
        dict: 분석 결과 데이터
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def list_results(output_dir: Path = None) -> list:
    """
    output 폴더의 결과 파일 목록 반환
    
    Args:
        output_dir: 결과 디렉토리 경로
        
    Returns:
        list: 결과 파일 경로 리스트 (최신순)
    """
    if output_dir is None:
        output_dir = get_output_dir()
    
    results = list(output_dir.glob("*.json"))
    results.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return [str(r) for r in results]


if __name__ == "__main__":
    # 테스트
    test_result = {
        "overall_score": 85.5,
        "analysis_details": {
            "total_frames_reference": 300,
            "total_frames_practice": 310,
            "aligned_frames": 300
        },
        "joint_errors": [
            {
                "joint_name": "LEFT_ELBOW",
                "joint_id": 13,
                "average_similarity": 0.62,
                "error_frames": [45, 46, 47],
                "error_severity": "high"
            }
        ],
        "timestamp": datetime.now().isoformat()
    }
    
    saved_path = save_result(test_result, "test")
    print(f"테스트 결과 저장: {saved_path}")
    
    loaded = load_result(saved_path)
    print(f"로드된 데이터: {json.dumps(loaded, indent=2, ensure_ascii=False)}")
