package SeSAC.Dance_Assessment.Infrastructure;

import SeSAC.Dance_Assessment.Domain.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Long> {

    /**
     * [NEW] 로그인 아이디로 사용자 조회
     */
    Optional<User> findByLoginId(String loginId);

    /**
     * [NEW] 특정 팀의 멤버 수 조회
     */
    int countByTeamId(Long teamId);

    /**
     * [NEW] 특정 팀의 모든 멤버 조회
     */
    List<User> findAllByTeamId(Long teamId);
}
