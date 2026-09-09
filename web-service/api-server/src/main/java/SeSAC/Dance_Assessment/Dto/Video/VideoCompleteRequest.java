package SeSAC.Dance_Assessment.Dto.Video;

/**
 * 업로드 완료 통보.
 *
 * <p>브라우저가 저장소에 직접 올리기 때문에 서버는 완료 시점을 알 수 없다.
 * 이 호출이 와야 영상이 분석 대상이 된다.
 *
 * @param assignmentId     숙제 제출인 경우
 * @param referenceVideoId 자유 연습에서 직접 고른 기준 영상
 */
public record VideoCompleteRequest(
        Long assignmentId,
        Long referenceVideoId) {
}
