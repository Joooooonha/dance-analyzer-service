package SeSAC.Dance_Assessment.Config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.List;

/**
 * CORS 설정.
 *
 * <p>{@code CorsFilter} 빈이 아니라 {@link CorsConfigurationSource}로 노출한다.
 * Spring Security가 이 소스를 받아 자기 필터 체인 안에서 CORS를 처리하게 하려는
 * 것이다. 별도 필터로 두면 Security 체인과 순서가 얽혀 프리플라이트가 인증에
 * 먼저 걸리는 일이 생긴다.
 */
@Configuration
public class CorsConfig {

    /**
     * 허용할 프론트엔드 오리진. 배포 도메인이 정해지면 설정으로 덮어쓴다.
     * 쿠키를 주고받으므로 와일드카드(*)는 쓸 수 없다 — 명시해야 한다.
     */
    @Value("${app.cors.allowed-origins:http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000}")
    private List<String> allowedOrigins;

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration config = new CorsConfiguration();

        // httpOnly 쿠키를 실어 보내려면 반드시 true여야 한다.
        config.setAllowCredentials(true);
        config.setAllowedOrigins(allowedOrigins);
        config.addAllowedHeader("*");

        // 메서드를 하나씩 나열하면 새 메서드를 쓸 때마다 프리플라이트가 막힌다
        // (실제로 PATCH /practice-logs/{id}/trim이 이 문제를 겪었다).
        // 어차피 Origin으로 제한하므로 전부 허용한다.
        config.addAllowedMethod("*");

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return source;
    }
}
