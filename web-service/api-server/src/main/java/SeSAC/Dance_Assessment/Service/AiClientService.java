package SeSAC.Dance_Assessment.Service;

import SeSAC.Dance_Assessment.Dto.Ai.AiAnalysisRequest;
import SeSAC.Dance_Assessment.Dto.Ai.AiAnalysisResponse;
import SeSAC.Dance_Assessment.Dto.Ai.AiProgressResponse;
import SeSAC.Dance_Assessment.Service.AnalysisResultWriter.AnalysisJob;
import io.netty.channel.ChannelOption;
import io.netty.handler.timeout.ReadTimeoutHandler;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;

import java.time.Duration;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

/**
 * 맥미니의 분석 서버와 통신한다.
 *
 * <p><b>영상 파일은 이 경로로 흐르지 않는다.</b> Spring은 저장소의 서명된 URL만
 * 넘기고, 분석 서버가 저장소에서 직접 받아 직접 올린다. 덕분에
 * <ul>
 *   <li>EC2가 100MB 영상을 중계하지 않는다</li>
 *   <li>맥미니에 저장소 자격증명을 두지 않아도 된다 — 짧은 URL만 받는다</li>
 * </ul>
 *
 * <p>분석은 오래 걸린다(실측 약 70초, 비교 영상까지 만들면 더). WebClient 기본
 * 설정으로는 응답 타임아웃에 걸릴 수 있어 명시적으로 길게 잡는다. 호출부는 반드시
 * 비동기({@code AsyncAnalysisService})에서 부를 것.
 */
@Slf4j
@Service
public class AiClientService {

    private static final Duration ANALYZE_TIMEOUT = Duration.ofMinutes(10);
    private static final int CONNECT_TIMEOUT_MS = 10_000;
    private static final int MAX_IN_MEMORY_BYTES = 16 * 1024 * 1024;

    /**
     * 진행 상황 조회 타임아웃. <b>짧아야 한다.</b>
     *
     * <p>이건 화면 폴링에 딸려 오는 부가 정보다. 분석 서버가 응답하지 않을 때
     * 여기서 오래 기다리면, 진행률을 보여주려다 오히려 화면이 멈춘다.
     */
    private static final Duration PROGRESS_TIMEOUT = Duration.ofSeconds(3);

    private final WebClient webClient;

    public AiClientService(@Value("${ai.server.url:http://localhost:8000}") String aiServerUrl) {
        HttpClient httpClient = HttpClient.create()
                .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, CONNECT_TIMEOUT_MS)
                .responseTimeout(ANALYZE_TIMEOUT)
                .doOnConnected(conn -> conn.addHandlerLast(
                        new ReadTimeoutHandler(ANALYZE_TIMEOUT.toSeconds(), TimeUnit.SECONDS)));

        this.webClient = WebClient.builder()
                .baseUrl(aiServerUrl)
                .clientConnector(new ReactorClientHttpConnector(httpClient))
                .codecs(c -> c.defaultCodecs().maxInMemorySize(MAX_IN_MEMORY_BYTES))
                .build();
    }

    /**
     * 분석을 요청한다.
     *
     * <p><b>트랜잭션 밖에서 부른다.</b> 3분 넘게 걸리는 호출이라 DB 커넥션을
     * 붙잡고 있으면 안 된다 — 그래서 엔티티가 아니라 값만 담은
     * {@link AnalysisJob}을 받는다.
     *
     * @param job   영상 URL·구간·업로드 슬롯
     * @param jobId 진행 상황을 조회할 때 대조할 작업 표식
     */
    public AiAnalysisResponse requestAnalysis(AnalysisJob job, String jobId) {
        AiAnalysisRequest request = AiAnalysisRequest.builder()
                .jobId(jobId)
                .referenceVideoUrl(job.referenceDownloadUrl())
                .practiceVideoUrl(job.practiceDownloadUrl())
                .referenceStartSec(job.referenceStartSec())
                .referenceEndSec(job.referenceEndSec())
                .practiceStartSec(job.practiceStartSec())
                .practiceEndSec(job.practiceEndSec())
                .topIssues(job.imageUploadUrls().size())
                .generateImages(true)
                // 비교 영상은 만들지 않는다. 렌더링에 60~90초가 더 드는데,
                // 응답의 sync_map으로 화면이 원본 두 개를 맞춰 돌릴 수 있어
                // 결과물이 오히려 낫다(되감기·반복·배속이 된다).
                .generateVideo(false)
                .imageUploadUrls(job.imageUploadUrls())
                .build();

        log.info("[Spring -> 분석서버] 구간: 기준 {}~{}, 연습 {}~{}",
                request.getReferenceStartSec(), request.getReferenceEndSec(),
                request.getPracticeStartSec(), request.getPracticeEndSec());

        AiAnalysisResponse response = webClient.post()
                .uri("/analyze")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(request)
                .retrieve()
                .bodyToMono(AiAnalysisResponse.class)
                .block(ANALYZE_TIMEOUT);

        if (response != null) {
            log.info("[분석서버 -> Spring] 지적 구간 {}개, 채점률 {}%",
                    response.getIssueCount(),
                    response.getQuality() != null ? response.getQuality().getScoredPct() : null);
            if (response.getTrim() != null && !Boolean.TRUE.equals(response.getTrim().getApplied())) {
                log.info("   (구간 미지정으로 분석됨 — 시작 시각을 주면 정확도가 오른다)");
            }
        }
        return response;
    }

    /**
     * 지금 분석 서버가 돌고 있는 작업의 진행 단계.
     *
     * <p><b>실패해도 되는 조회다.</b> 닿지 못하면 빈 값을 돌려준다 — 진행률은
     * 없어도 되는 정보이고, 이것 때문에 화면이 깨져서는 안 된다.
     *
     * <p>호출부는 반환된 {@code jobId}가 자기 작업의 것인지 반드시 확인할 것.
     * 분석 서버는 진행 상황을 한 건분만 들고 있어서, 확인하지 않으면 다른
     * 사용자의 진행률을 보여주게 된다.
     */
    public Optional<AiProgressResponse> fetchProgress() {
        try {
            return Optional.ofNullable(webClient.get()
                    .uri("/progress")
                    .retrieve()
                    .bodyToMono(AiProgressResponse.class)
                    .block(PROGRESS_TIMEOUT));
        } catch (Exception e) {
            log.debug("[진행 조회 실패] {}", e.getMessage());
            return Optional.empty();
        }
    }
}
