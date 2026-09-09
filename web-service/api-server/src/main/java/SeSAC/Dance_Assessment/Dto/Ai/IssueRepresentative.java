package SeSAC.Dance_Assessment.Dto.Ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.ToString;

/**
 * 지적 구간을 대표하는 프레임 (구간 안에서 오차가 가장 큰 지점).
 *
 * <p>{@code practiceSec} / {@code referenceSec}로 <b>양쪽 영상을 각각 그 시점으로
 * 점프</b>시킬 수 있다. 두 값이 다른 것이 정상이다 — 같은 동작이 두 영상에서
 * 서로 다른 시각에 나타나기 때문에 DTW로 정렬하는 것이다.
 */
@Getter
@NoArgsConstructor
@ToString
public class IssueRepresentative {

    @JsonProperty("practice_frame")
    private Integer practiceFrame;

    @JsonProperty("practice_sec")
    private Double practiceSec;

    @JsonProperty("reference_frame")
    private Integer referenceFrame;

    @JsonProperty("reference_sec")
    private Double referenceSec;

    @JsonProperty("frame_error_deg")
    private Double frameErrorDeg;
}
