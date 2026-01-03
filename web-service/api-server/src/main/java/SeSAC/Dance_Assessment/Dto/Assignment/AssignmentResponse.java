package SeSAC.Dance_Assessment.Dto.Assignment;

import SeSAC.Dance_Assessment.Domain.Assignment;

import java.time.LocalDateTime;

public record AssignmentResponse(
        Long assignmentId,
        String title,
        LocalDateTime startDate,
        LocalDateTime dueDate,
        String writerName,    // 숙제 낸 사람 이름
        Long targetVideoId    // 기준 영상 ID (프론트에서 썸네일 보여줄 때 필요)
) {
    // Entity -> DTO 변환 메서드
    public static AssignmentResponse from(Assignment assignment) {
        return new AssignmentResponse(
                assignment.getId(),
                assignment.getTitle(),
                assignment.getStartDate(),
                assignment.getDueDate(),
                assignment.getWriter().getNickname(), // User 엔티티에 name이 있다고 가정
                assignment.getTargetVideo().getId()
        );
    }
}
