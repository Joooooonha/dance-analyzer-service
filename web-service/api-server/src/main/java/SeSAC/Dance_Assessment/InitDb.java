package SeSAC.Dance_Assessment;

import SeSAC.Dance_Assessment.Domain.User;
import SeSAC.Dance_Assessment.Infrastructure.UserRepository;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@RequiredArgsConstructor
public class InitDb {

    private final UserRepository userRepository;

    @PostConstruct
    @Transactional
    public void init() {
        // 유저가 한 명도 없으면 테스트 유저 생성
        if (userRepository.count() == 0) {
            User testUser = User.builder()
                    .loginId("test")
                    .nickname("testUser")
                    .build();
            User testUser2 = User.builder()
                    .loginId("test2")
                    .nickname("testUser2")
                    .build();
            userRepository.save(testUser);
            userRepository.save(testUser2);
            System.out.println("========== 테스트용 유저 생성 완료 ==========");
        }
    }
}