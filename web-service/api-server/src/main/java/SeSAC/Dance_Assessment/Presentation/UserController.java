package SeSAC.Dance_Assessment.Presentation;

import SeSAC.Dance_Assessment.Dto.User.UserResponse;
import SeSAC.Dance_Assessment.Security.CurrentUserId;
import SeSAC.Dance_Assessment.Security.JwtCookie;
import SeSAC.Dance_Assessment.Service.UserService;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * 모든 환경에서 열리는 인증 API.
 *
 * <p>아이디/비밀번호 로그인은 여기 없다 — {@code DevAuthController}에 분리했다.
 * 운영에서는 소셜 로그인({@code /oauth2/authorization/{kakao|naver}})만 쓴다.
 */
@RestController
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;
    private final JwtCookie jwtCookie;

    /**
     * 로그아웃 — 쿠키를 지운다.
     *
     * <p>JWT는 서버가 상태를 갖지 않아 "무효화"가 불가능하다. 쿠키를 지우면
     * 브라우저가 더 이상 토큰을 보내지 않는 것으로 충분하다고 보았다.
     * 탈취된 토큰까지 막으려면 블랙리스트가 필요한데, 지금 규모에는 과하다.
     */
    @PostMapping("/auth/logout")
    public ResponseEntity<Void> logout(HttpServletResponse response) {
        jwtCookie.clear(response);
        return ResponseEntity.noContent().build();
    }

    /**
     * 현재 로그인된 사용자 정보.
     *
     * <p>프론트엔드는 이 API로 로그인 상태를 확인한다. 쿠키가 httpOnly라
     * 자바스크립트가 토큰을 직접 볼 수 없기 때문이다. 인증이 없으면 401.
     */
    @GetMapping("/users/me")
    public ResponseEntity<UserResponse> getCurrentUser(@CurrentUserId Long userId) {
        return ResponseEntity.ok(userService.getCurrentUser(userId));
    }
}
