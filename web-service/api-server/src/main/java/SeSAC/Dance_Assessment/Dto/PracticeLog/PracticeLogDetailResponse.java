package SeSAC.Dance_Assessment.Dto.PracticeLog;

import SeSAC.Dance_Assessment.Domain.AnalysisResult;
import SeSAC.Dance_Assessment.Domain.AnalysisStatus;
import SeSAC.Dance_Assessment.Domain.PracticeLog;
import SeSAC.Dance_Assessment.Domain.Video;

import SeSAC.Dance_Assessment.Dto.ApiTime;

import java.time.Instant;
import java.util.List;

/**
 * 연습 기록 상세 조회 응답.
 *
 * <p>분석이 비동기라 이 API가 <b>폴링 대상</b>이다. {@code status}가
 * COMPLETED가 되면 구간 피드백 필드들이 채워진다.
 *
 * <p><b>점수 필드가 없다.</b> 0~100 환산 상수가 임의값이라 절대값에 의미가
 * 없어서다. 대신 {@code issueCount}(틀린 동작 구간 개수)와 {@code topIssuesJson}을
 * 쓴다.
 */
public record PracticeLogDetailResponse(
        Long logId,
        Long userId,
        Instant createdAt,

        // 연습 영상 정보 (재생은 GET /videos/{id}. 저장 위치는 내려주지 않는다)
        Long practiceVideoId,
        Double practiceStartSec,
        Double practiceEndSec,

        // 기준 영상 정보
        Long referenceVideoId,
        Double referenceStartSec,
        Double referenceEndSec,

        // 분석 상태
        AnalysisStatus status,
        Instant analyzedAt,

        // 분석 결과 — 구간 피드백
        Integer issueCount,
        String feedback,
        String topIssuesJson,
        String unreliableSpansJson,
        String unreliableNote,
        String qualityJson,
        String qualityWarning,

        // 두 영상을 맞춰 재생하기 위한 대응표 [[연습 시각, 기준 시각], ...] (초).
        // 화면이 이걸로 원본 영상 두 개를 같은 안무 지점에 맞춰 돌린다.
        String syncMapJson,

        // 결과물. 서명 URL은 만료되므로 조회할 때마다 새로 만들어 담는다.
        String comparisonVideoUrl,
        List<String> issueImageUrls) {

    /**
     * 목록용 — 결과물 URL 없이 만든다.
     *
     * <p>서명 URL 발급은 공짜가 아니고(HMAC 계산), 목록 화면은 이미지를 쓰지도
     * 않는다. 기록 20개를 그리려고 URL 200개를 만들 이유가 없다.
     */
    public static PracticeLogDetailResponse from(PracticeLog log) {
        return from(log, null, List.of());
    }

    /**
     * @param comparisonVideoUrl 비교 영상 서명 URL. 없으면 null
     * @param issueImageUrls     상위 구간 순서대로의 비교 이미지 서명 URL.
     *                           만들지 못한 구간 자리는 null이 들어간다
     */
    public static PracticeLogDetailResponse from(PracticeLog log,
                                                 String comparisonVideoUrl,
                                                 List<String> issueImageUrls) {
        AnalysisResult result = log.getAnalysisResult();
        Video practice = log.getPracticeVideo();
        Video reference = log.getReferenceVideo();

        return new PracticeLogDetailResponse(
                log.getId(),
                log.getUser() != null ? log.getUser().getId() : null,
                ApiTime.utc(log.getCreatedAt()),

                practice != null ? practice.getId() : null,
                practice != null ? practice.getChoreographyStartSec() : null,
                practice != null ? practice.getChoreographyEndSec() : null,

                reference != null ? reference.getId() : null,
                reference != null ? reference.getChoreographyStartSec() : null,
                reference != null ? reference.getChoreographyEndSec() : null,

                result != null ? result.getStatus() : AnalysisStatus.WAITING,
                result != null ? ApiTime.utc(result.getAnalyzedDate()) : null,

                result != null ? result.getIssueCount() : null,
                result != null ? result.getFeedbackContent() : null,
                result != null ? result.getTopIssuesJson() : null,
                result != null ? result.getUnreliableSpansJson() : null,
                result != null ? result.getUnreliableNote() : null,
                result != null ? result.getQualityJson() : null,
                result != null ? result.getQualityWarning() : null,
                result != null ? result.getSyncMapJson() : null,

                comparisonVideoUrl,
                issueImageUrls);
    }
}
