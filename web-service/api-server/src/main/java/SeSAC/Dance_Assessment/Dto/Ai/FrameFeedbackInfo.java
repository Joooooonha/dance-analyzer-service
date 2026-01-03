package SeSAC.Dance_Assessment.Dto.Ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.ToString;

import java.util.List;

/**
 * 프레임별 피드백 정보 DTO
 */
@Getter
@NoArgsConstructor
@ToString
public class FrameFeedbackInfo {

    @JsonProperty("frame_number")
    private Integer frameNumber;

    @JsonProperty("timestamp_sec")
    private Double timestampSec;

    @JsonProperty("error_joints")
    private List<String> errorJoints;

    @JsonProperty("average_similarity")
    private Double averageSimilarity;

    @JsonProperty("comparison_image_url")
    private String comparisonImageUrl;
}
