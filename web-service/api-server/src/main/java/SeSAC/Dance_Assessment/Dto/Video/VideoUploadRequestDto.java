package SeSAC.Dance_Assessment.Dto.Video;

import SeSAC.Dance_Assessment.Domain.VideoType;
import lombok.Data;
import org.springframework.web.multipart.MultipartFile;

@Data // 파일 저장시 @ModelAttribute 바인딩을 위해 record 말고 class-@Data 구조 선택
public class VideoUploadRequestDto {
    private String title;
    private VideoType type;
    private MultipartFile file;

    private Long assignmentId;
    private Long userId;

    // [NEW] 자율 연습 시 기준 영상 ID (숙제 제출이 아닌 경우 사용)
    private Long referenceVideoId;
}
