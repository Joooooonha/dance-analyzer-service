package SeSAC.Dance_Assessment.Infrastructure;

import SeSAC.Dance_Assessment.Domain.PracticeLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface PracticeLogRepository extends JpaRepository<PracticeLog, Long> {

    // 특정 유저의 기록을 페이징해서 조회
    Page<PracticeLog> findByUserId(Long userId, Pageable pageable);

    // [RESTORED] 특정 숙제에 대한 모든 제출 기록 조회 (팀장 제출 현황용)
    List<PracticeLog> findAllByAssignmentIdOrderByCreatedAtDesc(Long assignmentId);

    // [NEW] 특정 사용자의 특정 숙제에 대한 제출 기록 조회 (최신 1개)
    Optional<PracticeLog> findTopByUserIdAndAssignmentIdOrderByCreatedAtDesc(Long userId, Long assignmentId);

    // [NEW] 특정 사용자의 특정 숙제에 대한 모든 제출 기록 조회
    List<PracticeLog> findAllByUserIdAndAssignmentIdOrderByCreatedAtDesc(Long userId, Long assignmentId);
}