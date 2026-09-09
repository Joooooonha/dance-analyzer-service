package SeSAC.Dance_Assessment.Service;

import SeSAC.Dance_Assessment.Domain.PushSubscription;
import SeSAC.Dance_Assessment.Infrastructure.PushSubscriptionRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import nl.martijndwars.webpush.Notification;
import nl.martijndwars.webpush.PushService;
import nl.martijndwars.webpush.Subscription;
import org.apache.http.HttpResponse;
import org.bouncycastle.jce.provider.BouncyCastleProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.Security;
import java.util.List;
import java.util.Map;

/**
 * 브라우저 푸시 발송.
 *
 * <p><b>키가 설정되지 않으면 조용히 아무것도 하지 않는다.</b> 개발 환경에서
 * VAPID 키 없이 띄우는 일이 흔한데, 알림이 안 가는 것 때문에 분석 자체가
 * 실패해서는 안 된다. 대신 시작할 때 한 번 경고를 남긴다.
 *
 * <p>발송 실패도 삼킨다 — 알림은 부가 기능이고, 실패의 대부분은 사용자가
 * 브라우저 데이터를 지워 구독이 죽은 경우다. 그런 구독(404/410)은 지운다.
 */
@Slf4j
@Service
public class WebPushService {

    /**
     * VAPID 서명은 P-256 곡선을 쓴다. JDK 기본 제공자로도 되지만 web-push가
     * BouncyCastle을 전제로 하고 있어 명시적으로 등록한다. 등록하지 않으면
     * 발송 시점에 "algorithm not available"로 실패한다.
     */
    static {
        if (Security.getProvider(BouncyCastleProvider.PROVIDER_NAME) == null) {
            Security.addProvider(new BouncyCastleProvider());
        }
    }

    private final PushSubscriptionRepository repository;
    private final ObjectMapper objectMapper;
    private final PushService pushService;   // 키가 없으면 null

    public WebPushService(PushSubscriptionRepository repository,
                          ObjectMapper objectMapper,
                          @Value("${push.vapid.public-key:}") String publicKey,
                          @Value("${push.vapid.private-key:}") String privateKey,
                          @Value("${push.vapid.subject:mailto:admin@odostudio.site}") String subject) {
        this.repository = repository;
        this.objectMapper = objectMapper;

        PushService svc = null;
        if (!publicKey.isBlank() && !privateKey.isBlank()) {
            try {
                svc = new PushService(publicKey, privateKey, subject);
            } catch (Exception e) {
                log.error("[푸시] VAPID 키가 잘못됐습니다. 알림이 발송되지 않습니다.", e);
            }
        } else {
            log.warn("[푸시] VAPID 키가 없어 알림을 보내지 않습니다 "
                    + "(push.vapid.public-key / private-key 설정 필요)");
        }
        this.pushService = svc;
    }

    public boolean isEnabled() {
        return pushService != null;
    }

    /**
     * 한 사용자의 모든 기기로 알림을 보낸다.
     *
     * <p>죽은 구독은 여기서 정리한다. 그냥 두면 사용자가 기기를 바꿀 때마다
     * 쌓여서, 알림 한 번에 실패하는 발송이 계속 늘어난다.
     */
    @Transactional
    public void sendToUser(Long userId, String title, String body, String url) {
        if (pushService == null) {
            return;
        }
        List<PushSubscription> subs = repository.findByUserId(userId);
        if (subs.isEmpty()) {
            return;
        }

        String payload;
        try {
            payload = objectMapper.writeValueAsString(
                    Map.of("title", title, "body", body, "url", url));
        } catch (Exception e) {
            log.warn("[푸시] 본문 직렬화 실패: {}", e.getMessage());
            return;
        }

        for (PushSubscription sub : subs) {
            try {
                HttpResponse res = pushService.send(new Notification(
                        new Subscription(sub.getEndpoint(),
                                new Subscription.Keys(sub.getP256dh(), sub.getAuth())),
                        payload));
                int status = res.getStatusLine().getStatusCode();

                // 404/410 = 구독이 더 이상 없다. 브라우저 데이터를 지웠거나
                // 앱을 삭제한 경우다. 다시 시도해도 영영 성공하지 않으므로 지운다.
                if (status == 404 || status == 410) {
                    log.info("[푸시] 만료된 구독 삭제 (userId={}, status={})", userId, status);
                    repository.delete(sub);
                } else if (status >= 400) {
                    log.warn("[푸시] 발송 실패 (userId={}, status={})", userId, status);
                }
            } catch (Exception e) {
                // 알림이 실패해도 분석 결과는 이미 저장돼 있다. 화면을 열면 보인다.
                log.warn("[푸시] 발송 오류 (userId={}): {}", userId, e.getMessage());
            }
        }
    }
}
