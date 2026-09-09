package SeSAC.Dance_Assessment.Dto.Video;

import SeSAC.Dance_Assessment.Domain.Video;
import SeSAC.Dance_Assessment.Dto.ApiTime;

import java.time.Instant;

/**
 * 다시 쓸 수 있는 영상 하나. 목록에서 고르는 용도라 최소한만 담는다.
 *
 * <p>저장소 키는 내보내지 않는다 — 재생과 분석은 모두 videoId로 하고,
 * 실제 위치는 서버만 안다.
 *
 * @param name     사용자가 올린 파일 이름. 이 컬럼이 생기기 전 행에는 없어 null일 수 있다
 * @param startSec 저장돼 있는 안무 시작 시각. 다시 쓰면 그대로 재사용된다
 */
public record VideoSummaryResponse(
        Long videoId,
        String name,
        Instant uploadedAt,
        Double startSec,
        Double endSec) {

    public static VideoSummaryResponse from(Video v) {
        return new VideoSummaryResponse(
                v.getId(),
                v.getOriginalName(),
                ApiTime.utc(v.getCreatedAt()),
                v.getChoreographyStartSec(),
                v.getChoreographyEndSec());
    }
}
