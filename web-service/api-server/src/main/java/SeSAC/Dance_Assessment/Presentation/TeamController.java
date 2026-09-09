package SeSAC.Dance_Assessment.Presentation;

import SeSAC.Dance_Assessment.Dto.Team.TeamCreateRequest;
import SeSAC.Dance_Assessment.Dto.Team.TeamResponse;
import SeSAC.Dance_Assessment.Service.TeamService;
import SeSAC.Dance_Assessment.Security.CurrentUserId;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequiredArgsConstructor
public class TeamController {

    private final TeamService teamService;

    // 팀 생성 API
    @PostMapping("/teams")
    public ResponseEntity<Long> createTeam(
            @CurrentUserId Long userId,
            @RequestBody TeamCreateRequest request) {
        Long teamId = teamService.createTeam(userId, request);
        return ResponseEntity.ok(teamId);
    }

    /**
     * [NEW] 팀 목록 조회 API
     * GET /teams
     * 
     * - 회원가입 시 가입 가능한 팀 목록을 보여주기 위해 사용
     * - 인증 없이 접근 가능
     */
    @GetMapping("/teams")
    public ResponseEntity<List<TeamResponse>> getAllTeams() {
        List<TeamResponse> teams = teamService.getAllTeams();
        return ResponseEntity.ok(teams);
    }
}
