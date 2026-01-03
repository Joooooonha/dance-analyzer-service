package SeSAC.Dance_Assessment.Service;

import SeSAC.Dance_Assessment.Dto.Ai.AiAnalysisRequest;
import SeSAC.Dance_Assessment.Dto.Ai.AiAnalysisResponse;
import SeSAC.Dance_Assessment.Dto.Ai.AiUploadResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;

import java.io.IOException;

/**
 * Python AI 서버와 통신하는 서비스
 * 
 * 흐름:
 * 1. uploadVideo() - 영상 파일을 Python 서버에 업로드
 * 2. requestAnalysis() - 업로드된 파일 경로로 분석 요청
 * 3. analyzeVideos() - 위 두 단계를 통합한 편의 메서드
 */
@Slf4j
@Service
public class AiClientService {

    private final WebClient webClient;

    public AiClientService(@Value("${ai.server.url:http://localhost:8000}") String aiServerUrl) {
        this.webClient = WebClient.builder()
                .baseUrl(aiServerUrl)
                .build();
    }

    /**
     * 영상 파일을 Python AI 서버에 업로드
     * 
     * @param file 업로드할 영상 파일
     * @return 업로드 결과 (파일명, 경로, URL)
     */
    public AiUploadResponse uploadVideo(MultipartFile file) throws IOException {
        log.info("🚀 [Spring → Python] 영상 업로드: {}", file.getOriginalFilename());

        // MultipartFile을 WebClient에서 사용 가능한 형태로 변환
        MultipartBodyBuilder builder = new MultipartBodyBuilder();
        builder.part("file", new ByteArrayResource(file.getBytes()) {
            @Override
            public String getFilename() {
                return file.getOriginalFilename();
            }
        }).contentType(MediaType.parseMediaType(
                file.getContentType() != null ? file.getContentType() : "video/mp4"));

        AiUploadResponse response = webClient.post()
                .uri("/upload")
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(BodyInserters.fromMultipartData(builder.build()))
                .retrieve()
                .bodyToMono(AiUploadResponse.class)
                .block();

        log.info("✅ [Python → Spring] 업로드 완료: {}", response);
        return response;
    }

    /**
     * 분석 요청
     * 
     * @param referenceVideoPath 기준 영상 경로 (Python 서버 내 경로)
     * @param practiceVideoPath  연습 영상 경로 (Python 서버 내 경로)
     * @return 분석 결과
     */
    public AiAnalysisResponse requestAnalysis(String referenceVideoPath, String practiceVideoPath) {
        log.info("🚀 [Spring → Python] 분석 요청");
        log.info("   기준 영상: {}", referenceVideoPath);
        log.info("   연습 영상: {}", practiceVideoPath);

        AiAnalysisRequest request = AiAnalysisRequest.builder()
                .referenceVideoPath(referenceVideoPath)
                .practiceVideoPath(practiceVideoPath)
                .similarityThreshold(0.7)
                .generateVideo(true)
                .topErrorFrames(10)
                .build();

        AiAnalysisResponse response = webClient.post()
                .uri("/analyze")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(request)
                .retrieve()
                .bodyToMono(AiAnalysisResponse.class)
                .block();

        log.info("✅ [Python → Spring] 분석 완료: 점수 = {}%", response.getOverallScore());
        return response;
    }

    /**
     * 영상 분석 통합 메서드
     * 
     * 두 영상을 업로드하고 분석 결과를 반환합니다.
     * 
     * @param referenceVideo 기준 영상 파일
     * @param practiceVideo  연습 영상 파일
     * @return 분석 결과
     */
    public AiAnalysisResponse analyzeVideos(MultipartFile referenceVideo, MultipartFile practiceVideo)
            throws IOException {

        log.info("========================================");
        log.info("🎬 춤 동작 분석 시작");
        log.info("========================================");

        // 1. 기준 영상 업로드
        log.info("[1/3] 기준 영상 업로드 중...");
        AiUploadResponse refUpload = uploadVideo(referenceVideo);

        // 2. 연습 영상 업로드
        log.info("[2/3] 연습 영상 업로드 중...");
        AiUploadResponse pracUpload = uploadVideo(practiceVideo);

        // 3. 분석 요청
        log.info("[3/3] 분석 요청 중...");
        AiAnalysisResponse result = requestAnalysis(
                refUpload.getFilePath(),
                pracUpload.getFilePath());

        log.info("========================================");
        log.info("🎉 분석 완료! 점수: {}%", result.getOverallScore());
        log.info("========================================");

        return result;
    }
}