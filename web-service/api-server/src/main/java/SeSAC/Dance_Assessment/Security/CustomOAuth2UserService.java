package SeSAC.Dance_Assessment.Security;

import SeSAC.Dance_Assessment.Domain.User;
import SeSAC.Dance_Assessment.Infrastructure.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.oauth2.client.userinfo.DefaultOAuth2UserService;
import org.springframework.security.oauth2.client.userinfo.OAuth2UserRequest;
import org.springframework.security.oauth2.core.user.DefaultOAuth2User;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;

/**
 * 소셜 로그인 성공 시 사용자를 찾거나 새로 만든다.
 *
 * <p>가입과 로그인을 구분하지 않는다 — 소셜 로그인은 "처음 오면 가입, 아니면 로그인"이
 * 자연스럽다. 별도 가입 절차를 두면 사용자만 번거로워진다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class CustomOAuth2UserService extends DefaultOAuth2UserService {

    /** 성공 핸들러가 이 키로 사용자 id를 꺼내 JWT를 만든다. */
    public static final String USER_ID_ATTRIBUTE = "appUserId";

    private final UserRepository userRepository;

    @Override
    @Transactional
    public OAuth2User loadUser(OAuth2UserRequest request) {
        OAuth2User oAuth2User = super.loadUser(request);
        String registrationId = request.getClientRegistration().getRegistrationId();

        OAuthAttributes attributes =
                OAuthAttributes.of(registrationId, oAuth2User.getAttributes());

        User user = userRepository
                .findByProviderAndProviderId(attributes.provider(), attributes.providerId())
                .map(existing -> {
                    existing.updateNickname(attributes.nickname());
                    return existing;
                })
                .orElseGet(() -> {
                    log.info("[소셜 가입] {} / {}", attributes.provider(), attributes.nickname());
                    return userRepository.save(User.ofSocial(
                            attributes.provider(), attributes.providerId(), attributes.nickname()));
                });

        // 원본 속성에 우리 쪽 사용자 id를 얹어서 넘긴다.
        Map<String, Object> merged = new java.util.HashMap<>(oAuth2User.getAttributes());
        merged.put(USER_ID_ATTRIBUTE, user.getId());

        return new DefaultOAuth2User(List.of(), merged, USER_ID_ATTRIBUTE);
    }
}
