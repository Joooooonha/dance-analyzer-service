package SeSAC.Dance_Assessment.Presentation;

import SeSAC.Dance_Assessment.Dto.Ai.AiAnalysisResponse;
import SeSAC.Dance_Assessment.Dto.Video.VideoUploadRequestDto;
import SeSAC.Dance_Assessment.Service.AiClientService;
import SeSAC.Dance_Assessment.Service.VideoService;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;

@RestController
@RequiredArgsConstructor
public class VideoController {

    private final VideoService videoService;
    private final AiClientService aiClientService; // Ai 분석 서버로 요청

    @PostMapping("/videos")
    public ResponseEntity<?> uploadVideo(
            @RequestHeader("X-User-Id") Long userId,
            @ModelAttribute VideoUploadRequestDto requestDto) {
        try {
            // 1. DTO에 유저 ID 주입 (서비스에 전달하기 위해)
            requestDto.setUserId(userId);

            // 2. 서비스 호출
            Long videoId = videoService.uploadVideo(requestDto);

            // 3. 성공 시 200 OK 반환
            return ResponseEntity.ok(videoId);

        } catch (IOException e) {
            // 파일 저장 실패 시 500 에러
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body("업로드 실패: 서버 파일 저장 중 오류 (" + e.getMessage() + ")");
        } catch (IllegalArgumentException e) {
            // 유저 없음, 숙제 없음 등 잘못된 요청 시 400 에러
            return ResponseEntity.badRequest()
                    .body("업로드 실패: " + e.getMessage());
        }
    }

    /**
     * [MODIFIED] 영상 재생 API
     * 
     * 수정 이유:
     * - 기존에는 X-User-Id 헤더로만 사용자 인증을 받았음
     * - 그러나 프론트엔드에서 <video src="URL"> 태그를 사용할 때는
     * HTTP 헤더를 직접 설정할 수 없는 브라우저 제약이 있음
     * - 따라서 쿼리 파라미터(?userId=xxx)로도 인증을 받을 수 있도록 수정
     * - 헤더와 쿼리 파라미터 중 하나만 제공하면 작동함
     * 
     * 사용 예시:
     * - 헤더 방식: GET /videos/1 (Header: X-User-Id: 123)
     * - 쿼리 방식: GET /videos/1?userId=123 (프론트엔드 video 태그용)
     */
    @GetMapping("/videos/{videoId}")
    public ResponseEntity<Resource> playVideo(
            @PathVariable Long videoId,
            @RequestHeader(value = "X-User-Id", required = false) Long viewerIdHeader,
            @RequestParam(value = "userId", required = false) Long viewerIdParam) {
        // 헤더 또는 쿼리 파라미터에서 사용자 ID 추출
        Long viewerId = viewerIdHeader != null ? viewerIdHeader : viewerIdParam;

        // 둘 다 없으면 인증 실패
        if (viewerId == null) {
            return ResponseEntity.status(401).build(); // Unauthorized
        }

        try {
            Resource videoResource = videoService.playVideo(videoId, viewerId);

            return ResponseEntity.ok()
                    // 헤더 설정
                    .contentType(MediaType.parseMediaType("video/mp4"))
                    // (선택) 다운로드 대신 브라우저에서 바로 재생(inline)하도록 설정
                    .header(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"video.mp4\"")
                    .body(videoResource);

        } catch (IllegalStateException e) {
            // 권한 없음 (403 Forbidden)
            return ResponseEntity.status(403).build();
        } catch (IllegalArgumentException e) {
            // 영상 없음 or 파일 없음 (404 Not Found)
            return ResponseEntity.notFound().build();
        }
    }

    // 영상 삭제
    @DeleteMapping("/videos/{videoId}")
    public ResponseEntity<String> deleteVideo(@PathVariable Long videoId,
            @RequestHeader("X-User-Id") Long requesterId) {
        try {
            videoService.deleteVideo(videoId, requesterId);
            return ResponseEntity.ok("영상이 정상적으로 삭제되었습니다.");
        } catch (IllegalStateException e) {
            // 권한 없음
            return ResponseEntity.status(403).body("삭제 실패: " + e.getMessage());
        } catch (IllegalArgumentException e) {
            // 영상 없음
            return ResponseEntity.notFound().build();
        }
    }

    // 분석 요청 API 테스트
    // POST http://localhost:8080/api/videos/1/analyze
    // PracticeLog로 API 넘겨서 안 쓸 예정
    // TODO: 실제 사용 시에는 기준 영상과 연습 영상의 경로를 DB에서 조회해야 함
    @PostMapping("/videos/{videoId}/analyze")
    public ResponseEntity<AiAnalysisResponse> analyzeVideo(@PathVariable Long videoId) {

        // 테스트용 경로 (기준 영상과 연습 영상)
        String referenceVideoPath = "input/reference.mp4"; // Python 서버 내 경로
        String practiceVideoPath = "input/practice.mp4"; // Python 서버 내 경로

        // AI 서버에 요청 (새 시그니처: 두 개의 영상 경로)
        AiAnalysisResponse result = aiClientService.requestAnalysis(
                referenceVideoPath,
                practiceVideoPath);

        // 결과 반환
        return ResponseEntity.ok(result);
    }
}
