package SeSAC.Dance_Assessment.Security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.lang.NonNull;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/**
 * 요청마다 쿠키의 JWT를 확인해 인증 정보를 채운다.
 *
 * <p>이 필터가 {@code X-User-Id} 헤더를 대체한다. 예전에는 클라이언트가 보낸
 * 헤더 값을 그대로 신뢰했기 때문에, 헤더만 바꾸면 아무나 남의 계정이 될 수 있었다.
 * 이제 사용자 id는 <b>서버가 서명한 토큰에서만</b> 나온다.
 */
@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtTokenProvider tokenProvider;
    private final JwtCookie jwtCookie;

    @Override
    protected void doFilterInternal(@NonNull HttpServletRequest request,
                                    @NonNull HttpServletResponse response,
                                    @NonNull FilterChain chain)
            throws ServletException, IOException {

        jwtCookie.read(request)
                .map(tokenProvider::parseUserId)
                .ifPresent(userId -> {
                    var auth = new UsernamePasswordAuthenticationToken(
                            userId, null, List.of());
                    auth.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                    SecurityContextHolder.getContext().setAuthentication(auth);
                });

        chain.doFilter(request, response);
    }
}
