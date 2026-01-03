package SeSAC.Dance_Assessment.Dto.User;

import SeSAC.Dance_Assessment.Domain.User;

/**
 * [NEW] 프론트엔드 연동을 위해 추가된 사용자 정보 응답 DTO
 * - 로그인 후 또는 /users/me에서 사용자 정보를 반환할 때 사용
 */
public record UserResponse(
        Long id,
        String loginId,
        String nickname,
        Long teamId,
        String teamName,
        boolean isLeader // 팀장 여부
) {
    public static UserResponse from(User user, boolean isLeader) {
        return new UserResponse(
                user.getId(),
                user.getLoginId(),
                user.getNickname(),
                user.getTeam() != null ? user.getTeam().getId() : null,
                user.getTeam() != null ? user.getTeam().getTeamName() : null,
                isLeader);
    }
}
