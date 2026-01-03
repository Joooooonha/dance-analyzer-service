package SeSAC.Dance_Assessment.Dto.User;

/**
 * [NEW] 프론트엔드 연동을 위해 추가된 회원가입 요청 DTO
 * - 회원가입 시 필요한 정보를 받습니다.
 * - teamId가 null이면 무소속, 값이 있으면 해당 팀에 가입
 * - createTeamName이 있으면 새 팀을 생성하고 팀장이 됩니다.
 */
public record SignupRequest(
        String loginId, // 로그인 아이디
        String password, // 비밀번호
        String nickname, // 닉네임
        Long teamId, // 기존 팀 가입 시 팀 ID (optional)
        String createTeamName // 새 팀 생성 시 팀 이름 (optional)
) {
}
