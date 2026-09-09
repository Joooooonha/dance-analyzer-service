package SeSAC.Dance_Assessment.Storage;

import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * 로컬 저장소의 업로드/다운로드 엔드포인트 — <b>개발 전용</b>.
 *
 * <p>R2의 presigned URL을 흉내낸다. 인증(JWT 쿠키)을 요구하지 않는 대신
 * URL 자체의 HMAC 서명으로 접근을 통제한다 — presigned URL의 동작 방식이 그렇고,
 * 분석 서버(맥미니)는 로그인 세션이 없기 때문이다.
 */
@RestController
@RequiredArgsConstructor
@ConditionalOnProperty(name = "storage.type", havingValue = "local", matchIfMissing = true)
public class LocalStorageController {

    private final LocalStorageService storage;

    @PutMapping("/local-storage")
    public ResponseEntity<Void> upload(@RequestParam String key,
                                       @RequestParam String method,
                                       @RequestParam long exp,
                                       @RequestParam String sig,
                                       HttpServletRequest request) throws IOException {
        Path path = storage.verifyAndResolve(key, method, exp, sig);
        if (!"PUT".equals(method)) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
        }
        Files.createDirectories(path.getParent());
        try (InputStream in = request.getInputStream()) {
            Files.copy(in, path, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        }
        return ResponseEntity.ok().build();
    }

    @GetMapping("/local-storage")
    public ResponseEntity<Resource> download(@RequestParam String key,
                                             @RequestParam String method,
                                             @RequestParam long exp,
                                             @RequestParam String sig) {
        Path path = storage.verifyAndResolve(key, method, exp, sig);
        if (!"GET".equals(method) || !Files.exists(path)) {
            return ResponseEntity.notFound().build();
        }
        MediaType type = key.endsWith(".jpg") ? MediaType.IMAGE_JPEG
                : MediaType.parseMediaType("video/mp4");
        return ResponseEntity.ok().contentType(type).body(new FileSystemResource(path));
    }

    /** 서명 실패·만료를 403으로 돌려준다. */
    @ExceptionHandler({IllegalStateException.class, IllegalArgumentException.class})
    public ResponseEntity<String> onDenied(RuntimeException e) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN).body(e.getMessage());
    }
}
