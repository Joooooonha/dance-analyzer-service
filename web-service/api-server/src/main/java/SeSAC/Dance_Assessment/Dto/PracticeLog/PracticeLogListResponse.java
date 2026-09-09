package SeSAC.Dance_Assessment.Dto.PracticeLog;

import SeSAC.Dance_Assessment.Domain.AnalysisResult;
import SeSAC.Dance_Assessment.Domain.AnalysisStatus;
import SeSAC.Dance_Assessment.Domain.PracticeLog;

import SeSAC.Dance_Assessment.Dto.ApiTime;

import java.time.Instant;

/**
 * 연습 기록 목록 항목.
 *
 * <p><b>점수 필드를 뺐다.</b> 0~100 환산 상수가 임의값이라 절대값에 의미가 없어
 * 화면에서 제거했다. 대신 {@code issueCount}(틀린 동작 구간 개수)를 준다.
 * 분석 전이면 null이다 — 0으로 채우면 "완벽했다"로 읽히기 때문이다.
 */
public record PracticeLogListResponse(
        Long logId,
        Instant createdDate,
        String title,
        Integer issueCount,
        AnalysisStatus status
) {
    public static PracticeLogListResponse from(PracticeLog log) {
        AnalysisResult result = log.getAnalysisResult();

        return new PracticeLogListResponse(
                log.getId(),
                ApiTime.utc(log.getCreatedAt()),
                "연습 영상 " + log.getId(), // 제목 로직
                result != null ? result.getIssueCount() : null,
                result != null ? result.getStatus() : AnalysisStatus.WAITING
        );
    }
}
