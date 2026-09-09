package SeSAC.Dance_Assessment.Storage;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.HexFormat;

/**
 * 로컬 디스크 구현 — <b>개발 전용</b>.
 *
 * <p>R2 자격증명 없이도 업로드·분석·조회 전 과정을 돌려보기 위한 것이다.
 * R2와 같은 계약(presigned URL)을 흉내내므로, 저장소를 R2로 바꿔도
 * 호출하는 쪽 코드는 그대로다.
 *
 * <p>URL은 HMAC으로 서명한다. 개발용이라도 키 문자열만 알면 아무 파일이나
 * 읽고 쓸 수 있게 두면, 이 구현이 실수로 배포됐을 때 그대로 구멍이 된다.
 */
@Slf4j
@Service
@ConditionalOnProperty(name = "storage.type", havingValue = "local", matchIfMissing = true)
public class LocalStorageService implements StorageService {

    private final Path root;
    private final String publicBaseUrl;
    private final byte[] signingKey;

    public LocalStorageService(
            @Value("${storage.local.dir:./storage-data}") String dir,
            @Value("${storage.local.base-url:http://localhost:8080}") String publicBaseUrl,
            @Value("${jwt.secret}") String secret) {
        this.root = Path.of(dir).toAbsolutePath().normalize();
        this.publicBaseUrl = publicBaseUrl;
        this.signingKey = secret.getBytes(StandardCharsets.UTF_8);
        try {
            Files.createDirectories(root);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        log.warn("[저장소] 로컬 디스크 사용 (개발용) — {}", root);
    }

    @Override
    public String createUploadUrl(String key, String contentType, Duration expiry) {
        return signedUrl(key, "PUT", expiry);
    }

    @Override
    public String createDownloadUrl(String key, Duration expiry) {
        return signedUrl(key, "GET", expiry);
    }

    @Override
    public void delete(String key) {
        try {
            Files.deleteIfExists(resolve(key));
        } catch (IOException e) {
            log.warn("[저장소] 삭제 실패 key={} : {}", key, e.getMessage());
        }
    }

    private String signedUrl(String key, String method, Duration expiry) {
        long exp = Instant.now().plus(expiry).getEpochSecond();
        String sig = sign(key, method, exp);
        // 경로에 /api가 붙는 이유: 모든 컨트롤러가 /api 아래로 옮겨졌다
        // (WebMvcConfig.configurePathMatch — 프론트엔드 SPA 라우팅과의 충돌 때문).
        //
        // 키를 경로가 아니라 **쿼리 파라미터**에 담는다. 키에는 슬래시가 들어 있는데
        // (`videos/1/abc.mp4`), 경로에 넣으려고 %2F로 인코딩하면 Tomcat이 기본
        // 설정에서 그 요청을 400으로 거부한다.
        return "%s/api/local-storage?key=%s&method=%s&exp=%d&sig=%s".formatted(
                publicBaseUrl,
                URLEncoder.encode(key, StandardCharsets.UTF_8),
                method, exp, sig);
    }

    String sign(String key, String method, long exp) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(signingKey, "HmacSHA256"));
            byte[] out = mac.doFinal((key + "|" + method + "|" + exp).getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(out);
        } catch (Exception e) {
            throw new IllegalStateException("서명 실패", e);
        }
    }

    /** 서명·만료를 검증한다. 통과하면 실제 파일 경로. */
    Path verifyAndResolve(String key, String method, long exp, String sig) {
        if (Instant.now().getEpochSecond() > exp) {
            throw new IllegalStateException("URL이 만료되었습니다.");
        }
        // 문자열 비교는 타이밍 공격에 취약하므로 상수 시간 비교를 쓴다.
        byte[] expected = sign(key, method, exp).getBytes(StandardCharsets.UTF_8);
        byte[] actual = sig == null ? new byte[0] : sig.getBytes(StandardCharsets.UTF_8);
        if (!java.security.MessageDigest.isEqual(expected, actual)) {
            throw new IllegalStateException("서명이 올바르지 않습니다.");
        }
        return resolve(key);
    }

    /**
     * 키를 실제 경로로 바꾼다.
     *
     * <p>{@code ../}가 섞인 키가 저장 디렉터리 밖을 가리키지 못하게 막는다.
     * 키는 서버가 만들지만, 검증 없이 신뢰할 이유는 없다.
     */
    private Path resolve(String key) {
        Path path = root.resolve(key).normalize();
        if (!path.startsWith(root)) {
            throw new IllegalArgumentException("잘못된 키입니다: " + key);
        }
        return path;
    }

    Path rootDir() {
        return root;
    }

    /** 개발 편의: base64 없이 바로 쓸 수 있는 짧은 식별자. */
    static String randomId() {
        byte[] b = new byte[9];
        new java.security.SecureRandom().nextBytes(b);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(b);
    }
}
