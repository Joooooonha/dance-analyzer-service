package SeSAC.Dance_Assessment.Service;

import SeSAC.Dance_Assessment.Domain.*;
import SeSAC.Dance_Assessment.Dto.Video.VideoUploadRequestDto;
import SeSAC.Dance_Assessment.Infrastructure.AssignmentRepository;
import SeSAC.Dance_Assessment.Infrastructure.PracticeLogRepository;
import SeSAC.Dance_Assessment.Infrastructure.UserRepository;
import SeSAC.Dance_Assessment.Infrastructure.VideoRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.util.UUID;

@Service
@RequiredArgsConstructor // Autowired 대신 의존성 주임
@Transactional(readOnly = true) // 조회만 허용
public class VideoService {

    // @RequiredArgsConstructor 어노테이션으로 lombok이 생성자 만들어서 final 필드에 의존성 자동 주입받도록 함
    private final VideoRepository videoRepository;
    private final UserRepository userRepository;
    private final PracticeLogRepository practiceLogRepository;
    private final AssignmentRepository assignmentRepository;
    private final AsyncAnalysisService asyncAnalysisService; // [NEW] 비동기 분석 서비스

    private final String UPLOAD_DIRECTORY = "/Users/parkjooha/SeSAC/Project/자유 주제 개인 프로젝트Dance_Assessment/VideoUpload/";

    @Transactional
    public Long uploadVideo(VideoUploadRequestDto dto) throws IOException {

        // 유저 조회
        User user = userRepository.findById(dto.getUserId())
                .orElseThrow(() -> new IllegalArgumentException("존재하지 않는 사용자입니다."));

        // 유효성 검사
        MultipartFile multipartFile = dto.getFile();
        if (multipartFile.isEmpty()) {
            throw new IllegalArgumentException("파일이 전송되지 않았습니다.");
        }

        // 파일 저장
        String originalFilename = multipartFile.getOriginalFilename();
        String storeFileName = UUID.randomUUID() + "_" + originalFilename;
        String fullPath = UPLOAD_DIRECTORY + storeFileName;

        File dest = new File(fullPath);
        if (!dest.getParentFile().exists()) {
            dest.getParentFile().mkdirs(); // 폴더가 없으면 생성
        }
        multipartFile.transferTo(dest);

        VideoType videoType = dto.getType() != null ? dto.getType() : VideoType.PRACTICE;
        // Video 엔티티 생성 및 저장
        // VideoType은 DTO에 없다면 PRACTICE로 고정하거나 DTO에 필드 추가)
        Video video = Video.builder()
                .uploader(user)
                .videoPath(fullPath)
                .type(videoType) // 일단 연습 영상으로 고정 (필요시 dto.getType()))
                .build();

        videoRepository.save(video);

        // ======숙제 제출인 경우======
        // 숙제 정보 조회
        Assignment assignment = null;
        if (dto.getAssignmentId() != null) {
            assignment = assignmentRepository.findById(dto.getAssignmentId())
                    .orElseThrow(() -> new IllegalArgumentException("존재하지 않는 숙제입니다."));
        }

        // ======기준 영상 결정======
        Video referenceVideo = null;
        if (assignment != null) {
            // 숙제 제출: 숙제의 targetVideo가 기준 영상
            referenceVideo = assignment.getTargetVideo();
        } else if (dto.getReferenceVideoId() != null) {
            // 자율 연습: 직접 업로드한 기준 영상 사용
            referenceVideo = videoRepository.findById(dto.getReferenceVideoId())
                    .orElseThrow(() -> new IllegalArgumentException("기준 영상을 찾을 수 없습니다."));
        }

        // 6. PracticeLog 생성 및 저장
        PracticeLog practiceLog = PracticeLog.builder()
                .user(user)
                .practiceVideo(video)
                .referenceVideo(referenceVideo)
                .assignment(assignment)
                .build();

        practiceLogRepository.save(practiceLog);

        // [NEW] 기준 영상이 있으면 자동으로 비동기 분석 시작
        if (referenceVideo != null) {
            asyncAnalysisService.analyzeAsync(practiceLog.getId());
        }

        return video.getId();
    }

    public Resource playVideo(Long videoId, Long viewerId) {

        Video video = videoRepository.findById(videoId)
                .orElseThrow(() -> new IllegalArgumentException("존재하지 않는 영상입니다."));

        // 조회자 정보
        User viewer = userRepository.findById(viewerId)
                .orElseThrow(() -> new IllegalArgumentException("존재하지 않는 사용자입니다."));

        // ===== 권한 검사 =====
        // 1. 본인이 업로드한 영상 → OK
        boolean isUploader = video.getUploader().getId().equals(viewerId);

        // 2. 같은 팀원이 업로드한 기준 영상(REFERENCE) → OK
        boolean isSameTeamReferenceVideo = false;
        if (video.getType() == VideoType.REFERENCE) {
            Team uploaderTeam = video.getUploader().getTeam();
            Team viewerTeam = viewer.getTeam();
            if (uploaderTeam != null && viewerTeam != null) {
                isSameTeamReferenceVideo = uploaderTeam.getId().equals(viewerTeam.getId());
            }
        }

        // 권한이 없으면 거부
        if (!isUploader && !isSameTeamReferenceVideo) {
            throw new IllegalStateException("해당 영상을 볼 권한이 없습니다.");
        }

        String path = video.getVideoPath();
        FileSystemResource resource = new FileSystemResource(path);

        // DB에는 있는데 실제 파일이 지워졌을 경우 대비
        if (!resource.exists()) {
            throw new IllegalArgumentException("파일이 서버에서 삭제되었습니다. 경로: " + path);
        }

        return resource;
    }

    // 영상 삭제
    @Transactional // DB 작업이 있으므로 트랜잭션 필수
    public void deleteVideo(Long videoId, Long requesterId) {
        // 삭제할 영상 확인
        Video video = videoRepository.findById(videoId)
                .orElseThrow(() -> new IllegalArgumentException("존재하지 않는 영상입니다."));

        // 권한 인증
        if (!video.getUploader().getId().equals(requesterId)) {
            throw new IllegalStateException("삭제 권한이 없습니다.");
        }

        // DB를 먼저 지워야해서 경로 미리 저장해둠
        String filePath = video.getVideoPath();

        // 물리 파일보다 DB에서 먼저 삭제
        videoRepository.delete(video);

        // DB 먼저 삭제 후 물리 파일 삭제, 아까 저장한 경로 활용
        deleteFile(filePath);
    }

    // 물리 파일 삭제 메서드
    private void deleteFile(String filePath) {
        File file = new File(filePath);
        if (file.exists()) {
            boolean deleted = file.delete();
            if (!deleted) {
                // 로그 남기라는데 왜 이유는 모르겠다.
                System.out.println("경고: DB는 삭제되었으나 파일 삭제 실패. 경로: " + filePath);
            }
        }
    }

}
