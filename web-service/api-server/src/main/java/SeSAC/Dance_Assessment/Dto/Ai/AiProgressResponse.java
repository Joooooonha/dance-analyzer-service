package SeSAC.Dance_Assessment.Dto.Ai;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.ToString;

/**
 * Python AI 서버 {@code GET /progress} 응답 DTO.
 *
 * <p>분석은 3분 가까이 걸리는데 그동안 밖으로 나가는 신호가 없어, 사용자
 * 입장에서는 멈춘 것과 구분되지 않았다. 이 응답은 <b>지금 실제로 어느 단계를
 * 돌고 있는지</b>를 알려준다.
 *
 * <p><b>단계 전환은 실제 사건이고 퍼센트는 추정이다.</b> 한 단계 안에서 얼마나
 * 진행됐는지는 알 수 없으므로 그 단계의 시작({@code pct})과 끝({@code nextPct})을
 * 함께 준다. 그 사이를 어떻게 보여줄지는 화면이 정한다.
 */
@Getter
@NoArgsConstructor
@ToString
@JsonIgnoreProperties(ignoreUnknown = true)
public class AiProgressResponse {

    /** idle | running | done | failed */
    @JsonProperty("state")
    private String state;

    /** 요청 때 붙여 보낸 작업 표식. 다르면 남의 분석이므로 무시해야 한다. */
    @JsonProperty("job_id")
    private String jobId;

    /** extract_reference 같은 기계용 단계 이름 */
    @JsonProperty("stage")
    private String stage;

    /** "기준 영상 분석 중" 같은 사용자용 문구 */
    @JsonProperty("label")
    private String label;

    /** 현재 단계가 시작되는 지점(%) */
    @JsonProperty("pct")
    private Double pct;

    /** 현재 단계가 끝나는 지점(%) */
    @JsonProperty("next_pct")
    private Double nextPct;

    @JsonProperty("stage_elapsed_sec")
    private Double stageElapsedSec;

    @JsonProperty("elapsed_sec")
    private Double elapsedSec;
}
