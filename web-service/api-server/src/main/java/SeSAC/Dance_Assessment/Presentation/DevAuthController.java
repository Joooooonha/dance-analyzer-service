package SeSAC.Dance_Assessment.Presentation;

import SeSAC.Dance_Assessment.Domain.User;
import SeSAC.Dance_Assessment.Dto.User.LoginRequest;
import SeSAC.Dance_Assessment.Dto.User.SignupRequest;
import SeSAC.Dance_Assessment.Dto.User.UserResponse;
import SeSAC.Dance_Assessment.Security.JwtCookie;
import SeSAC.Dance_Assessment.Security.JwtTokenProvider;
import SeSAC.Dance_Assessment.Service.UserService;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Profile;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * 아이디/비밀번호 로그인 — <b>개발 환경 전용</b>.
 *
 * <p>소셜 로그인만 두면 로컬에서 개발할 때마다 실제 카카오/네이버 로그인을
 * 거쳐야 해서 남겨둔 경로다. 운영에서는 이 컨트롤러 자체가 빈으로 등록되지 않아
 * 엔드포인트가 존재하지 않는다(404). 덕분에 운영 DB에는 비밀번호가 저장되지 않는다.
 *
 * <p><b>왜 별도 클래스인가.</b> 처음에는 {@code UserController}의 메서드에
 * {@code @Profile("dev")}를 붙였는데 <b>아무 효과가 없었다</b> —
 * {@code @Profile}은 빈(클래스/{@code @Bean} 메서드) 단위로만 동작하고
 * 컨트롤러의 요청 매핑 메서드에는 적용되지 않는다. 그래서 운영 프로파일에서도
 * {@code POST /api/auth/signup}이 200으로 계정을 만들어 주고 있었다.
 * 프로파일로 무언가를 끄려면 <b>반드시 클래스를 분리</b>해야 한다.
 */
@Profile("dev")
@RestController
@RequiredArgsConstructor
public class DevAuthController {

    private final UserService userService;
    private final JwtTokenProvider tokenProvider;
    private final JwtCookie jwtCookie;

    @PostMapping("/auth/signup")
    public ResponseEntity<UserResponse> signup(@RequestBody SignupRequest request) {
        return ResponseEntity.ok(userService.signup(request));
    }

    /** 성공하면 JWT를 httpOnly 쿠키로 굽는다 (응답 본문에 토큰은 없다). */
    @PostMapping("/auth/login")
    public ResponseEntity<UserResponse> login(@RequestBody LoginRequest request,
                                              HttpServletResponse response) {
        User user = userService.login(request);
        jwtCookie.write(response, tokenProvider.createToken(user.getId()),
                tokenProvider.getValidity());
        return ResponseEntity.ok(userService.toResponse(user));
    }
}
