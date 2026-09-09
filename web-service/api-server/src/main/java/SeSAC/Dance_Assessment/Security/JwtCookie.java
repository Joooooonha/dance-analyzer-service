package SeSAC.Dance_Assessment.Security;

import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.Arrays;
import java.util.Optional;

/**
 * JWT를 담는 쿠키를 굽고 지운다.
 *
 * <p><b>왜 localStorage가 아니라 httpOnly 쿠키인가.</b> localStorage에 둔 토큰은
 * 자바스크립트로 읽을 수 있어서, XSS가 한 번만 터져도 그대로 탈취된다.
 * httpOnly 쿠키는 스크립트가 읽지 못하고 브라우저가 알아서 실어 보낸다.
 * 프론트엔드와 API가 같은 도메인이라 이 방식이 가장 단순하기도 하다.
 */
@Component
public class JwtCookie {

    public static final String NAME = "access_token";

    /**
     * 운영에서는 반드시 true. HTTPS로만 쿠키가 전송된다.
     * 로컬 개발은 http라 false로 두지 않으면 쿠키가 아예 저장되지 않는다.
     */
    private final boolean secure;

    public JwtCookie(@Value("${app.cookie.secure:true}") boolean secure) {
        this.secure = secure;
    }

    public void write(HttpServletResponse response, String token, Duration maxAge) {
        Cookie cookie = new Cookie(NAME, token);
        cookie.setHttpOnly(true);
        cookie.setSecure(secure);
        cookie.setPath("/");
        cookie.setMaxAge((int) maxAge.toSeconds());
        // Lax면 외부 사이트에서 넘어오는 GET에는 쿠키가 실린다. OAuth 공급자가
        // 리다이렉트로 돌려보내는 흐름을 살리면서 CSRF는 막는 절충점이다.
        cookie.setAttribute("SameSite", "Lax");
        response.addCookie(cookie);
    }

    public void clear(HttpServletResponse response) {
        Cookie cookie = new Cookie(NAME, "");
        cookie.setHttpOnly(true);
        cookie.setSecure(secure);
        cookie.setPath("/");
        cookie.setMaxAge(0);
        cookie.setAttribute("SameSite", "Lax");
        response.addCookie(cookie);
    }

    public Optional<String> read(HttpServletRequest request) {
        if (request.getCookies() == null) {
            return Optional.empty();
        }
        return Arrays.stream(request.getCookies())
                .filter(c -> NAME.equals(c.getName()))
                .map(Cookie::getValue)
                .filter(v -> v != null && !v.isBlank())
                .findFirst();
    }
}
