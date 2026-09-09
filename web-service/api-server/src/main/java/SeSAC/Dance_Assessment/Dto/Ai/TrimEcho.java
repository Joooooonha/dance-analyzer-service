package SeSAC.Dance_Assessment.Dto.Ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.ToString;

/**
 * 요청한 안무 구간이 실제로 적용됐는지 확인용.
 *
 * <p>{@code applied}는 <b>양쪽 시작 시각이 모두 주어졌을 때만</b> true다.
 * 한쪽만 주면 두 영상 사이의 전역 오프셋이 남아 좁은 밴드를 쓸 수 없으므로,
 * AI 서버가 넓은 밴드로 되돌린다. 프론트에서 "구간을 지정하면 정확해집니다"를
 * 안내할 때 이 값을 근거로 쓸 것.
 */
@Getter
@NoArgsConstructor
@ToString
public class TrimEcho {

    @JsonProperty("applied")
    private Boolean applied;

    @JsonProperty("reference_start_sec")
    private Double referenceStartSec;

    @JsonProperty("reference_end_sec")
    private Double referenceEndSec;

    @JsonProperty("practice_start_sec")
    private Double practiceStartSec;

    @JsonProperty("practice_end_sec")
    private Double practiceEndSec;

    @JsonProperty("note")
    private String note;
}
