package SeSAC.Dance_Assessment.Dto.Ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.ToString;

import java.util.List;

/**
 * Python AI 서버 /analyze 응답 DTO
 */
@Getter
@NoArgsConstructor
@ToString
public class AiAnalysisResponse {

    @JsonProperty("status")
    private String status;

    @JsonProperty("overall_score")
    private Double overallScore;

    @JsonProperty("total_frames")
    private Integer totalFrames;

    @JsonProperty("top_error_joints")
    private List<JointErrorInfo> topErrorJoints;

    @JsonProperty("top_error_frames")
    private List<FrameFeedbackInfo> topErrorFrames;

    @JsonProperty("comparison_video_url")
    private String comparisonVideoUrl;

    @JsonProperty("json_result_url")
    private String jsonResultUrl;

    @JsonProperty("message")
    private String message;
}