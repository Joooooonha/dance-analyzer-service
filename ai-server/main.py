"""
Dance Analyzer FastAPI Server (Hybrid Mode)
- 분석 + 결과물(영상/이미지) 생성
- Spring 서버에 URL 형태로 결과 반환
- 클라이언트가 직접 파일 다운로드 가능
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import os
import shutil
from pathlib import Path
from datetime import datetime
import uuid

from analyzer import DanceAnalyzer
from pose_extractor import PoseExtractor
from result_writer import save_result, list_results, load_result, get_output_dir
from report_generator import generate_analysis_report
from video_renderer import create_analysis_video

app = FastAPI(
    title="Dance Analyzer API",
    description="정면 시점 춤 영상 비교 분석 서비스 (Hybrid Mode)",
    version="2.1.0"
)

# CORS 설정 (Spring 서버에서 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 디렉토리 설정
OUTPUT_DIR = get_output_dir()
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 정적 파일 서빙 (이미지, 영상 접근용)
app.mount("/files/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
app.mount("/files/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# =====================================================
# Request/Response DTOs
# =====================================================

class AnalyzeRequest(BaseModel):
    """분석 요청 DTO"""
    reference_video_path: str = Field(..., description="기준 영상 파일 경로 (서버 내 경로 또는 업로드된 파일명)")
    practice_video_path: str = Field(..., description="연습 영상 파일 경로")
    similarity_threshold: Optional[float] = Field(default=0.7, ge=0.0, le=1.0)
    generate_video: Optional[bool] = Field(default=True)
    top_error_frames: Optional[int] = Field(default=10, ge=1, le=50)


class JointErrorInfo(BaseModel):
    """관절 오류 정보"""
    joint_name: str
    joint_id: int
    average_similarity: float
    severity: str


class FrameFeedbackInfo(BaseModel):
    """프레임별 피드백 정보 (URL 포함)"""
    frame_number: int
    timestamp_sec: float
    error_joints: List[str]
    average_similarity: float
    comparison_image_url: str  # URL로 변경


class AnalysisResult(BaseModel):
    """분석 결과 응답 DTO (URL 기반)"""
    status: str
    overall_score: float
    total_frames: int
    
    # 상위 오류 정보
    top_error_joints: List[JointErrorInfo]
    top_error_frames: List[FrameFeedbackInfo]
    
    # 결과물 URL
    comparison_video_url: Optional[str] = None  # 비교 영상 URL
    json_result_url: Optional[str] = None       # JSON 결과 URL
    
    message: str


class UploadResponse(BaseModel):
    """파일 업로드 응답"""
    filename: str
    file_path: str
    file_url: str


# =====================================================
# Helper Functions
# =====================================================

def get_base_url(request: Request) -> str:
    """요청에서 베이스 URL 추출"""
    return f"{request.url.scheme}://{request.url.netloc}"


def path_to_url(file_path: str, request: Request) -> str:
    """파일 경로를 URL로 변환"""
    base_url = get_base_url(request)
    path = Path(file_path)
    
    # output 폴더 내 파일
    if "output" in str(path):
        relative = path.relative_to(OUTPUT_DIR.parent) if OUTPUT_DIR.parent in path.parents else path.name
        if "images" in str(path):
            return f"{base_url}/files/output/images/{path.name}"
        return f"{base_url}/files/output/{path.name}"
    
    # uploads 폴더 내 파일
    if "uploads" in str(path):
        return f"{base_url}/files/uploads/{path.name}"
    
    return f"{base_url}/files/output/{Path(file_path).name}"


# =====================================================
# API Endpoints
# =====================================================

@app.get("/")
def root():
    """헬스 체크"""
    return {
        "service": "Dance Analyzer",
        "status": "running",
        "version": "2.1.0",
        "mode": "hybrid"
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_video(request: Request, file: UploadFile = File(...)):
    """
    영상 파일 업로드
    
    Spring 서버에서 영상을 업로드하면 저장 경로와 URL을 반환합니다.
    이후 /analyze 호출 시 이 경로를 사용하세요.
    """
    # 고유 파일명 생성
    ext = Path(file.filename).suffix
    unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = UPLOAD_DIR / unique_name
    
    # 파일 저장
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return UploadResponse(
        filename=unique_name,
        file_path=str(file_path),
        file_url=f"{get_base_url(request)}/files/uploads/{unique_name}"
    )


@app.post("/analyze", response_model=AnalysisResult)
async def analyze_dance(request: Request, body: AnalyzeRequest):
    """
    춤 동작 비교 분석 API
    
    기준 영상과 연습 영상을 비교 분석하여:
    - 전체 일치도 점수
    - 상위 오류 관절 정보
    - 상위 오류 프레임별 비교 이미지 URL
    - 나란히 비교 영상 URL
    
    을 반환합니다.
    
    Spring 서버에서 이 URL들을 클라이언트에 전달하면,
    클라이언트가 직접 이 서버에서 파일을 다운로드합니다.
    """
    reference_path = body.reference_video_path
    practice_path = body.practice_video_path
    
    # 업로드된 파일명만 전달된 경우 경로 변환
    if not os.path.isabs(reference_path) and not reference_path.startswith("input"):
        reference_path = str(UPLOAD_DIR / reference_path)
    if not os.path.isabs(practice_path) and not practice_path.startswith("input"):
        practice_path = str(UPLOAD_DIR / practice_path)
    
    # 파일 존재 확인
    if not os.path.exists(reference_path):
        raise HTTPException(status_code=404, detail=f"기준 영상을 찾을 수 없습니다: {reference_path}")
    if not os.path.exists(practice_path):
        raise HTTPException(status_code=404, detail=f"연습 영상을 찾을 수 없습니다: {practice_path}")
    
    try:
        print(f"\n[API 요청] 분석 시작")
        print(f"기준 영상: {reference_path}")
        print(f"연습 영상: {practice_path}")
        
        # 1. 포즈 추출
        extractor = PoseExtractor()
        print("\n[1단계] 기준 영상 포즈 추출 중...")
        reference_poses = extractor.extract_from_video(reference_path)
        print("[2단계] 연습 영상 포즈 추출 중...")
        practice_poses = extractor.extract_from_video(practice_path)
        
        # 2. 분석 수행
        print("\n[3단계] 동작 분석 중...")
        analyzer = DanceAnalyzer(
            similarity_threshold=body.similarity_threshold,
            include_frame_details=True
        )
        result = analyzer.analyze(reference_path, practice_path)
        
        # 3. 보고서 생성 (상위 N개 오류 프레임 + 비교 이미지)
        print(f"\n[4단계] 보고서 생성 중 (상위 {body.top_error_frames}개 프레임)...")
        report = generate_analysis_report(
            reference_path, practice_path,
            reference_poses, practice_poses,
            result, top_n=body.top_error_frames
        )
        
        # 4. 비교 영상 생성 (옵션)
        video_url = None
        if body.generate_video:
            print("\n[5단계] 비교 영상 생성 중...")
            video_path = create_analysis_video(reference_path, practice_path, result)
            video_url = path_to_url(video_path, request)
        
        # 5. JSON 결과 저장
        json_path = save_result(report.to_dict(), "analysis_report")
        json_url = path_to_url(json_path, request)
        
        print(f"\n[분석 완료] 전체 일치도: {result.overall_score:.2f}%")
        
        # 응답 구성 (URL 기반)
        return AnalysisResult(
            status="success",
            overall_score=round(result.overall_score, 2),
            total_frames=result.total_frames_practice,
            top_error_joints=[
                JointErrorInfo(
                    joint_name=j["joint_name"],
                    joint_id=j["joint_id"],
                    average_similarity=j["average_similarity"],
                    severity=j["severity"]
                ) for j in report.top_error_joints
            ],
            top_error_frames=[
                FrameFeedbackInfo(
                    frame_number=f.frame_number,
                    timestamp_sec=round(f.timestamp_ms / 1000, 2),
                    error_joints=f.error_joints,
                    average_similarity=round(f.avg_similarity, 2),
                    comparison_image_url=path_to_url(f.comparison_image_path, request)
                ) for f in report.top_error_frames
            ],
            comparison_video_url=video_url,
            json_result_url=json_url,
            message=f"분석 완료 - 전체 일치도: {result.overall_score:.2f}%"
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"분석 중 오류 발생: {str(e)}")


@app.get("/results")
def get_results(request: Request, limit: int = 10):
    """최근 분석 결과 목록 조회 (URL 포함)"""
    results = list_results()[:limit]
    base_url = get_base_url(request)
    
    return {
        "count": len(results),
        "results": [
            {
                "filename": Path(r).name,
                "url": f"{base_url}/files/output/{Path(r).name}"
            } for r in results
        ]
    }


@app.get("/results/{filename}")
def get_result_detail(filename: str):
    """특정 분석 결과 상세 조회"""
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"결과 파일을 찾을 수 없습니다: {filename}")
    return load_result(str(filepath))


if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("  Dance Analyzer API Server v2.1 (Hybrid Mode)")
    print("="*60)
    print(f"  서버 시작: http://localhost:8000")
    print(f"  API 문서: http://localhost:8000/docs")
    print(f"  출력 폴더: {OUTPUT_DIR}")
    print(f"  업로드 폴더: {UPLOAD_DIR}")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8000)