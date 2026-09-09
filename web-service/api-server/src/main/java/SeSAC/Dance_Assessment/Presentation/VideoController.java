package SeSAC.Dance_Assessment.Presentation;

import SeSAC.Dance_Assessment.Dto.Video.*;
import SeSAC.Dance_Assessment.Security.CurrentUserId;
import SeSAC.Dance_Assessment.Service.VideoService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URI;

/**
 * 영상 API.
 *
 * <p><b>업로드는 두 단계다.</b> 파일 바이트가 이 서버를 지나가지 않는다.
 *
 * <pre>
 * 1) POST /videos/upload-url   → 서명된 PUT URL 발급
 * 2) PUT  {uploadUrl}          → 브라우저가 저장소에 직접 업로드
 * 3) POST /videos/{id}/complete → 완료 통보 (여기서 연습 기록 생성)
 * </pre>
 */
@RestController
@RequiredArgsConstructor
public class VideoController {

    private final VideoService videoService;

    /** 1단계: 업로드 URL 발급. */
    @PostMapping("/videos/upload-url")
    public ResponseEntity<VideoUploadUrlResponse> createUploadUrl(
            @CurrentUserId Long userId,
            @RequestBody VideoUploadUrlRequest request) {
        return ResponseEntity.ok(videoService.createUploadUrl(userId, request));
    }

    /** 3단계: 업로드 완료 통보. */
    @PostMapping("/videos/{videoId}/complete")
    public ResponseEntity<VideoUploadResponse> completeUpload(
            @CurrentUserId Long userId,
            @PathVariable Long videoId,
            @RequestBody(required = false) VideoCompleteRequest request) {
        return ResponseEntity.ok(videoService.completeUpload(userId, videoId, request));
    }

    /**
     * 영상 재생 — 저장소의 서명된 URL로 <b>리다이렉트</b>한다.
     *
     * <p>파일을 이 서버가 직접 흘려보내지 않는 이유는 대역폭 때문이다.
     * 리다이렉트하면 브라우저가 저장소에서 바로 받아가고, EC2는 권한 판단만 한다.
     *
     * <p>{@code <video src>}에 이 주소를 그대로 쓰면 된다 — 브라우저가 쿠키를
     * 실어 보내고(인증), 302를 따라가 실제 영상을 받는다.
     */
    @GetMapping("/videos/{videoId}")
    public ResponseEntity<Void> playVideo(@PathVariable Long videoId,
                                          @CurrentUserId Long viewerId) {
        try {
            String url = videoService.createPlaybackUrl(videoId, viewerId);
            return ResponseEntity.status(HttpStatus.FOUND).location(URI.create(url)).build();
        } catch (IllegalStateException e) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
        } catch (IllegalArgumentException e) {
            return ResponseEntity.notFound().build();
        }
    }

    @DeleteMapping("/videos/{videoId}")
    public ResponseEntity<String> deleteVideo(@PathVariable Long videoId,
                                              @CurrentUserId Long requesterId) {
        try {
            videoService.deleteVideo(videoId, requesterId);
            return ResponseEntity.ok("영상이 정상적으로 삭제되었습니다.");
        } catch (IllegalStateException e) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN).body("삭제 실패: " + e.getMessage());
        } catch (IllegalArgumentException e) {
            return ResponseEntity.notFound().build();
        }
    }
}
