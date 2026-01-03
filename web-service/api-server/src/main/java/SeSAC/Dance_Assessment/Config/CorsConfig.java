package SeSAC.Dance_Assessment.Config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.filter.CorsFilter;

/**
 * [NEW] 프론트엔드 연동을 위한 CORS 설정
 * - 프론트엔드 개발 서버(localhost:5173)에서의 요청을 허용
 */
@Configuration
public class CorsConfig {

    @Bean
    public CorsFilter corsFilter() {
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        CorsConfiguration config = new CorsConfiguration();

        // 자격 증명 허용 (쿠키 등)
        config.setAllowCredentials(true);

        // 허용할 Origin (프론트엔드 개발 서버)
        config.addAllowedOrigin("http://localhost:5173");
        config.addAllowedOrigin("http://localhost:3000");
        config.addAllowedOrigin("http://127.0.0.1:5173");

        // 허용할 헤더
        config.addAllowedHeader("*");

        // X-User-Id 헤더를 노출 (프론트에서 읽을 수 있도록)
        config.addExposedHeader("X-User-Id");

        // 허용할 HTTP 메서드
        config.addAllowedMethod("GET");
        config.addAllowedMethod("POST");
        config.addAllowedMethod("PUT");
        config.addAllowedMethod("DELETE");
        config.addAllowedMethod("OPTIONS");

        source.registerCorsConfiguration("/**", config);
        return new CorsFilter(source);
    }
}
