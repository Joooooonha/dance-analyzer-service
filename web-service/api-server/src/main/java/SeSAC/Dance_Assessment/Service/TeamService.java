package SeSAC.Dance_Assessment.Service;

import SeSAC.Dance_Assessment.Domain.Team;
import SeSAC.Dance_Assessment.Domain.User;
import SeSAC.Dance_Assessment.Dto.Team.TeamCreateRequest;
import SeSAC.Dance_Assessment.Dto.Team.TeamResponse;
import SeSAC.Dance_Assessment.Infrastructure.TeamRepository;
import SeSAC.Dance_Assessment.Infrastructure.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class TeamService {

    private final TeamRepository teamRepository;
    private final UserRepository userRepository;

    @Transactional
    public Long createTeam(Long userId, TeamCreateRequest request) {
        // 신청자 조회
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("유저 없음"));

        // if (user.getTeam() != null) {
        // throw new IllegalStateException("이미 소속된 팀이 있습니다.");
        // }

        // 팀 생성 및 저장
        Team team = new Team(request.name());
        teamRepository.save(team); // 영속성 컨텍스트가 아니라 Dirty Checking 안돼서 직접 저장

        // 관계 설정 (양방향)
        user.setTeam(team); // 사용자 -> 팀
        team.changeLeader(user); // 팀 -> 팀장

        return team.getId();
    }

    /**
     * [NEW] 팀 목록 조회
     * - 회원가입 시 가입 가능한 팀 목록을 보여주기 위해 사용
     * - 각 팀의 멤버 수도 함께 반환
     */
    public List<TeamResponse> getAllTeams() {
        List<Team> teams = teamRepository.findAll();

        return teams.stream()
                .map(team -> {
                    int memberCount = userRepository.countByTeamId(team.getId());
                    return TeamResponse.from(team, memberCount);
                })
                .toList();
    }
}
