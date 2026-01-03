package SeSAC.Dance_Assessment.Dto.PracticeLog;

import SeSAC.Dance_Assessment.Domain.AnalysisResult;
import SeSAC.Dance_Assessment.Domain.AnalysisStatus;
import SeSAC.Dance_Assessment.Domain.PracticeLog;

import java.time.LocalDateTime;

/**
 * [MODIFIED] 연습 기록 상세 조회용 응답 DTO
 * - 분석 결과(점수, 피드백)를 포함한 상세 정보
 * - 비교 영상 URL, 오류 관절/프레임 정보 추가
 */
public record PracticeLogDetailResponse(
        Long logId,
        Long userId,
        LocalDateTime createdAt,

        // 연습 영상 정보
        Long practiceVideoId,
        String practiceVideoPath,

        // 기준 영상 정보
        Long referenceVideoId,
        String referenceVideoPath,

        // 분석 결과
        AnalysisStatus status,
        Integer totalScore,
        String feedback,
        LocalDateTime analyzedAt,

        // [NEW] 상세 분석 결과
        String comparisonVideoUrl,
        String jsonResultUrl,
        String topErrorJointsJson,
        String topErrorFramesJson) {
    public static PracticeLogDetailResponse from(PracticeLog log) {
        AnalysisResult result = log.getAnalysisResult();

        return new PracticeLogDetailResponse(
                log.getId(),
                log.getUser() != null ? log.getUser().getId() : null,
                log.getCreatedAt(),

                log.getPracticeVideo() != null ? log.getPracticeVideo().getId() : null,
                log.getPracticeVideo() != null ? log.getPracticeVideo().getVideoPath() : null,

                log.getReferenceVideo() != null ? log.getReferenceVideo().getId() : null,
                log.getReferenceVideo() != null ? log.getReferenceVideo().getVideoPath() : null,

                result != null ? result.getStatus() : AnalysisStatus.WAITING,
                result != null ? result.getTotalScore() : null,
                result != null ? result.getFeedbackContent() : null,
                result != null ? result.getAnalyzedDate() : null,

                // 상세 결과
                result != null ? result.getComparisonVideoUrl() : null,
                result != null ? result.getJsonResultUrl() : null,
                result != null ? result.getTopErrorJointsJson() : null,
                result != null ? result.getTopErrorFramesJson() : null);
    }
}
