package SeSAC.Dance_Assessment.Domain;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Assignment extends BaseTimeEntity {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "assignment_id")
    private Long id;

    // 1. 어느 팀의 숙제인지 (team_id)
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "team_id")
    private Team team;

    // 2. 숙제를 낸 팀장/작성자 (writer_id)
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "writer_id")
    private User writer;

    // 3. 기준이 되는 영상 (target_video_id)
    // 여러 숙제에서 같은 영상을 쓸 수도 있으니 ManyToOne이 안전합니다.
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "target_video_id")
    private Video targetVideo;

    // 4. 제목
    private String title;

    // 5. 시작일 (start_date)
    // BaseTimeEntity의 createdDate와 다르게, "숙제 시작일"을 별도로 지정하고 싶을 때 사용
    private LocalDateTime startDate;

    // 6. 마감일 (due_date)
    private LocalDateTime dueDate;

    @Builder
    public Assignment(Team team, User writer, Video targetVideo, String title, LocalDateTime startDate, LocalDateTime dueDate) {
        this.team = team;
        this.writer = writer;
        this.targetVideo = targetVideo;
        this.title = title;
        this.startDate = startDate;
        this.dueDate = dueDate;
    }
}
