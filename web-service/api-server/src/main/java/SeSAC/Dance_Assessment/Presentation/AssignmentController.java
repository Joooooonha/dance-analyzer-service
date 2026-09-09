package SeSAC.Dance_Assessment.Presentation;

import SeSAC.Dance_Assessment.Dto.Assignment.AssignmentCreateRequest;
import SeSAC.Dance_Assessment.Dto.Assignment.AssignmentDetailResponse;
import SeSAC.Dance_Assessment.Dto.Assignment.AssignmentResponse;
import SeSAC.Dance_Assessment.Dto.Assignment.SubmissionResponseDto;
import SeSAC.Dance_Assessment.Dto.PracticeLog.PracticeLogDetailResponse;
import SeSAC.Dance_Assessment.Service.AssignmentService;
import SeSAC.Dance_Assessment.Security.CurrentUserId;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.nio.file.AccessDeniedException;
import java.util.List;

@RestController
@RequiredArgsConstructor
public class AssignmentController {

    private final AssignmentService assignmentService;

    // 숙제 생성 API
    @PostMapping("/assignments")
    public ResponseEntity<Long> createAssignment(
            @CurrentUserId Long userId,
            @RequestBody AssignmentCreateRequest request) {
        Long assignmentId = assignmentService.createAssignment(userId, request);
        return ResponseEntity.ok(assignmentId);
    }

    // 숙제 목록 조회(전체)
    @GetMapping("/assignments")
    public ResponseEntity<List<AssignmentResponse>> getAssignments(@CurrentUserId Long userId) {
        List<AssignmentResponse> responses = assignmentService.getMyTeamAssignments(userId);
        return ResponseEntity.ok(responses);
    }

    /**
     * [NEW] 숙제 상세 조회 API
     * GET /assignments/{id}
     * 
     * - 숙제 정보와 기준 영상 정보를 함께 반환
     * - 팀원이 숙제 제출 페이지에서 기준 영상을 확인할 때 사용
     */
    @GetMapping("/assignments/{id}")
    public ResponseEntity<AssignmentDetailResponse> getAssignment(
            @PathVariable Long id,
            @CurrentUserId Long userId) {
        AssignmentDetailResponse response = assignmentService.getAssignmentDetail(id, userId);
        return ResponseEntity.ok(response);
    }

    /**
     * [NEW] 숙제별 제출 현황 조회 API (팀장용)
     * GET /assignments/{id}/submissions
     * 
     * - 팀장만 조회 가능
     * - 팀원들의 제출 여부와 분석 상태를 확인
     */
    @GetMapping("/assignments/{id}/submissions")
    public ResponseEntity<List<SubmissionResponseDto>> getSubmissions(
            @PathVariable Long id,
            @CurrentUserId Long userId) throws AccessDeniedException {
        List<SubmissionResponseDto> submissions = assignmentService.getSubmissions(userId, id);
        return ResponseEntity.ok(submissions);
    }

    /**
     * [NEW] 내 제출 이력 조회 API
     * GET /assignments/{id}/my-submissions
     * 
     * - 해당 숙제에 내가 제출한 모든 기록 반환
     */
    @GetMapping("/assignments/{id}/my-submissions")
    public ResponseEntity<List<PracticeLogDetailResponse>> getMySubmissions(
            @PathVariable Long id,
            @CurrentUserId Long userId) {
        List<PracticeLogDetailResponse> submissions = assignmentService.getMySubmissions(userId, id);
        return ResponseEntity.ok(submissions);
    }
}
