package SeSAC.Dance_Assessment.Dto.Ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.ToString;

/**
 * 관절 오류 정보 DTO
 */
@Getter
@NoArgsConstructor
@ToString
public class JointErrorInfo {

    @JsonProperty("joint_name")
    private String jointName;

    @JsonProperty("joint_id")
    private Integer jointId;

    @JsonProperty("average_similarity")
    private Double averageSimilarity;

    @JsonProperty("severity")
    private String severity;
}
