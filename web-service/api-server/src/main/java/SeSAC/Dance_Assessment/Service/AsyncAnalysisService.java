package SeSAC.Dance_Assessment.Service;

import SeSAC.Dance_Assessment.Domain.AnalysisResult;
import SeSAC.Dance_Assessment.Domain.AnalysisStatus;
import SeSAC.Dance_Assessment.Domain.PracticeLog;
import SeSAC.Dance_Assessment.Dto.Ai.AiAnalysisResponse;
import SeSAC.Dance_Assessment.Infrastructure.AnalysisResultRepository;
import SeSAC.Dance_Assessment.Infrastructure.PracticeLogRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * [NEW] 비동기 AI 분석 서비스
 * - 영상 업로드 완료 후 백그라운드에서 분석 실행
 * - 사용자는 분석 완료를 기다리지 않고 다른 작업 가능
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AsyncAnalysisService {

    private final PracticeLogRepository practiceLogRepository;
    private final AnalysisResultRepository analysisResultRepository;
    private final AiClientService aiClientService;

    /**
     * 비동기 분석 실행
     * - 별도 스레드에서 실행되어 호출자를 블로킹하지 않음
     */
    @Async
    @Transactional
    public void analyzeAsync(Long practiceLogId) {
        log.info("[비동기 분석 시작] PracticeLog ID: {}", practiceLogId);

        try {
            // PracticeLog 조회
            PracticeLog practiceLog = practiceLogRepository.findById(practiceLogId)
                    .orElseThrow(() -> new IllegalArgumentException("기록 없음: " + practiceLogId));

            // 기준 영상 체크
            if (practiceLog.getReferenceVideo() == null) {
                log.warn("[비동기 분석 스킵] 기준 영상 없음: {}", practiceLogId);
                return;
            }

            // 분석 상태를 PROCESSING으로 변경
            AnalysisResult result = analysisResultRepository.findByPracticeLogId(practiceLogId)
                    .orElse(AnalysisResult.builder()
                            .practiceLog(practiceLog)
                            .status(AnalysisStatus.PROCESSING)
                            .build());

            if (result.getId() == null) {
                analysisResultRepository.save(result);
            }

            // 영상 경로
            String referenceVideoPath = practiceLog.getReferenceVideo().getVideoPath();
            String practiceVideoPath = practiceLog.getPracticeVideo().getVideoPath();

            log.info("[비동기 분석] AI 서버 요청 - 기준: {}, 연습: {}", referenceVideoPath, practiceVideoPath);

            // AI 서버에 분석 요청
            AiAnalysisResponse response = aiClientService.requestAnalysis(
                    referenceVideoPath,
                    practiceVideoPath);

            // 상세 결과 저장
            String topErrorJointsJson = toJson(response.getTopErrorJoints());
            String topErrorFramesJson = toJson(response.getTopErrorFrames());

            result.updateDetailedResult(
                    response.getOverallScore().intValue(),
                    response.getMessage(),
                    response.getComparisonVideoUrl(),
                    response.getJsonResultUrl(),
                    topErrorJointsJson,
                    topErrorFramesJson);

            log.info("[비동기 분석 완료] PracticeLog ID: {}, 점수: {}", practiceLogId, response.getOverallScore());

        } catch (Exception e) {
            log.error("[비동기 분석 실패] PracticeLog ID: {}, 에러: {}", practiceLogId, e.getMessage(), e);

            // 실패 상태 저장
            try {
                AnalysisResult result = analysisResultRepository.findByPracticeLogId(practiceLogId).orElse(null);
                if (result != null) {
                    result.updateResult(0, "분석 실패: " + e.getMessage());
                }
            } catch (Exception saveError) {
                log.error("[분석 실패 상태 저장 실패]", saveError);
            }
        }
    }

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
