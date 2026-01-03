package SeSAC.Dance_Assessment.Presentation;

import SeSAC.Dance_Assessment.Dto.Ai.AiAnalysisResponse;
import SeSAC.Dance_Assessment.Dto.PracticeLog.PracticeLogDetailResponse;
import SeSAC.Dance_Assessment.Dto.PracticeLog.PracticeLogListResponse;
import SeSAC.Dance_Assessment.Service.PracticeLogService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequiredArgsConstructor
public class PracticeLogController {

    private final PracticeLogService practiceLogService;

    // Header: X-User-Id = 1
    // 연습 기록 목록 조회
    @GetMapping("/practice-logs")
    public ResponseEntity<Page<PracticeLogListResponse>> getMyLogs(
            @RequestHeader("X-User-Id") Long userId,
            // size=10, sort=createdDate, DESC(최신순)을 기본값으로 설정
            @PageableDefault(size = 10, sort = "createdAt", direction = Sort.Direction.DESC) Pageable pageable) {

        Page<PracticeLogListResponse> result = practiceLogService.getMyPracticeLogs(userId, pageable);
        return ResponseEntity.ok(result);
    }

    /**
     * [NEW] 연습 기록 상세 조회 API
     * GET /practice-logs/{logId}
     * 
     * - 분석 결과(점수, 피드백)를 포함한 상세 정보 반환
     * - 프론트엔드 분석 결과 페이지에서 사용
     */
    @GetMapping("/practice-logs/{logId}")
    public ResponseEntity<PracticeLogDetailResponse> getLogDetail(
            @PathVariable Long logId,
            @RequestHeader("X-User-Id") Long userId) {
        PracticeLogDetailResponse response = practiceLogService.getPracticeLogDetail(logId, userId);
        return ResponseEntity.ok(response);
    }

    // 코드 다시 보기
    // 분석 API가 Video에서 PracticeLog로 넘어옴
    @PostMapping("/practice-logs/{logId}/analyze")
    public ResponseEntity<AiAnalysisResponse> analyze(@PathVariable Long logId,
            @RequestHeader("X-User-Id") Long userId) {
        AiAnalysisResponse result = practiceLogService.analyzePracticeLog(logId, userId);
        return ResponseEntity.ok(result);
    }
}