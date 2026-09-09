package SeSAC.Dance_Assessment.Storage;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.S3Configuration;
import software.amazon.awssdk.services.s3.model.DeleteObjectRequest;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.GetObjectPresignRequest;
import software.amazon.awssdk.services.s3.presigner.model.PutObjectPresignRequest;

import jakarta.annotation.PreDestroy;
import java.net.URI;
import java.time.Duration;

/**
 * Cloudflare R2 구현. S3 호환 API라 AWS SDK를 그대로 쓴다.
 *
 * <p>R2를 고른 이유는 <b>egress(내려받기) 요금이 없어서</b>다. 이 서비스에서
 * 가장 큰 트래픽이 맥미니의 영상 다운로드와 사용자의 결과물 조회인데, S3였다면
 * 그 둘이 곧바로 비용이 된다.
 */
@Slf4j
@Service
@ConditionalOnProperty(name = "storage.type", havingValue = "r2")
public class R2StorageService implements StorageService {

    private final String bucket;
    private final S3Client client;
    private final S3Presigner presigner;

    public R2StorageService(
            @Value("${storage.r2.bucket}") String bucket,
            @Value("${storage.r2.endpoint}") String endpoint,
            @Value("${storage.r2.access-key}") String accessKey,
            @Value("${storage.r2.secret-key}") String secretKey) {

        this.bucket = bucket;
        var credentials = StaticCredentialsProvider.create(
                AwsBasicCredentials.create(accessKey, secretKey));

        // R2는 리전 개념이 없지만 SDK가 값을 요구한다. "auto"가 R2의 관례다.
        Region region = Region.of("auto");

        // path-style을 강제한다. 가상 호스트 방식(bucket.endpoint)은 R2에서
        // 기대대로 동작하지 않는다.
        S3Configuration config = S3Configuration.builder()
                .pathStyleAccessEnabled(true)
                .build();

        this.client = S3Client.builder()
                .endpointOverride(URI.create(endpoint))
                .credentialsProvider(credentials)
                .region(region)
                .serviceConfiguration(config)
                .build();

        this.presigner = S3Presigner.builder()
                .endpointOverride(URI.create(endpoint))
                .credentialsProvider(credentials)
                .region(region)
                .serviceConfiguration(config)
                .build();

        log.info("[저장소] R2 사용 — bucket={}", bucket);
    }

    @Override
    public String createUploadUrl(String key, String contentType, Duration expiry) {
        PutObjectRequest put = PutObjectRequest.builder()
                .bucket(bucket)
                .key(key)
                .contentType(contentType)
                .build();

        return presigner.presignPutObject(PutObjectPresignRequest.builder()
                .signatureDuration(expiry)
                .putObjectRequest(put)
                .build()).url().toString();
    }

    @Override
    public String createDownloadUrl(String key, Duration expiry) {
        GetObjectRequest get = GetObjectRequest.builder()
                .bucket(bucket)
                .key(key)
                .build();

        return presigner.presignGetObject(GetObjectPresignRequest.builder()
                .signatureDuration(expiry)
                .getObjectRequest(get)
                .build()).url().toString();
    }

    @Override
    public void delete(String key) {
        try {
            client.deleteObject(DeleteObjectRequest.builder().bucket(bucket).key(key).build());
        } catch (Exception e) {
            // 파일이 이미 없어도 DB 정리는 진행돼야 한다.
            log.warn("[저장소] 삭제 실패 key={} : {}", key, e.getMessage());
        }
    }

    @PreDestroy
    void close() {
        presigner.close();
        client.close();
    }
}
