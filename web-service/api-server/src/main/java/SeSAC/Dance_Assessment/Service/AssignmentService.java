package SeSAC.Dance_Assessment.Service;

import SeSAC.Dance_Assessment.Domain.Assignment;
import SeSAC.Dance_Assessment.Domain.PracticeLog;
import SeSAC.Dance_Assessment.Domain.User;
import SeSAC.Dance_Assessment.Domain.Video;
import SeSAC.Dance_Assessment.Dto.Assignment.AssignmentCreateRequest;
import SeSAC.Dance_Assessment.Dto.Assignment.AssignmentDetailResponse;
import SeSAC.Dance_Assessment.Dto.Assignment.AssignmentResponse;
import SeSAC.Dance_Assessment.Dto.Assignment.SubmissionResponseDto;
import SeSAC.Dance_Assessment.Dto.PracticeLog.PracticeLogDetailResponse;
import SeSAC.Dance_Assessment.Infrastructure.AssignmentRepository;
import SeSAC.Dance_Assessment.Infrastructure.PracticeLogRepository;
import SeSAC.Dance_Assessment.Infrastructure.UserRepository;
import SeSAC.Dance_Assessment.Infrastructure.VideoRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.file.AccessDeniedException;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class AssignmentService {

    private final AssignmentRepository assignmentRepository;
    private final UserRepository userRepository;
    private final VideoRepository videoRepository;
    private final PracticeLogRepository practiceLogRepository;

    // 숙제 생성 -> 팀장 고유 권한
    @Transactional
    public Long createAssignment(Long writerId, AssignmentCreateRequest request) {
        // 작성자 확인
        User writer = userRepository.findById(writerId)
                .orElseThrow(() -> new IllegalArgumentException("유저 없음"));

        // 팀 소속 확인
        if (writer.getTeam() == null) {
            throw new IllegalStateException("소속된 팀이 없습니다.");
        }

        // 기준 영상 확인
        Video targetVideo = videoRepository.findById(request.targetVideoId())
                .orElseThrow(() -> new IllegalArgumentException("영상 없음"));

        // 저장
        Assignment assignment = Assignment.builder()
                .team(writer.getTeam()) // 작성자의 팀으로 자동 할당
                .writer(writer)
                .targetVideo(targetVideo)
                .title(request.title())
                .startDate(request.startDate())
                .dueDate(request.dueDate())
                .build();

        return assignmentRepository.save(assignment).getId();
    }

    // 내 팀의 숙제 목록 조회
    public List<AssignmentResponse> getMyTeamAssignments(Long userId) {
        // 1. 유저 조회
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("유저 없음"));

        // 2. 팀 소속 확인
        if (user.getTeam() == null) {
            // 팀이 없으면 빈 리스트 반환 (또는 에러 처리)
            return List.of();
        }

        // 3. 리포지토리 조회 (아까 에러 잡았던 그 메서드 사용!)
        // Team 엔티티의 변수명을 'id'로 수정했다고 가정합니다.
        List<Assignment> assignments = assignmentRepository.findAllByTeamIdOrderByDueDateDesc(user.getTeam().getId());

        // 4. DTO 변환
        return assignments.stream()
                .map(AssignmentResponse::from)
                .toList();
    }

    // 팀장이 생성한 각 숙제별 팀원 제출 상황 확인
    public List<SubmissionResponseDto> getSubmissions(Long userId, Long assignmentId) throws AccessDeniedException {
        // 숙제 조회
        Assignment assignment = assignmentRepository.findById(assignmentId)
                .orElseThrow(() -> new IllegalArgumentException("숙제가 없습니다."));

        // 권한 체크 (핵심!: 요청자(userId)가 숙제 작성자(writer_id)와 같은가?)
        if (!assignment.getWriter().getId().equals(userId)) { // 비교값 넘겨줘서 확인하는 방식으로 수정
            throw new AccessDeniedException("팀장만 제출 목록을 볼 수 있습니다.");
        }

        // [RESTORED] 숙제에 대한 제출 기록 조회
        List<PracticeLog> logs = practiceLogRepository.findAllByAssignmentIdOrderByCreatedAtDesc(assignmentId);
        return logs.stream().map(SubmissionResponseDto::new).collect(Collectors.toList());
    }

    /**
     * [NEW] 숙제 상세 조회
     * - 숙제 정보와 기준 영상 정보를 함께 반환
     * - 팀원이 숙제 제출 페이지에서 기준 영상을 확인할 때 사용
     */
    public AssignmentDetailResponse getAssignmentDetail(Long assignmentId, Long userId) {
        // 유저 확인
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("유저 없음"));

        // 숙제 조회
        Assignment assignment = assignmentRepository.findById(assignmentId)
                .orElseThrow(() -> new IllegalArgumentException("숙제가 없습니다."));

        // 같은 팀인지 확인
        if (user.getTeam() == null || !user.getTeam().getId().equals(assignment.getTeam().getId())) {
            throw new IllegalStateException("해당 숙제를 볼 권한이 없습니다.");
        }

        return AssignmentDetailResponse.from(assignment);
    }

    /**
     * [NEW] 특정 숙제에 대한 내 제출 이력 조회
     * - 해당 숙제에 내가 제출한 모든 기록 반환
     */
    public List<PracticeLogDetailResponse> getMySubmissions(Long userId, Long assignmentId) {
        // 유저 확인
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("유저 없음"));

        // 숙제 확인 및 팀 권한 체크
        Assignment assignment = assignmentRepository.findById(assignmentId)
                .orElseThrow(() -> new IllegalArgumentException("숙제가 없습니다."));

        if (user.getTeam() == null || !user.getTeam().getId().equals(assignment.getTeam().getId())) {
            throw new IllegalStateException("해당 숙제를 볼 권한이 없습니다.");
        }

        // 내 제출 기록 조회
        List<PracticeLog> logs = practiceLogRepository.findAllByUserIdAndAssignmentIdOrderByCreatedAtDesc(userId,
                assignmentId);

        return logs.stream()
                .map(PracticeLogDetailResponse::from)
                .toList();
    }
}
