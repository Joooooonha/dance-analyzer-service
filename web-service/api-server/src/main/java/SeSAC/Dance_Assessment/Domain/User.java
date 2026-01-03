package SeSAC.Dance_Assessment.Domain;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Getter
@Table(name = "users")
@NoArgsConstructor(access = AccessLevel.PROTECTED) // 안정성을 위해 코드 추천 받음 -> 기본 생성자 접근 제한
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "user_id")
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "team_id")
    private Team team;

    private String loginId;
    private String password;
    private String nickname;

    @Builder
    public User(String loginId, String nickname, String password) {
        this.loginId = loginId;
        this.nickname = nickname;
        this.password = password; // [NEW] Builder에 password 추가
    }

    public void setTeam(Team team) {
        this.team = team;
    }

    /**
     * [NEW] 비밀번호 설정 메서드
     * - 회원가입 시 비밀번호 설정에 사용
     * - 실제 운영 시에는 암호화(BCrypt 등) 적용 필요
     */
    public void setPassword(String password) {
        this.password = password;
    }
}
