package SeSAC.Dance_Assessment.Infrastructure;

import SeSAC.Dance_Assessment.Domain.AnalysisResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.repository.CrudRepository;

import java.util.Optional;

public interface AnalysisResultRepository extends JpaRepository<AnalysisResult, Integer> {
    // 1:1 관계라서 logId로 결과가 이미 있는지 확인하는 메서드가 필요할 수 있음
    Optional<AnalysisResult> findByPracticeLogId(Long logId);
}
