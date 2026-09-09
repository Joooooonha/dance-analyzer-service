package SeSAC.Dance_Assessment;

import SeSAC.Dance_Assessment.Domain.User;
import SeSAC.Dance_Assessment.Infrastructure.UserRepository;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Profile;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * 개발용 시드 데이터.
 *
 * <p><b>{@code dev} 프로파일에서만 동작한다.</b> 예전에는 프로파일 제한이 없어
 * 운영에서도 테스트 계정이 만들어질 수 있었다. 비밀번호가 붙은 계정이 운영에
 * 생기는 것은 그 자체로 위험하다.
 */
@Slf4j
@Profile("dev")
@Component
@RequiredArgsConstructor
public class InitDb {

    /** 개발 전용 계정 비밀번호. 운영에는 이 컴포넌트 자체가 로드되지 않는다. */
    private static final String DEV_PASSWORD = "test1234";

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @PostConstruct
    @Transactional
    public void init() {
        if (userRepository.count() > 0) {
            return;
        }
        createDevUser("test", "testUser");
        createDevUser("test2", "testUser2");
        log.info("========== 개발용 테스트 계정 생성 (비밀번호: {}) ==========", DEV_PASSWORD);
    }

    private void createDevUser(String loginId, String nickname) {
        User user = User.builder()
                .loginId(loginId)
                .nickname(nickname)
                .build();
        // 평문 저장 금지 — 개발 계정도 예외 없이 해싱한다.
        user.setEncodedPassword(passwordEncoder.encode(DEV_PASSWORD));
        userRepository.save(user);
    }
}
