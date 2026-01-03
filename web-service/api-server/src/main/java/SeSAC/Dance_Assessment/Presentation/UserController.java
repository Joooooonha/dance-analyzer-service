package SeSAC.Dance_Assessment.Presentation;

import SeSAC.Dance_Assessment.Dto.User.LoginRequest;
import SeSAC.Dance_Assessment.Dto.User.SignupRequest;
import SeSAC.Dance_Assessment.Dto.User.UserResponse;
import SeSAC.Dance_Assessment.Service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * [NEW] 프론트엔드 연동을 위해 추가된 인증 컨트롤러
 * - 회원가입, 로그인, 현재 사용자 정보 조회 API 제공
 */
@RestController
@RequiredArgsConstructor
@RequestMapping("/api") // 프론트엔드와 구분하기 위해 /api prefix 사용
public class UserController {

    private final UserService userService;

    /**
     * [NEW] 회원가입 API
     * POST /api/auth/signup
     * 
     * 요청 본문:
     * {
     * "loginId": "user1",
     * "password": "1234",
     * "nickname": "댄서1",
     * "teamId": 1, // 기존 팀 가입 시 (optional)
     * "createTeamName": "" // 새 팀 생성 시 (optional)
     * }
     */
    @PostMapping("/auth/signup")
    public ResponseEntity<UserResponse> signup(@RequestBody SignupRequest request) {
        UserResponse response = userService.signup(request);
        return ResponseEntity.ok(response);
    }

    /**
     * [NEW] 로그인 API
     * POST /api/auth/login
     * 
     * 요청 본문:
     * {
     * "loginId": "user1",
     * "password": "1234"
     * }
     * 
     * 응답: 사용자 정보 (프론트에서 localStorage에 저장)
     */
    @PostMapping("/auth/login")
    public ResponseEntity<UserResponse> login(@RequestBody LoginRequest request) {
        UserResponse response = userService.login(request);
        return ResponseEntity.ok(response);
    }

    /**
     * [NEW] 현재 로그인된 사용자 정보 조회 API
     * GET /api/users/me
     * 
     * 헤더: X-User-Id (로그인된 사용자 ID)
     */
    @GetMapping("/users/me")
    public ResponseEntity<UserResponse> getCurrentUser(@RequestHeader("X-User-Id") Long userId) {
        UserResponse response = userService.getCurrentUser(userId);
        return ResponseEntity.ok(response);
    }
}
