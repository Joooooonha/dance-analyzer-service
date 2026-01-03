package SeSAC.Dance_Assessment.Dto.Ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.ToString;

/**
 * Python AI 서버 /upload 응답 DTO
 */
@Getter
@NoArgsConstructor
@ToString
public class AiUploadResponse {

    @JsonProperty("filename")
    private String filename;

    @JsonProperty("file_path")
    private String filePath;

    @JsonProperty("file_url")
    private String fileUrl;
}
