package SeSAC.Dance_Assessment.Dto.Ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.ToString;

import java.util.List;

/**
 * Python AI 서버 {@code POST /analyze} 응답 DTO.
 *
 * <p><b>{@code overall_score}가 없다.</b> 0~100 점수의 환산 상수가 임의값이라
 * 절대값에 의미가 없었기 때문이다. 대신 <b>틀린 동작 구간 개수</b>와 구간 목록을
 * 준다. UI에도 점수를 표시하지 않는다.
 */
@Getter
@NoArgsConstructor
@ToString
public class AiAnalysisResponse {

    @JsonProperty("status")
    private String status;

    /** 틀린 동작 구간 총 개수. 점수가 아니다. */
    @JsonProperty("issue_count")
    private Integer issueCount;

    /** 심각도 x 지속시간 순 상위 구간 */
    @JsonProperty("top_issues")
    private List<IssueInfo> topIssues;

    /** 평가하지 않은 구간 */
    @JsonProperty("unreliable_spans")
    private List<UnreliableSpan> unreliableSpans;

    /** 위 구간을 왜 제외했는지 사용자에게 보여줄 문구. 없으면 null. */
    @JsonProperty("unreliable_note")
    private String unreliableNote;

    @JsonProperty("quality")
    private AlignmentQuality quality;

    @JsonProperty("trim")
    private TrimEcho trim;

    /** 비교 영상을 업로드했는지. 키는 Spring이 안다(슬롯 방식과 같은 이유). */
    @JsonProperty("comparison_video_uploaded")
    private Boolean comparisonVideoUploaded;

    /**
     * 두 영상을 맞춰 재생하기 위한 대응표: {@code [[연습 시각, 기준 시각], ...]} (초).
     *
     * <p><b>비교 영상을 렌더링하는 대신 받는다.</b> 렌더링은 분석 시간을 60~90초
     * 더 쓰는데, 정작 사용자가 하고 싶은 건 "이 구간만 느리게 반복해서 보기"다.
     * 표를 받아두면 브라우저가 원본 영상 두 개를 직접 맞춰 돌릴 수 있어
     * 되감기·반복·배속이 전부 공짜가 되고 분석은 조금도 느려지지 않는다.
     *
     * <p>30초 영상 기준 300쌍 남짓(약 5KB).
     */
    @JsonProperty("sync_map")
    private List<List<Double>> syncMap;

    @JsonProperty("message")
    private String message;
}
