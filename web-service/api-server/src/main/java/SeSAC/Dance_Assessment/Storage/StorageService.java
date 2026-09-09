package SeSAC.Dance_Assessment.Storage;

import java.time.Duration;

/**
 * 영상·결과물 저장소.
 *
 * <p><b>파일 바이트가 Spring을 지나가지 않는 것이 핵심이다.</b> 브라우저는
 * presigned URL로 저장소에 직접 올리고, 맥미니의 분석 서버도 저장소에서 직접
 * 받는다. EC2는 "누가 무엇에 접근해도 되는지"만 판단하고 URL을 발급한다.
 *
 * <p>이렇게 하는 이유:
 * <ul>
 *   <li>영상이 100MB에 가까운데 EC2 대역폭·디스크를 쓰지 않는다</li>
 *   <li>Cloudflare 프록시의 요청 본문 100MB 제한을 거치지 않는다</li>
 *   <li>맥미니에 저장소 자격증명을 두지 않아도 된다 — 짧은 URL만 받는다.
 *       홈서버가 뚫려도 만료된 URL 몇 개 외에는 얻을 것이 없다</li>
 * </ul>
 */
public interface StorageService {

    /** presigned URL 기본 유효 기간. 업로드/분석에 충분하되 길지 않게. */
    Duration DEFAULT_EXPIRY = Duration.ofMinutes(30);

    /**
     * 이 키에 파일을 올릴 수 있는 일회성 URL.
     *
     * @param contentType 브라우저가 실제로 보낼 Content-Type.
     *                    서명에 포함되므로 값이 다르면 업로드가 거부된다.
     */
    String createUploadUrl(String key, String contentType, Duration expiry);

    /** 이 키를 내려받을 수 있는 일회성 URL. */
    String createDownloadUrl(String key, Duration expiry);

    /** 객체를 지운다. 없으면 조용히 넘어간다. */
    void delete(String key);

    default String createUploadUrl(String key, String contentType) {
        return createUploadUrl(key, contentType, DEFAULT_EXPIRY);
    }

    default String createDownloadUrl(String key) {
        return createDownloadUrl(key, DEFAULT_EXPIRY);
    }
}
