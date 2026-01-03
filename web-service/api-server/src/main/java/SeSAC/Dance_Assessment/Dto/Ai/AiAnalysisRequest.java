package SeSAC.Dance_Assessment.Dto.Ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * Python AI 서버 /analyze 요청 DTO
 */
@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AiAnalysisRequest {

    @JsonProperty("reference_video_path")
    private String referenceVideoPath;

    @JsonProperty("practice_video_path")
    private String practiceVideoPath;

    @JsonProperty("similarity_threshold")
    @Builder.Default
    private Double similarityThreshold = 0.7;

    @JsonProperty("generate_video")
    @Builder.Default
    private Boolean generateVideo = true;

    @JsonProperty("top_error_frames")
    @Builder.Default
    private Integer topErrorFrames = 10;
}
