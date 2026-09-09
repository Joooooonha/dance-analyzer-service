package SeSAC.Dance_Assessment.Dto.PracticeLog;

import SeSAC.Dance_Assessment.Domain.AnalysisStatus;

/**
 * 분석 요청 접수 결과.
 *
 * <p>분석은 비동기다. 이 응답은 "시작했다"는 뜻이지 결과가 아니다.
 * 클라이언트는 {@code pollUrl}을 폴링해 {@code status}가 COMPLETED가 되기를
 * 기다린다. 실측 소요는 약 2분이다(맥미니 CPU, 30초 구간, stride=2 기준).
 */
public record AnalysisAcceptedResponse(
        Long logId,
        AnalysisStatus status,
        boolean trimApplied,
        String pollUrl,
        String message) {

    public static AnalysisAcceptedResponse accepted(Long logId, boolean trimApplied) {
        String note = trimApplied
                ? "분석을 시작했습니다. 2~3분 정도 걸립니다."
                : "분석을 시작했습니다. 2~3분 정도 걸립니다. "
                        + "두 영상의 안무 시작 시각을 지정하면 결과가 더 정확해집니다.";
        return new AnalysisAcceptedResponse(
                logId, AnalysisStatus.PROCESSING, trimApplied, pollUrl(logId), note);
    }

    public static AnalysisAcceptedResponse alreadyRunning(Long logId) {
        return new AnalysisAcceptedResponse(
                logId, AnalysisStatus.PROCESSING, false, pollUrl(logId),
                "이미 분석이 진행 중입니다.");
    }

    private static String pollUrl(Long logId) {
        return "/practice-logs/" + logId;
    }
}
