package SeSAC.Dance_Assessment.Dto.User;

/**
 * [NEW] 프론트엔드 연동을 위해 추가된 로그인 요청 DTO
 */
public record LoginRequest(
        String loginId,
        String password) {
}
