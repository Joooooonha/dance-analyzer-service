package SeSAC.Dance_Assessment.Dto.Assignment;

import java.time.LocalDateTime;

public record AssignmentCreateRequest(
        Long targetVideoId,      // 팀장이 올린 영상 ID
        String title,
        LocalDateTime startDate, // 시작일
        LocalDateTime dueDate    // 마감일
) {}

