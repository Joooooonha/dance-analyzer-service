package SeSAC.Dance_Assessment.Presentation;

import SeSAC.Dance_Assessment.Dto.PracticeLog.AnalysisAcceptedResponse;
import SeSAC.Dance_Assessment.Dto.PracticeLog.AnalysisProgressResponse;
import SeSAC.Dance_Assessment.Dto.PracticeLog.PracticeLogDetailResponse;
import SeSAC.Dance_Assessment.Dto.PracticeLog.PracticeLogListResponse;
import SeSAC.Dance_Assessment.Dto.PracticeLog.TrimRangeRequest;
import SeSAC.Dance_Assessment.Service.PracticeLogService;
import SeSAC.Dance_Assessment.Security.CurrentUserId;
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

    // 연습 기록 목록 조회
    @GetMapping("/practice-logs")
    public ResponseEntity<Page<PracticeLogListResponse>> getMyLogs(
            @CurrentUserId Long userId,
            // size=10, sort=createdAt, DESC(최신순)을 기본값으로 설정
            @PageableDefault(size = 10, sort = "createdAt", direction = Sort.Direction.DESC) Pageable pageable) {

        Page<PracticeLogListResponse> result = practiceLogService.getMyPracticeLogs(userId, pageable);
        return ResponseEntity.ok(result);
    }

    /**
     * 연습 기록 상세 조회.
     *
     * <p><b>분석 진행 상황을 확인하는 폴링 대상이다.</b> {@code status}가
     * COMPLETED가 되면 구간 피드백이 채워진다.
     */
    @GetMapping("/practice-logs/{logId}")
    public ResponseEntity<PracticeLogDetailResponse> getLogDetail(
            @PathVariable Long logId,
            @CurrentUserId Long userId) {
        return ResponseEntity.ok(practiceLogService.getPracticeLogDetail(logId, userId));
    }

    /**
     * 분석 진행 단계 조회.
     *
     * <p>상세 조회와 <b>따로 둔다.</b> 진행률은 분석 서버에 물어봐야 알 수 있는데,
     * 그걸 상세 조회에 넣으면 분석 서버가 꺼진 동안 결과 화면이 통째로 열리지
     * 않는다. 이건 없어도 되는 부가 정보이므로 실패해도 상태만 돌려준다.
     */
    @GetMapping("/practice-logs/{logId}/progress")
    public ResponseEntity<AnalysisProgressResponse> getProgress(
            @PathVariable Long logId,
            @CurrentUserId Long userId) {
        return ResponseEntity.ok(practiceLogService.getAnalysisProgress(logId, userId));
    }

    /**
     * 안무 구간 지정.
     *
     * <p>프론트의 트림 UI에서 고른 시작/끝 시각을 저장한다. 영상을 실제로 자르지
     * 않고 타임스탬프만 보관하므로 화질 손실이 없고 즉시 끝난다.
     * 분석 요청 전에 호출하면 그 값이 분석에 반영된다.
     */
    @PatchMapping("/practice-logs/{logId}/trim")
    public ResponseEntity<PracticeLogDetailResponse> updateTrim(
            @PathVariable Long logId,
            @CurrentUserId Long userId,
            @RequestBody TrimRangeRequest request) {
        practiceLogService.updateTrimRange(logId, userId, request);
        return ResponseEntity.ok(practiceLogService.getPracticeLogDetail(logId, userId));
    }

    /**
     * 분석 시작.
     *
     * <p><b>결과를 기다리지 않고 202로 즉시 반환한다.</b> 분석에 실측 약 2분이
     * 걸려 HTTP 요청을 붙잡고 있을 수 없다. 클라이언트는 응답의
     * {@code pollUrl}을 폴링해 완료를 확인한다.
     */
    @PostMapping("/practice-logs/{logId}/analyze")
    public ResponseEntity<AnalysisAcceptedResponse> analyze(
            @PathVariable Long logId,
            @CurrentUserId Long userId) {
        AnalysisAcceptedResponse accepted = practiceLogService.requestAnalysis(logId, userId);
        return ResponseEntity.accepted().body(accepted);
    }
}
