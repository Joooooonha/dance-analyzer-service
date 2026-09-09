package SeSAC.Dance_Assessment.Dto.Ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.ToString;

/**
 * 분석 품질 지표.
 *
 * <p><b>여기에 "정렬이 맞았는지"를 알려주는 값은 없다.</b> 그것을 추정하려고
 * 신뢰도 신호 5종을 시험했지만 전부 정렬 오차를 예측하지 못했다(상관 0.03~0.26).
 * 정렬 실패가 "불확실한 매칭"이 아니라 "확신에 찬 오답"으로 나타나기 때문이다.
 * 없는 능력을 있는 것처럼 UI에 표시하지 말 것.
 *
 * <p>{@code warning}은 <b>관절 검출 실패율</b>에만 반응한다 — 이건 직접 측정되는
 * 값이다. 임계값(30%)은 잠정값이며 사용자 체감과의 관계는 아직 미측정이다.
 */
@Getter
@NoArgsConstructor
@ToString
public class AlignmentQuality {

    /** DTW 경로 중 실제로 채점된 대응쌍 비율 */
    @JsonProperty("scored_pct")
    private Double scoredPct;

    @JsonProperty("mean_error_deg")
    private Double meanErrorDeg;

    @JsonProperty("median_error_deg")
    private Double medianErrorDeg;

    @JsonProperty("p90_error_deg")
    private Double p90ErrorDeg;

    @JsonProperty("reference_unusable_frame_pct")
    private Double referenceUnusableFramePct;

    @JsonProperty("practice_unusable_frame_pct")
    private Double practiceUnusableFramePct;

    @JsonProperty("reference_joint_valid_ratio")
    private Double referenceJointValidRatio;

    @JsonProperty("practice_joint_valid_ratio")
    private Double practiceJointValidRatio;

    /** 두 영상의 고정 시간 차이(초). 녹화 시작 시점 차이라 정상적인 값이다. */
    @JsonProperty("global_offset_sec")
    private Double globalOffsetSec;

    /** 재촬영을 권할 만한 문제가 있을 때만 채워진다. 없으면 null. */
    @JsonProperty("warning")
    private String warning;
}
