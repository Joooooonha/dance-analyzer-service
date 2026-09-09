package SeSAC.Dance_Assessment.Dto.Video;

/**
 * 영상 업로드 응답.
 *
 * <p>예전에는 {@code videoId}(Long) 하나만 돌려줬고, 프론트가 그 값을
 * <b>연습 기록 id로도 그대로 썼다.</b> 업로드 한 번이 Video 한 행과 PracticeLog
 * 한 행을 항상 함께 만들던 시절에는 두 IDENTITY 값이 우연히 같이 늘어나 동작했지만,
 * 보장된 계약이 아니었다 — 한쪽에만 행이 생기는 경로가 하나라도 늘면 조용히
 * 엉뚱한 기록을 가리킨다. 그래서 {@code logId}를 명시적으로 내려준다.
 *
 * @param videoId    저장된 영상 id
 * @param logId      이 업로드로 만들어진 연습 기록 id.
 *                   기준 영상 업로드처럼 연습 기록이 생기지 않는 경우 {@code null}
 * @param analyzable 지금 바로 분석을 요청할 수 있는지 (기준 영상이 연결됐는지)
 */
public record VideoUploadResponse(
        Long videoId,
        Long logId,
        boolean analyzable) {
}
