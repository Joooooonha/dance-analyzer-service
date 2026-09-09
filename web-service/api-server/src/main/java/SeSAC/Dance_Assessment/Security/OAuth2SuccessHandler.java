package SeSAC.Dance_Assessment.Security;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.security.web.authentication.SimpleUrlAuthenticationSuccessHandler;
import org.springframework.stereotype.Component;

import java.io.IOException;

/**
 * 소셜 로그인 성공 후 JWT를 쿠키에 굽고 프론트로 돌려보낸다.
 *
 * <p><b>토큰을 URL 쿼리에 실어 보내지 않는다.</b> 그 방식은 브라우저 기록,
 * 리퍼러 헤더, 서버 접근 로그에 토큰이 그대로 남는다. 쿠키로 주면 프론트엔드가
 * 토큰을 만질 일 자체가 없다.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class OAuth2SuccessHandler extends SimpleUrlAuthenticationSuccessHandler {

    private final JwtTokenProvider tokenProvider;
    private final JwtCookie jwtCookie;

    @Value("${app.frontend.redirect-uri:http://localhost:5173}")
    private String frontendRedirectUri;

    @Override
    public void onAuthenticationSuccess(HttpServletRequest request,
                                        HttpServletResponse response,
                                        Authentication authentication) throws IOException {

        OAuth2User principal = (OAuth2User) authentication.getPrincipal();
        Long userId = ((Number) principal.getAttributes()
                .get(CustomOAuth2UserService.USER_ID_ATTRIBUTE)).longValue();

        String token = tokenProvider.createToken(userId);
        jwtCookie.write(response, token, tokenProvider.getValidity());

        log.info("[로그인 성공] userId={}", userId);
        getRedirectStrategy().sendRedirect(request, response, frontendRedirectUri);
    }
}
