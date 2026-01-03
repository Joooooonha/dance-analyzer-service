package SeSAC.Dance_Assessment.Domain;

import jakarta.persistence.*;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Getter
@NoArgsConstructor
public class AnalysisResult extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "result_id")
    private Long id;

    // 어떤 연습에 대한 분석 결과인지
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "log_id")
    private PracticeLog practiceLog;

    private Integer totalScore;

    @Lob
    private String feedbackContent;

    @Enumerated(EnumType.STRING)
    private AnalysisStatus status; // WAITING, PROGRESS, COMPLETE, FAIL (AI 분석 상태)

    // 분석 완료 시간은 실제로 분석이 끝나는 시점이라 단순 생성 시간이랑 구분해야 함
    private LocalDateTime analyzedDate;

    // ===== [NEW] 상세 분석 결과 =====
    // 비교 영상 URL (Python 서버)
    private String comparisonVideoUrl;

    // JSON 결과 URL
    private String jsonResultUrl;

    // 오류 관절 정보 (JSON 형태로 저장)
    @Lob
    private String topErrorJointsJson;

    // 오류 프레임 정보 (JSON 형태로 저장)
    @Lob
    private String topErrorFramesJson;

    @Builder
    public AnalysisResult(PracticeLog practiceLog, AnalysisStatus status) {
        this.practiceLog = practiceLog;
        this.status = status;
    }

    public void updateResult(Integer score, String feedback) {
        this.totalScore = score;
        this.feedbackContent = feedback;
        this.analyzedDate = LocalDateTime.now();
        this.status = AnalysisStatus.COMPLETED;
    }

    /**
     * [NEW] 상세 분석 결과 업데이트
     */
    public void updateDetailedResult(
            Integer score,
            String feedback,
            String comparisonVideoUrl,
            String jsonResultUrl,
            String topErrorJointsJson,
            String topErrorFramesJson) {
        this.totalScore = score;
        this.feedbackContent = feedback;
        this.comparisonVideoUrl = comparisonVideoUrl;
        this.jsonResultUrl = jsonResultUrl;
        this.topErrorJointsJson = topErrorJointsJson;
        this.topErrorFramesJson = topErrorFramesJson;
        this.analyzedDate = LocalDateTime.now();
        this.status = AnalysisStatus.COMPLETED;
    }
}
