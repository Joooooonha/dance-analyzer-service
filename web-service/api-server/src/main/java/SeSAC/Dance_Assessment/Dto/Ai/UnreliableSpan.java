package SeSAC.Dance_Assessment.Dto.Ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.ToString;

/**
 * 정렬 신뢰도가 낮아 <b>평가에서 제외한</b> 구간.
 *
 * <p>오차가 지나치게 크면 사용자가 틀린 것이 아니라 대응 시점을 잘못 찾은 것일 수
 * 있다. 그런 구간을 틀렸다고 지적하는 대신 따로 모아 "확인이 어려웠다"고 알린다.
 * 틀린 피드백을 주는 것보다 낫다는 판단이다.
 */
@Getter
@NoArgsConstructor
@ToString
public class UnreliableSpan {

    @JsonProperty("start_sec")
    private Double startSec;

    @JsonProperty("end_sec")
    private Double endSec;

    // 필드 이름이 `nFrames`면 안 된다.
    // Lombok이 `getNFrames()`를 만드는데 Jackson은 그 게터의 프로퍼티 이름을
    // "nframes"로 읽는다. 필드 이름 "nFrames"와 달라서 **둘을 서로 다른
    // 프로퍼티로 취급**하고, 다시 직렬화하면 `{"nframes":3, ..., "n_frames":3}`처럼
    // 같은 값이 두 번 나간다. 실제로 DB에 그렇게 저장된 것을 확인했다.
    // `numFrames`는 게터가 `getNumFrames()`라 프로퍼티 이름이 필드와 일치한다.
    @JsonProperty("n_frames")
    private Integer numFrames;
}
