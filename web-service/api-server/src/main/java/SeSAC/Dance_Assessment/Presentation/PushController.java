package SeSAC.Dance_Assessment.Presentation;

import SeSAC.Dance_Assessment.Domain.PushSubscription;
import SeSAC.Dance_Assessment.Domain.User;
import SeSAC.Dance_Assessment.Dto.Push.PushSubscribeRequest;
import SeSAC.Dance_Assessment.Infrastructure.PushSubscriptionRepository;
import SeSAC.Dance_Assessment.Infrastructure.UserRepository;
import SeSAC.Dance_Assessment.Security.CurrentUserId;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 브라우저 푸시 구독 관리.
 *
 * <p>흐름: 화면이 {@code GET /push/public-key}로 VAPID 공개키를 받아
 * {@code pushManager.subscribe()}에 넘기고, 브라우저가 만들어준 구독 정보를
 * {@code POST /push/subscribe}로 올린다.
 *
 * <p>공개키는 이름 그대로 공개해도 되는 값이라 인증 없이 준다. 구독 등록은
 * 사용자에 묶이므로 인증이 필요하다.
 */
@RestController
@RequiredArgsConstructor
public class PushController {

    private final PushSubscriptionRepository repository;
    private final UserRepository userRepository;

    @Value("${push.vapid.public-key:}")
    private String publicKey;

    /** VAPID 공개키. 비어 있으면 화면이 구독 UI를 감춘다. */
    @GetMapping("/push/public-key")
    public ResponseEntity<Map<String, String>> publicKey() {
        return ResponseEntity.ok(Map.of("publicKey", publicKey));
    }

    /**
     * 구독 등록. 같은 브라우저가 다시 부르면 키만 갱신한다.
     *
     * <p>브라우저는 키를 주기적으로 새로 발급할 수 있는데, 그때 새 행을 만들면
     * 죽은 구독이 쌓인다. endpoint를 신원으로 삼아 갱신한다.
     */
    @PostMapping("/push/subscribe")
    @Transactional
    public ResponseEntity<Void> subscribe(@CurrentUserId Long userId,
                                          @RequestBody PushSubscribeRequest request) {
        if (request.endpoint() == null || request.keys() == null) {
            return ResponseEntity.badRequest().build();
        }

        repository.findByEndpoint(request.endpoint())
                .ifPresentOrElse(
                        existing -> existing.refresh(request.keys().p256dh(), request.keys().auth()),
                        () -> {
                            User user = userRepository.findById(userId)
                                    .orElseThrow(() -> new IllegalArgumentException("사용자 없음"));
                            repository.save(PushSubscription.builder()
                                    .user(user)
                                    .endpoint(request.endpoint())
                                    .p256dh(request.keys().p256dh())
                                    .auth(request.keys().auth())
                                    .build());
                        });
        return ResponseEntity.noContent().build();
    }

    /** 구독 해제. 브라우저에서 알림을 끌 때 부른다. */
    @DeleteMapping("/push/subscribe")
    @Transactional
    public ResponseEntity<Void> unsubscribe(@RequestParam String endpoint) {
        repository.deleteByEndpoint(endpoint);
        return ResponseEntity.noContent().build();
    }
}
