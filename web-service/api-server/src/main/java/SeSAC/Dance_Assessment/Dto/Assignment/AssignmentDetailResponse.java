package SeSAC.Dance_Assessment.Dto.Assignment;

import SeSAC.Dance_Assessment.Domain.Assignment;

import java.time.LocalDateTime;

/**
 * [NEW] 숙제 상세 조회용 응답 DTO
 * - 기존 AssignmentResponse에 기준 영상 경로 정보 추가
 */
public record AssignmentDetailResponse(
        Long assignmentId,
        String title,
        LocalDateTime startDate,
        LocalDateTime dueDate,
        String writerName,
        Long targetVideoId
        // 영상 경로는 내려주지 않는다. 서버 내부 저장 위치는 클라이언트가 알 필요가
        // 없고, 알려주면 그 자체가 정보 노출이다. 재생은 GET /videos/{id}로 한다.
) {
    public static AssignmentDetailResponse from(Assignment assignment) {
        return new AssignmentDetailResponse(
                assignment.getId(),
                assignment.getTitle(),
                assignment.getStartDate(),
                assignment.getDueDate(),
                assignment.getWriter().getNickname(),
                assignment.getTargetVideo().getId());
    }
}
