package SeSAC.Dance_Assessment.Config;

import SeSAC.Dance_Assessment.Security.CurrentUserIdArgumentResolver;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.method.support.HandlerMethodArgumentResolver;
import org.springframework.web.servlet.config.annotation.PathMatchConfigurer;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * {@code @CurrentUserId} 파라미터 주입과 API 경로 접두사를 등록한다.
 */
@Configuration
@RequiredArgsConstructor
public class WebMvcConfig implements WebMvcConfigurer {

    private final CurrentUserIdArgumentResolver currentUserIdArgumentResolver;

    @Override
    public void addArgumentResolvers(List<HandlerMethodArgumentResolver> resolvers) {
        resolvers.add(currentUserIdArgumentResolver);
    }

    /**
     * 모든 REST 컨트롤러를 {@code /api} 아래로 옮긴다.
     *
     * <p><b>왜 필요한가.</b> 프론트엔드도 SPA 라우팅을 쓰기 때문에 경로가 겹친다.
     * {@code /assignments}는 <b>숙제 목록 화면이면서 동시에 API</b>였다 —
     * Nginx가 경로만 보고는 어느 쪽으로 보낼지 정할 수 없어, 화면으로 들어가면
     * Spring의 404 페이지가 떴다. {@code /login}도 같은 문제였다.
     *
     * <p>접두사를 붙이면 규칙이 단순해진다: {@code /api}로 시작하면 백엔드,
     * 나머지는 전부 프론트엔드.
     *
     * <p>OAuth 경로({@code /oauth2/**}, {@code /login/oauth2/**})는 컨트롤러가
     * 아니라 <b>Spring Security 필터가 처리</b>하므로 이 설정의 영향을 받지 않는다.
     * 카카오·네이버 콘솔에 등록한 Redirect URI를 바꾸지 않아도 된다.
     */
    @Override
    public void configurePathMatch(PathMatchConfigurer configurer) {
        configurer.addPathPrefix("/api",
                c -> c.isAnnotationPresent(RestController.class));
    }
}
