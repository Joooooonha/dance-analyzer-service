package SeSAC.Dance_Assessment.Domain;

/**
 * 계정이 어디서 왔는지.
 *
 * <p>{@link #LOCAL}은 <b>개발 환경 전용</b>이다. 소셜 로그인만 두면 로컬에서
 * 개발할 때마다 실제 카카오/네이버 로그인을 거쳐야 해서 불편하므로 남겨두되,
 * 운영 프로파일에서는 로그인 경로 자체를 막는다. 덕분에 운영에는 비밀번호가
 * 아예 저장되지 않는다.
 */
public enum AuthProvider {
    LOCAL,
    KAKAO,
    NAVER;

    public static AuthProvider fromRegistrationId(String registrationId) {
        return valueOf(registrationId.toUpperCase());
    }
}
