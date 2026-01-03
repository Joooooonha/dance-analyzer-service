package SeSAC.Dance_Assessment.Dto.Team;

import SeSAC.Dance_Assessment.Domain.Team;

/**
 * [NEW] 팀 목록 조회용 응답 DTO
 * - 회원가입 시 가입 가능한 팀 목록을 보여주기 위해 사용
 */
public record TeamResponse(
        Long id,
        String name,
        String leaderName,
        int memberCount) {
    public static TeamResponse from(Team team, int memberCount) {
        return new TeamResponse(
                team.getId(),
                team.getTeamName(),
                team.getLeader() != null ? team.getLeader().getNickname() : null,
                memberCount);
    }
}
