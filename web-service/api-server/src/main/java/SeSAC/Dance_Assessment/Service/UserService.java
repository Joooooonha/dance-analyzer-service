package SeSAC.Dance_Assessment.Service;

import SeSAC.Dance_Assessment.Domain.Team;
import SeSAC.Dance_Assessment.Domain.User;
import SeSAC.Dance_Assessment.Dto.User.LoginRequest;
import SeSAC.Dance_Assessment.Dto.User.SignupRequest;
import SeSAC.Dance_Assessment.Dto.User.UserResponse;
import SeSAC.Dance_Assessment.Infrastructure.TeamRepository;
import SeSAC.Dance_Assessment.Infrastructure.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * [NEW] 프론트엔드 연동을 위해 추가된 사용자 인증 서비스
 * - 회원가입, 로그인, 현재 사용자 조회 기능 제공
 * - 실제 운영 시에는 Spring Security + JWT 등으로 교체 권장
 */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class UserService {

    private final UserRepository userRepository;
    private final TeamRepository teamRepository;

    /**
     * [NEW] 회원가입
     * - teamId가 있으면 해당 팀에 가입
     * - createTeamName이 있으면 새 팀 생성 후 팀장이 됨
     * - 둘 다 없으면 무소속으로 가입
     */
    @Transactional
    public UserResponse signup(SignupRequest request) {
        // 1. 아이디 중복 체크
        if (userRepository.findByLoginId(request.loginId()).isPresent()) {
            throw new IllegalArgumentException("이미 사용 중인 아이디입니다.");
        }

        // 2. 사용자 생성
        User user = User.builder()
                .loginId(request.loginId())
                .nickname(request.nickname())
                .build();

        // 3. 비밀번호 설정 (실제로는 암호화 필요)
        user.setPassword(request.password());

        // 4. 팀 처리
        boolean isLeader = false;

        if (request.createTeamName() != null && !request.createTeamName().isBlank()) {
            // 새 팀 생성 - 팀장이 됨
            Team newTeam = new Team(request.createTeamName());
            teamRepository.save(newTeam);
            user.setTeam(newTeam);
            userRepository.save(user);
            newTeam.changeLeader(user);
            isLeader = true;
        } else if (request.teamId() != null) {
            // 기존 팀에 가입
            Team team = teamRepository.findById(request.teamId())
                    .orElseThrow(() -> new IllegalArgumentException("존재하지 않는 팀입니다."));
            user.setTeam(team);
            userRepository.save(user);
        } else {
            // 무소속
            userRepository.save(user);
        }

        return UserResponse.from(user, isLeader);
    }

    /**
     * [NEW] 로그인
     * - 간단한 아이디/비밀번호 확인
     * - 실제로는 JWT 토큰 발급 등 필요
     */
    public UserResponse login(LoginRequest request) {
        User user = userRepository.findByLoginId(request.loginId())
                .orElseThrow(() -> new IllegalArgumentException("존재하지 않는 아이디입니다."));

        // 비밀번호 확인 (실제로는 암호화된 비밀번호 비교 필요)
        if (!user.getPassword().equals(request.password())) {
            throw new IllegalArgumentException("비밀번호가 일치하지 않습니다.");
        }

        boolean isLeader = isTeamLeader(user);
        return UserResponse.from(user, isLeader);
    }

    /**
     * [NEW] 현재 로그인된 사용자 정보 조회
     */
    public UserResponse getCurrentUser(Long userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("존재하지 않는 사용자입니다."));

        boolean isLeader = isTeamLeader(user);
        return UserResponse.from(user, isLeader);
    }

    /**
     * [NEW] 팀장 여부 확인
     */
    private boolean isTeamLeader(User user) {
        if (user.getTeam() == null)
            return false;
        return user.getTeam().getLeader() != null
                && user.getTeam().getLeader().getId().equals(user.getId());
    }
}
