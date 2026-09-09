package SeSAC.Dance_Assessment.Domain;

import jakarta.persistence.*;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/**
 * 브라우저 푸시 구독 하나.
 *
 * <p><b>왜 필요한가.</b> 분석이 3분 넘게 걸리는데 그 사이 사용자가 탭을 닫거나
 * 폰을 잠그면 {@code Notification} API로는 아무것도 알릴 수 없다 — 그건 페이지가
 * 열려 있을 때만 동작한다. 브라우저를 닫아도 알림이 뜨려면 서버가 푸시 서비스
 * (FCM/APNs/Mozilla)로 보내야 하고, 그러려면 브라우저가 발급한 구독 정보를
 * 서버가 들고 있어야 한다.
 *
 * <p><b>사용자당 여러 개다.</b> 기기·브라우저마다 구독이 따로 생긴다.
 * 폰과 노트북에서 각각 로그인하면 둘 다 저장되고 둘 다로 알림이 간다.
 *
 * <p>{@code endpoint}가 구독의 신원이다. 같은 브라우저가 다시 구독하면 같은
 * endpoint가 오므로 여기에 유니크 제약을 걸어 중복을 막는다. 길이가 정해져
 * 있지 않고 500자를 넘기도 해서 인덱스는 걸지 않는다(그 대신 조회는 사용자로 한다).
 */
@Entity
@Getter
@NoArgsConstructor
@Table(name = "push_subscription",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_push_subscription_endpoint", columnNames = "endpoint"))
public class PushSubscription extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "push_subscription_id")
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id")
    private User user;

    /** 푸시 서비스 주소. 브라우저마다 다르고(FCM/Mozilla 등) 길다. */
    @JdbcTypeCode(SqlTypes.LONGVARCHAR)
    private String endpoint;

    /** 종단간 암호화용 공개키 (p256dh). 서버도 내용을 못 보게 하는 장치다. */
    private String p256dh;

    /** 종단간 암호화용 인증 비밀 (auth). */
    private String auth;

    @Builder
    public PushSubscription(User user, String endpoint, String p256dh, String auth) {
        this.user = user;
        this.endpoint = endpoint;
        this.p256dh = p256dh;
        this.auth = auth;
    }

    /** 같은 브라우저가 키를 새로 발급받았을 때 갱신한다. */
    public void refresh(String p256dh, String auth) {
        this.p256dh = p256dh;
        this.auth = auth;
    }
}
