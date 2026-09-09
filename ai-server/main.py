"""
Dance Analyzer FastAPI Server
- 기준 영상 vs 연습 영상 비교 → 구간 단위 피드백
- Spring 서버에 URL 형태로 결과 반환
- 클라이언트가 직접 파일 다운로드 가능

v3.0에서 분석 경로를 `engine/`(model-research에서 검증한 구현)으로 교체했다.
바뀐 것과 그 이유는 `engine/analyze.py` 상단 표와 `TASKS-SERVICE.md` 참조.

**응답에서 `overall_score`가 빠졌다.** 점수 환산 상수(45도=0점)가 임의값이라
절대값에 의미가 없었기 때문이다. 대신 "틀린 동작 구간 개수"와 구간 목록을 준다.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
import tempfile
import shutil
import threading
import time
from datetime import datetime

from engine.analyze import analyze
from visualize import render_issue_images, render_comparison_video
import remote_io

app = FastAPI(
    title="Dance Analyzer API",
    description="정면 시점 춤 영상 비교 분석 서비스",
    version="3.0.0"
)

# CORS 설정 (Spring 서버에서 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 로컬 저장소도, 정적 파일 서빙도 없다.
#
# 예전에는 `/files/output`과 `/files/uploads`를 정적으로 열어두고 결과물을
# 직접 서빙했다. 그 경로에는 **인증이 없어서** 이 서버가 외부에 노출되는 순간
# 모든 사용자의 분석 결과물이 공개된다. `/upload`도 아무나 100MB 파일을 저장할
# 수 있는 구멍이었다.
#
# 지금은 영상을 서명된 URL로 받아 임시 파일에 쓰고, 결과물도 서명된 URL로
# 올린 뒤 임시 파일을 지운다. 이 서버는 아무것도 보관하지 않는다.

# 관절 검출이 이 비율을 넘게 실패하면 "다시 촬영" 안내를 붙인다.
# **잠정값이다.** 검출 실패율과 사용자 체감 품질의 관계를 아직 측정하지 않았다.
# 정렬 신뢰도는 여기에 넣지 않는다 — 신뢰도 신호 5종이 정렬 오차를 예측하지
# 못한다는 것이 이미 측정됐다(상관 0.03~0.26). 없는 능력을 있는 척하지 않는다.
UNUSABLE_FRAME_PCT_WARN = 30.0

# 동시에 돌릴 분석 수.
#
# 분석 한 건이 이 기계의 CPU를 1분 넘게 붙잡는다(영상마다 별도 프로세스를 띄우고
# MediaPipe가 여러 코어를 쓴다). 두 건을 동시에 돌리면 서로 코어를 나눠 갖다가
# 둘 다 느려지고, 결국 어느 쪽도 제때 끝나지 않는다.
#
# Spring 쪽에도 동시 1건 제한이 있지만 여기서 또 막는다 — 같은 Tailscale 망의
# 다른 경로로 요청이 들어오면 Spring의 제한은 아무 소용이 없다.
MAX_CONCURRENT_ANALYSES = 1

# 비블로킹으로 잡는다. 자리가 없으면 기다리지 않고 즉시 429로 돌려보낸다.
# 여기서 대기시키면 호출자가 응답을 못 받은 채로 묶여, 어디서 막혔는지
# 알 수 없게 된다. 재시도 판단은 호출자가 하는 편이 낫다.
_analysis_slots = threading.BoundedSemaphore(MAX_CONCURRENT_ANALYSES)


# =====================================================
# 진행 상황
# =====================================================
#
# 분석은 3분 가까이 걸리는데 그동안 밖으로 나가는 신호가 하나도 없었다.
# 사용자 입장에서는 멈춘 것과 구분되지 않아 "그냥 기다리게 된다".
#
# **진행률을 지어내지 않는다.** 단계 전환은 실제 코드 위치에서 일어나는 사건이고,
# 아래 가중치만 실측에서 얻은 추정이다. 단계 안에서의 세부 진행은 알 수 없으므로
# 그 구간의 시작·끝 퍼센트를 함께 내보내고, 그 사이를 어떻게 보여줄지는 화면에 맡긴다.
#
# 가중치 근거 — 맥미니 M1(CPU), 30초 영상 2개, 총 201초 실측:
#   다운로드 5초 / 기준 추출 89초 / 연습 추출 89초 / 정렬·피드백 5초 / 이미지 18초
# 영상이 길어지면 절대 시간은 늘지만 비율은 대체로 유지된다(추출이 지배적).
PROGRESS_STAGES = [
    ('download',          '영상 받는 중',           0.03),
    ('extract_reference', '기준 영상 분석 중',       0.43),
    ('extract_practice',  '내 영상 분석 중',         0.43),
    ('align',             '동작 맞추는 중',          0.03),
    ('render',            '비교 이미지 만드는 중',    0.08),
]


class _ProgressTracker:
    """지금 돌고 있는 분석 한 건의 단계를 들고 있는다.

    동시 분석이 1건으로 제한돼 있어(`MAX_CONCURRENT_ANALYSES`) 하나만 기억하면 된다.
    **`job_id`를 함께 돌려준다** — 호출자가 자기가 맡긴 작업의 진행인지 확인하지
    않으면 남의 분석 진행률을 자기 것으로 보여주게 된다.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._reset()

    def _reset(self):
        self.job_id = None
        self.state = 'idle'
        self.stage_name = None
        self.started_at = None
        self.stage_started_at = None
        self.finished_at = None

    def start(self, job_id):
        with self._lock:
            now = time.monotonic()
            self.job_id = job_id
            self.state = 'running'
            self.stage_name = PROGRESS_STAGES[0][0]
            self.started_at = now
            self.stage_started_at = now
            self.finished_at = None

    def stage(self, name):
        with self._lock:
            if self.state != 'running':
                return
            self.stage_name = name
            self.stage_started_at = time.monotonic()

    def finish(self, state):
        """state: 'done' | 'failed'. 끝난 뒤에도 마지막 상태는 남겨둔다 —
        호출자가 완료를 진행률로도 확인할 수 있어야 한다."""
        with self._lock:
            if self.state == 'running':
                self.state = state
                self.stage_name = None
                # 끝난 시각을 박아둔다. 이걸 안 하면 분석이 끝난 뒤에도
                # elapsed_sec이 계속 늘어나 "아직 돌고 있는 것"처럼 보인다.
                self.finished_at = time.monotonic()

    def snapshot(self):
        with self._lock:
            if self.state == 'idle':
                return {'state': 'idle'}

            # 끝난 작업의 경과 시간은 끝난 시점에 멈춘다.
            now = self.finished_at or time.monotonic()
            pct = next_pct = 100.0
            label = None
            cum = 0.0
            for name, text, weight in PROGRESS_STAGES:
                if name == self.stage_name:
                    pct = round(cum * 100, 1)
                    next_pct = round((cum + weight) * 100, 1)
                    label = text
                    break
                cum += weight

            return {
                'state': self.state,
                'job_id': self.job_id,
                'stage': self.stage_name,
                'label': label,
                # 이 단계의 시작·끝 퍼센트. 단계 안에서의 세부 진행은 모른다.
                'pct': pct if self.state == 'running' else 100.0,
                'next_pct': next_pct if self.state == 'running' else 100.0,
                'stage_elapsed_sec': round(now - (self.stage_started_at or now), 1),
                'elapsed_sec': round(now - (self.started_at or now), 1),
            }


_progress = _ProgressTracker()


# =====================================================
# Request/Response DTOs
# =====================================================

class AnalyzeRequest(BaseModel):
    """분석 요청 DTO"""
    reference_video_url: str = Field(..., description="기준 영상 다운로드 URL (서명됨)")
    practice_video_url: str = Field(..., description="연습 영상 다운로드 URL (서명됨)")

    # 안무 구간 (선택). 시작점만 줘도 전역 오프셋이 제거되어 정렬이 크게 좋아진다.
    # 끝점의 추가 이득은 실측 4.7%p로 작아서, UI에서는 시작점을 우선 안내한다.
    reference_start_sec: Optional[float] = Field(default=None, ge=0.0, description="기준 영상에서 안무가 시작하는 시각(초)")
    reference_end_sec: Optional[float] = Field(default=None, ge=0.0, description="기준 영상에서 안무가 끝나는 시각(초)")
    practice_start_sec: Optional[float] = Field(default=None, ge=0.0, description="연습 영상에서 안무가 시작하는 시각(초)")
    practice_end_sec: Optional[float] = Field(default=None, ge=0.0, description="연습 영상에서 안무가 끝나는 시각(초)")

    # 진행률을 물어볼 때 "내가 맡긴 그 작업이 맞는지" 확인하는 표식.
    # 없으면 동시에 들어온 다른 분석의 진행률을 자기 것으로 착각할 수 있다.
    job_id: Optional[str] = Field(default=None, description="호출자가 붙이는 작업 식별자")

    top_issues: Optional[int] = Field(default=10, ge=1, le=50, description="반환할 상위 지적 구간 수")
    generate_images: Optional[bool] = Field(default=True, description="구간별 비교 이미지 생성")
    generate_video: Optional[bool] = Field(default=False, description="정렬된 나란히 비교 영상 생성 (느림)")

    # 결과물을 올릴 서명된 PUT URL들.
    # 이 서버는 저장소 자격증명을 갖지 않는다 — 요청마다 필요한 만큼의 짧은
    # URL만 받아서 쓴다. 맥미니가 뚫려도 얻을 것이 곧 만료될 URL뿐이다.
    image_upload_urls: Optional[List[str]] = Field(
        default=None, description="구간 순위별 이미지 업로드 URL")
    video_upload_url: Optional[str] = Field(
        default=None, description="비교 영상 업로드 URL")

    @model_validator(mode='after')
    def _check_ranges(self):
        for name, s, e in (('reference', self.reference_start_sec, self.reference_end_sec),
                           ('practice', self.practice_start_sec, self.practice_end_sec)):
            if s is not None and e is not None and e <= s:
                raise ValueError(f"{name}_end_sec는 {name}_start_sec보다 커야 합니다")
        return self


class IssueRepresentative(BaseModel):
    """구간을 대표하는 프레임 (오차가 가장 큰 지점). 비교 이미지의 근거."""
    practice_frame: int
    practice_sec: float
    reference_frame: int
    reference_sec: float
    frame_error_deg: float


class IssueInfo(BaseModel):
    """지적 구간 하나. 신체 그룹(왼팔/오른다리/상체) 단위로 병합된 결과."""
    rank: int
    group: str
    message: str
    start_sec: float
    end_sec: float
    duration_sec: float
    severity: float = Field(..., description="그 영상 자체의 부위별 분포 대비 배수 (1.0=중앙값)")
    mean_error_deg: float
    parts: List[str]
    representative: Optional[IssueRepresentative] = None

    # 이 구간의 비교 이미지를 어느 업로드 슬롯에 올렸는지.
    # URL이 아니라 슬롯 번호인 이유: 이 서버는 자기가 올린 객체의 **키를 모른다**
    # (서명된 URL만 받았다). 키를 아는 Spring이 슬롯 → 키로 되돌린다.
    image_slot: Optional[int] = None


class UnreliableSpan(BaseModel):
    """평가에서 제외한 구간."""
    start_sec: float
    end_sec: float
    n_frames: int


class AlignmentQuality(BaseModel):
    """
    측정 가능한 품질 지표만 담는다.

    **정렬이 맞았는지 여부는 여기 없다.** 그것을 추정하려고 신뢰도 신호 5종을
    시험했지만 전부 정렬 오차를 예측하지 못했다(상관 0.03~0.26). 정렬 실패는
    "불확실한 매칭"이 아니라 "확신에 찬 오답"으로 나타나기 때문이다.
    """
    scored_pct: float = Field(..., description="DTW 경로 중 실제 채점된 대응쌍 비율")
    mean_error_deg: Optional[float] = None
    median_error_deg: Optional[float] = None
    p90_error_deg: Optional[float] = None
    reference_unusable_frame_pct: float
    practice_unusable_frame_pct: float
    reference_joint_valid_ratio: float
    practice_joint_valid_ratio: float
    global_offset_sec: float
    warning: Optional[str] = None


class TrimEcho(BaseModel):
    """요청한 구간이 실제로 적용됐는지 확인용."""
    applied: bool = Field(..., description="양쪽 시작점이 모두 주어져 좁은 밴드를 적용했는지")
    reference_start_sec: Optional[float] = None
    reference_end_sec: Optional[float] = None
    practice_start_sec: Optional[float] = None
    practice_end_sec: Optional[float] = None
    note: Optional[str] = None


class AnalysisResult(BaseModel):
    """분석 결과 응답 DTO (URL 기반)"""
    status: str
    issue_count: int = Field(..., description="틀린 동작 구간 총 개수 (점수 아님)")
    top_issues: List[IssueInfo]
    unreliable_spans: List[UnreliableSpan]
    unreliable_note: Optional[str] = None
    quality: AlignmentQuality
    trim: TrimEcho

    comparison_video_uploaded: bool = False

    # 두 영상을 맞춰 재생하기 위한 대응표: [[연습 시각, 기준 시각], ...] (원본 영상 기준 초).
    #
    # **비교 영상을 렌더링하는 대신 이 표를 준다.** 렌더링은 분석 시간을 60~90초
    # 더 쓰고 브라우저가 재생 못 하는 코덱 문제까지 안고 있는데, 정작 사용자가
    # 하고 싶은 건 "이 구간만 느리게 반복해서 보기"다. 표를 주면 화면이 두 영상을
    # 직접 맞춰 돌릴 수 있어 되감기·반복·배속이 전부 공짜로 된다.
    sync_map: List[List[float]] = Field(
        default_factory=list, description="[[연습 시각, 기준 시각], ...] 초 단위")

    message: str


# =====================================================
# Helper Functions
# =====================================================

def build_quality(meta: dict, stats: dict) -> AlignmentQuality:
    ref_cov = meta.get('reference_coverage', {})
    prac_cov = meta.get('practice_coverage', {})

    warnings = []
    for name, cov in (("기준 영상", ref_cov), ("연습 영상", prac_cov)):
        pct = float(cov.get('ungated_pct', 0.0))
        if pct >= UNUSABLE_FRAME_PCT_WARN:
            warnings.append(
                f"{name}의 {pct:.0f}% 프레임에서 관절을 제대로 잡지 못했습니다")
    if stats.get('scored_pairs', 0) == 0:
        warnings.append("채점 가능한 대응 구간이 없습니다")

    return AlignmentQuality(
        scored_pct=round(float(stats.get('scored_pct', 0.0)), 1),
        mean_error_deg=(round(stats['mean_error'], 1) if 'mean_error' in stats else None),
        median_error_deg=(round(stats['median_error'], 1) if 'median_error' in stats else None),
        p90_error_deg=(round(stats['p90_error'], 1) if 'p90_error' in stats else None),
        reference_unusable_frame_pct=round(float(ref_cov.get('ungated_pct', 0.0)), 1),
        practice_unusable_frame_pct=round(float(prac_cov.get('ungated_pct', 0.0)), 1),
        reference_joint_valid_ratio=round(float(ref_cov.get('joint_valid_ratio', 0.0)), 3),
        practice_joint_valid_ratio=round(float(prac_cov.get('joint_valid_ratio', 0.0)), 3),
        global_offset_sec=round(float(stats.get('global_offset_sec', 0.0)), 3),
        warning=(" / ".join(warnings) + " — 전신이 밝은 곳에서 다 나오게 다시 촬영하면 결과가 좋아집니다"
                 if warnings else None),
    )


# =====================================================
# API Endpoints
# =====================================================

@app.get("/")
def root():
    """헬스 체크. 분석 중에도 즉시 응답해야 한다."""
    """헬스 체크"""
    return {
        "service": "Dance Analyzer",
        "status": "running",
        "version": "3.0.0",
        "engine": "angle-feature DTW (model-research 검증본)",
    }


@app.get("/progress")
def progress():
    """지금 돌고 있는 분석의 단계.

    **분석 중에도 즉시 응답해야 한다.** 락은 값을 읽는 동안만 잡고, 무거운 일은
    하지 않는다. 이 응답이 늦으면 진행률을 보여주려다 오히려 화면이 멈춘다.

    호출자는 `job_id`가 자기가 맡긴 값과 같은지 반드시 확인할 것.
    """
    return _progress.snapshot()


# **`async def`가 아니라 `def`다.** 이 함수의 본문은 처음부터 끝까지 블로킹이다
# (영상 다운로드, OpenCV, MediaPipe, 서브프로세스). `async def`로 두면 그 1분
# 남짓 동안 이벤트 루프가 통째로 멈춰서 헬스체크조차 응답하지 못한다 —
# 밖에서 보면 서버가 죽은 것과 구분되지 않는다.
# 평범한 `def`로 두면 FastAPI가 스레드풀에서 실행해 루프가 계속 돈다.
@app.post("/analyze", response_model=AnalysisResult)
def analyze_dance(body: AnalyzeRequest):
    """
    춤 동작 비교 분석 API.

    기준 영상과 연습 영상을 비교해 **틀린 동작 구간**을 돌려준다.

    - `*_video_url`: 저장소의 **서명된 다운로드 URL**. 이 서버는 저장소
      자격증명을 갖지 않고, 받은 URL로만 접근한다.
    - `image_upload_urls`: 결과 이미지를 올릴 슬롯. 쓴 슬롯 번호를 구간마다
      `image_slot`으로 돌려준다 — 이 서버는 객체 키를 모르기 때문이다.
    - `*_start_sec` / `*_end_sec`: 안무 구간. **양쪽 시작점을 주면** 정렬 정확도가
      크게 오른다(앵커 기준 ±5프레임 내 71.8% → 78.9%, 각속도 보조까지 더하면
      81.6%). 끝점은 선택이다.

    영상과 결과물은 전부 임시 파일로만 다루고 응답 직전에 지운다.
    이 서버는 아무것도 보관하지 않는다.
    """
    if not _analysis_slots.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail="다른 분석이 진행 중입니다. 잠시 후 다시 요청해주세요.",
            headers={"Retry-After": "60"},
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    workdir = tempfile.mkdtemp(prefix="analyze_")
    ref_path = prac_path = None
    _progress.start(body.job_id)

    try:
        print("\n[분석 요청] 영상 다운로드 중...")
        try:
            ref_path = remote_io.download_to_temp(body.reference_video_url, ".mp4")
            prac_path = remote_io.download_to_temp(body.practice_video_url, ".mp4")
        except remote_io.RemoteIOError as e:
            # 서명 만료·네트워크 문제는 서버 잘못이 아니므로 502로 구분해 알린다.
            raise HTTPException(status_code=502, detail=str(e))

        result = analyze(
            ref_path, prac_path,
            ref_start_sec=body.reference_start_sec,
            ref_end_sec=body.reference_end_sec,
            prac_start_sec=body.practice_start_sec,
            prac_end_sec=body.practice_end_sec,
            top_issues=body.top_issues,
            with_context=True,
            progress_cb=_progress.stage,
        )
        ctx = result.pop('_context')
        feedback = result['feedback']
        meta = result['meta']
        issues = feedback['top_issues']

        upload_urls = body.image_upload_urls or []
        image_slots = {}

        if body.generate_images and issues and upload_urls:
            _progress.stage('render')
            print(f"[이미지] 상위 {len(issues)}개 구간 렌더링...")
            rendered = render_issue_images(
                ref_path, prac_path,
                ctx['reference_sequence'], ctx['practice_sequence'],
                result['details'], issues, workdir, timestamp)

            for idx, img_path in rendered:
                if idx >= len(upload_urls):
                    # 발급받은 슬롯보다 구간이 많으면 남는 것은 버린다.
                    continue
                if remote_io.upload_file(upload_urls[idx], img_path, "image/jpeg"):
                    image_slots[idx] = idx

        video_uploaded = False
        if body.generate_video and body.video_upload_url:
            print("[영상] 정렬 비교 영상 렌더링...")
            video_path = render_comparison_video(
                ref_path, prac_path,
                ctx['reference_sequence'], ctx['practice_sequence'],
                ctx['path'], issues, workdir, timestamp)
            if video_path:
                video_uploaded = remote_io.upload_file(
                    body.video_upload_url, video_path, "video/mp4")

        quality = build_quality(meta, result.get('stats', {}))
        n = feedback['issue_count']
        _progress.finish('done')
        print(f"\n[분석 완료] 지적 구간 {n}개, 채점률 {quality.scored_pct}%")

        return AnalysisResult(
            status="success",
            issue_count=n,
            top_issues=[
                IssueInfo(
                    rank=i + 1,
                    group=g['group'],
                    message=g['message'],
                    start_sec=g['start_sec'],
                    end_sec=g['end_sec'],
                    duration_sec=g['duration_sec'],
                    severity=g['severity'],
                    mean_error_deg=g['mean_error_deg'],
                    parts=g['parts'],
                    representative=(IssueRepresentative(**g['representative'])
                                    if g.get('representative') else None),
                    image_slot=image_slots.get(i),
                ) for i, g in enumerate(issues)
            ],
            unreliable_spans=[UnreliableSpan(**u) for u in feedback['unreliable_spans']],
            unreliable_note=feedback.get('unreliable_note'),
            quality=quality,
            trim=TrimEcho(
                applied=meta['trimmed'],
                reference_start_sec=body.reference_start_sec,
                reference_end_sec=body.reference_end_sec,
                practice_start_sec=body.practice_start_sec,
                practice_end_sec=body.practice_end_sec,
                note=(None if meta['trimmed'] else
                      "양쪽 영상의 안무 시작 시각을 지정하면 정렬 정확도가 올라갑니다"),
            ),
            comparison_video_uploaded=video_uploaded,
            sync_map=result.get('sync_map', []),
            message=f"분석 완료 — 다듬을 구간 {n}개를 찾았습니다",
        )

    except HTTPException:
        _progress.finish('failed')
        raise
    except Exception as e:
        _progress.finish('failed')
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"분석 중 오류 발생: {str(e)}")

    finally:
        # 영상도 결과물도 남기지 않는다. 이 서버는 저장소가 아니다.
        remote_io.cleanup(ref_path, prac_path)
        shutil.rmtree(workdir, ignore_errors=True)
        _analysis_slots.release()


# `/results` 목록·상세 엔드포인트는 제거했다.
# 로컬 output 폴더를 읽어 결과 JSON을 돌려주는 것이었는데,
# (1) 이제 이 서버는 결과를 보관하지 않고,
# (2) 인증이 없어 외부에 노출되면 모든 사용자의 분석 결과가 공개된다.
# 결과 조회는 Spring이 권한을 확인한 뒤 담당한다.


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  Dance Analyzer API Server v3.0")
    print("=" * 60)
    print("  서버 시작: http://127.0.0.1:8000")
    print("  API 문서: http://127.0.0.1:8000/docs")
    print("  저장소: 없음 (영상·결과물은 서명 URL로만 주고받음)")
    print("=" * 60)
    # **127.0.0.1에만 바인딩한다.** 이 서버에는 인증이 없다 —
    # 접근 통제는 "네트워크에서 닿을 수 없다"는 것에 의존한다.
    # 배포 시에는 Tailscale 주소로만 열고 공인 IP에는 절대 노출하지 않는다.
    uvicorn.run(app, host="127.0.0.1", port=8000)
