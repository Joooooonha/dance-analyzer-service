package SeSAC.Dance_Assessment.Domain;

import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
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

    // [사용 안 함] 0~100 점수. 환산 상수가 임의값이라 절대값에 의미가 없어
    // 화면에서 제거했다. 컬럼은 남겨둔다 — 지우면 스키마 마이그레이션이 필요한데
    // 얻는 것이 없다. 새 코드에서 읽거나 쓰지 말 것.
    @Deprecated
    private Integer totalScore;

    @Lob
    private String feedbackContent;

    @Enumerated(EnumType.STRING)
    private AnalysisStatus status; // WAITING, PROGRESS, COMPLETE, FAIL (AI 분석 상태)

    // 분석 완료 시간은 실제로 분석이 끝나는 시점이라 단순 생성 시간이랑 구분해야 함
    private LocalDateTime analyzedDate;

    // ===== 결과물 =====
    // 저장소 객체 키. **URL이 아니라 키를 저장한다.**
    // 예전에는 분석 서버가 만든 URL을 그대로 저장했는데, 그 값이
    // `http://127.0.0.1:8000/...`이라 외부 브라우저에서는 절대 열리지 않았다.
    // 서명 URL은 만료되므로 저장해도 곧 무효가 된다 — 조회 시점에 새로 만든다.
    private String comparisonVideoKey;

    // ===== 구간 피드백 =====
    // 틀린 동작 구간의 총 개수. 점수를 대체하는 값이다.
    private Integer issueCount;

    // 상위 지적 구간 목록 (AiAnalysisResponse.topIssues를 JSON 그대로 보관).
    // 구간 구조가 앞으로 바뀔 수 있고 조회 조건으로 쓸 일이 없어 정규화하지 않는다.
    @Lob
    private String topIssuesJson;

    // 정렬 신뢰도가 낮아 평가하지 않은 구간
    @Lob
    private String unreliableSpansJson;

    // 위 구간을 제외한 이유 문구
    @Lob
    private String unreliableNote;

    // 채점률·검출률 등 품질 지표
    @Lob
    private String qualityJson;

    // 재촬영을 권할 만한 문제가 있을 때만 채워진다
    private String qualityWarning;

    /**
     * 두 영상을 맞춰 재생하기 위한 대응표: {@code [[연습 시각, 기준 시각], ...]} (초).
     *
     * <p>DTW가 찾은 프레임 대응을 0.1초 간격으로 추린 것이다. 이게 있으면 화면이
     * 원본 영상 두 개를 같은 안무 지점에 맞춰 돌릴 수 있다 — 서버에서 비교 영상을
     * 렌더링(분석 +60~90초)하지 않아도 된다. 30초 영상 기준 5KB 남짓.
     *
     * <p><b>{@code @Lob}을 쓰지 않는다.</b> Hibernate 6에서 {@code @Lob String}은
     * PostgreSQL의 {@code oid}(Large Object)로 매핑된다. 그러면 값이 테이블이 아니라
     * 별도 저장소에 들어가서, psql로 그냥 조회하면 JSON이 아니라 숫자 하나가 나오고
     * ({@code convert_from(lo_get(...))}로 읽어야 한다) 행을 지워도 실제 데이터는
     * 남는다. 위의 {@code @Lob} 필드들이 실제로 그렇게 저장돼 있다 — 고치려면
     * 데이터 이관이 필요해 그대로 두었고, 새 필드는 처음부터 {@code text}로 만든다.
     */
    @JdbcTypeCode(SqlTypes.LONGVARCHAR)
    private String syncMapJson;

    /**
     * 이번 분석 실행을 가리키는 표식. 진행 상황을 물어볼 때 대조한다.
     *
     * <p>분석 서버는 동시에 한 건만 돌려서 진행 상황도 한 건분만 들고 있다.
     * 대조하지 않으면 다른 사용자의 분석 진행률을 자기 것으로 보여주게 된다.
     */
    private String analysisJobId;

    @Builder
    public AnalysisResult(PracticeLog practiceLog, AnalysisStatus status) {
        this.practiceLog = practiceLog;
        this.status = status;
    }

    /**
     * 분석 실패를 기록한다.
     */
    public void markFailed(String reason) {
        this.feedbackContent = reason;
        this.analyzedDate = LocalDateTime.now();
        this.status = AnalysisStatus.FAILED;
    }

    /**
     * 분석 결과를 저장한다.
     *
     * <p>점수는 받지 않는다 — AI 서버가 더 이상 점수를 내지 않는다.
     */
    public void updateSegmentResult(
            Integer issueCount,
            String message,
            String comparisonVideoKey,
            String topIssuesJson,
            String unreliableSpansJson,
            String unreliableNote,
            String qualityJson,
            String qualityWarning,
            String syncMapJson) {
        this.issueCount = issueCount;
        this.feedbackContent = message;
        this.comparisonVideoKey = comparisonVideoKey;
        this.topIssuesJson = topIssuesJson;
        this.unreliableSpansJson = unreliableSpansJson;
        this.unreliableNote = unreliableNote;
        this.qualityJson = qualityJson;
        this.qualityWarning = qualityWarning;
        this.syncMapJson = syncMapJson;
        this.analyzedDate = LocalDateTime.now();
        this.status = AnalysisStatus.COMPLETED;
    }

    /**
     * 분석 요청을 접수했음을 표시한다.
     *
     * <p>이 시점에는 아직 분석 서버가 일을 시작하지 않았으므로 작업 표식이 없다.
     * <b>이전 실행의 표식은 지운다</b> — 남겨두면 재분석 대기 중에 지난번 진행률을
     * 지금 것으로 보여줄 수 있다.
     */
    public void markProcessing() {
        markProcessing(null);
    }

    /**
     * 분석 서버에 일을 맡기면서 이번 실행의 표식을 붙인다.
     */
    public void markProcessing(String jobId) {
        this.status = AnalysisStatus.PROCESSING;
        this.analysisJobId = jobId;
    }
}
