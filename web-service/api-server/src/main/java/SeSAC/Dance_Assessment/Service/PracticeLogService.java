package SeSAC.Dance_Assessment.Service;

import SeSAC.Dance_Assessment.Domain.AnalysisResult;
import SeSAC.Dance_Assessment.Domain.AnalysisStatus;
import SeSAC.Dance_Assessment.Domain.PracticeLog;
import SeSAC.Dance_Assessment.Dto.Ai.AiAnalysisResponse;
import SeSAC.Dance_Assessment.Dto.PracticeLog.PracticeLogDetailResponse;
import SeSAC.Dance_Assessment.Dto.PracticeLog.PracticeLogListResponse;
import SeSAC.Dance_Assessment.Infrastructure.AnalysisResultRepository;
import SeSAC.Dance_Assessment.Infrastructure.PracticeLogRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true) // 조회 전용
public class PracticeLogService {

    private final PracticeLogRepository practiceLogRepository;
    private final AnalysisResultRepository analysisResultRepository;
    private final AiClientService aiClientService;

    public Page<PracticeLogListResponse> getMyPracticeLogs(Long userId, Pageable pageable) {
        Page<PracticeLog> logPage = practiceLogRepository.findByUserId(userId, pageable);

        // 엔티티 목록 DTO 목록으로 변환
        return logPage.map(PracticeLogListResponse::from);
    }

    /**
     * [NEW] 연습 기록 상세 조회
     * - 분석 결과(점수, 피드백)를 포함한 상세 정보 반환
     */
    public PracticeLogDetailResponse getPracticeLogDetail(Long logId, Long userId) {
        PracticeLog practiceLog = practiceLogRepository.findById(logId)
                .orElseThrow(() -> new IllegalArgumentException("기록 없음"));

        // 권한 체크 (본인의 기록만 조회 가능)
        if (!practiceLog.getUser().getId().equals(userId)) {
            throw new IllegalStateException("권한 없음");
        }

        return PracticeLogDetailResponse.from(practiceLog);
    }

    /**
     * 연습 기록 분석 요청
     * 
     * 분석 흐름:
     * 1. 기준 영상 경로 (PracticeLog.referenceVideo에서 가져옴)
     * 2. 연습 영상 경로 (PracticeLog.practiceVideo에서 가져옴)
     * 3. AI 서버에 분석 요청 (두 경로 전달)
     * 
     * ⚠️ referenceVideo가 없으면 분석 불가
     */
    @Transactional
    public AiAnalysisResponse analyzePracticeLog(Long logId, Long userId) {
        // 연습 기록 조회
        PracticeLog practiceLog = practiceLogRepository.findById(logId)
                .orElseThrow(() -> new IllegalArgumentException("기록 없음"));

        // 권한 체크
        if (!practiceLog.getUser().getId().equals(userId)) {
            throw new IllegalStateException("권한 없음");
        }

        // ===== 기준 영상 체크 =====
        // referenceVideo가 없으면 분석 불가
        if (practiceLog.getReferenceVideo() == null) {
            throw new IllegalStateException("기준 영상이 없어 분석할 수 없습니다. 기준 영상을 먼저 업로드해주세요.");
        }

        // 기준 영상 경로 (PracticeLog에 연결된 기준 영상)
        String referenceVideoPath = practiceLog.getReferenceVideo().getVideoPath();
        // 연습 영상 경로
        String practiceVideoPath = practiceLog.getPracticeVideo().getVideoPath();

        // AI 서버에 분석 요청
        AiAnalysisResponse response = aiClientService.requestAnalysis(
                referenceVideoPath,
                practiceVideoPath);

        // 이미 결과가 있으면 업데이트, 없으면 생성
        AnalysisResult result = analysisResultRepository.findByPracticeLogId(logId)
                .orElse(AnalysisResult.builder()
                        .practiceLog(practiceLog)
                        .status(AnalysisStatus.COMPLETED)
                        .build());

        // [MODIFIED] 상세 결과 저장 (오류 관절/프레임은 JSON 직렬화)
        String topErrorJointsJson = toJson(response.getTopErrorJoints());
        String topErrorFramesJson = toJson(response.getTopErrorFrames());

        result.updateDetailedResult(
                response.getOverallScore().intValue(),
                response.getMessage(),
                response.getComparisonVideoUrl(),
                response.getJsonResultUrl(),
                topErrorJointsJson,
                topErrorFramesJson);

        // 생성 이력이 없는 경우 저장
        if (result.getId() == null) {
            analysisResultRepository.save(result);
        }

        return response;
    }

    /**
     * [NEW] 객체를 JSON 문자열로 변환
     */
    private String toJson(Object obj) {
        if (obj == null)
            return null;
        try {
            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            return mapper.writeValueAsString(obj);
        } catch (Exception e) {
            return null;
        }
    }
}