package SeSAC.Dance_Assessment.Dto.Push;

/**
 * 브라우저의 {@code PushSubscription.toJSON()}을 그대로 받는다.
 *
 * <p>키 두 개(p256dh, auth)는 <b>종단간 암호화용</b>이다. 이걸로 암호화해서
 * 보내기 때문에 중간의 푸시 서비스(구글·모질라)는 알림 내용을 볼 수 없다.
 */
public record PushSubscribeRequest(String endpoint, Keys keys) {
    public record Keys(String p256dh, String auth) {
    }
}
