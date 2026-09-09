package SeSAC.Dance_Assessment.Infrastructure;

import SeSAC.Dance_Assessment.Domain.Video;
import SeSAC.Dance_Assessment.Domain.VideoType;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface VideoRepository extends JpaRepository<Video, Long> {

    /**
     * 다시 쓸 수 있는 내 영상 목록.
     *
     * <p>{@code uploadCompleted}가 false인 것은 제외한다 — 서명 URL만 받고 실제
     * 업로드는 하지 않은 행이 남을 수 있는데, 그걸 고르면 분석이 반드시 실패한다.
     */
    List<Video> findByUploaderIdAndTypeAndUploadCompletedTrueOrderByCreatedAtDesc(
            Long uploaderId, VideoType type);
}
