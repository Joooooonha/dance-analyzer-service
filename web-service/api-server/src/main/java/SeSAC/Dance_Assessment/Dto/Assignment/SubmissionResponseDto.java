package SeSAC.Dance_Assessment.Dto.Assignment;

import SeSAC.Dance_Assessment.Domain.PracticeLog;
import lombok.Getter;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@Getter
@NoArgsConstructor
public class SubmissionResponseDto {

    private Long logId; // 상세 페이지 이동을 위한 Key
    private Long id; // 팀원 ID
    private String NickName; // 팀원 이름 (User 테이블)
    private String videoStatus; // 영상 분석 상태 (WAITING, PROCESSING, COMPLETED, FAILED)
    private LocalDateTime submittedAt; // 제출 시간

    // Entity -> DTO 변환 생성자
    public SubmissionResponseDto(PracticeLog log) {
        this.logId = log.getId();

        // User 정보 매핑 (Null Check는 프로젝트 정책에 따라 추가)
        if (log.getUser() != null) {
            this.id = log.getUser().getId();
            this.NickName = log.getUser().getNickname(); // 혹은 getNickname()
        }

        // Video 정보 매핑
        if (log.getPracticeVideo() != null) {
            // analysisStatus가 null인 경우 "WAITING"으로 기본값 설정
            if (log.getPracticeVideo().getAnalysisStatus() != null) {
                this.videoStatus = log.getPracticeVideo().getAnalysisStatus().toString();
            } else {
                this.videoStatus = "WAITING";
            }
        }

        this.submittedAt = log.getCreatedAt();
    }
}
