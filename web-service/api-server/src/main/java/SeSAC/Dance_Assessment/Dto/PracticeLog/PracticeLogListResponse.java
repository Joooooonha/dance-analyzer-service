package SeSAC.Dance_Assessment.Dto.PracticeLog;

import SeSAC.Dance_Assessment.Domain.AnalysisStatus;
import SeSAC.Dance_Assessment.Domain.PracticeLog;

import java.time.LocalDateTime;

public record PracticeLogListResponse(
        Long logId,
        LocalDateTime createdDate,
        String title,
        Integer score,
        AnalysisStatus status
) {
    public static PracticeLogListResponse from(PracticeLog log) {
        Integer score = 0;
        AnalysisStatus status = AnalysisStatus.WAITING;

        if (log.getAnalysisResult() != null) {
            score = log.getAnalysisResult().getTotalScore();
            status = log.getAnalysisResult().getStatus();
        }

        return new PracticeLogListResponse(
                log.getId(),
                log.getCreatedAt(),
                "연습 영상 " + log.getId(), // 제목 로직
                score,
                status
        );
    }
}
