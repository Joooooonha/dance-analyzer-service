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
        Long targetVideoId,
        String targetVideoPath // [NEW] 기준 영상 재생을 위한 경로
) {
    public static AssignmentDetailResponse from(Assignment assignment) {
        return new AssignmentDetailResponse(
                assignment.getId(),
                assignment.getTitle(),
                assignment.getStartDate(),
                assignment.getDueDate(),
                assignment.getWriter().getNickname(),
                assignment.getTargetVideo().getId(),
                assignment.getTargetVideo().getVideoPath());
    }
}
