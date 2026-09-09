package SeSAC.Dance_Assessment.Dto.Video;

/**
 * 업로드 URL 발급 응답.
 *
 * @param videoId   등록된 영상 id. 업로드를 마친 뒤 완료 통보에 쓴다
 * @param uploadUrl 저장소에 직접 PUT할 서명된 URL (수십 분 후 만료)
 */
public record VideoUploadUrlResponse(Long videoId, String uploadUrl) {
}
