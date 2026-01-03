package SeSAC.Dance_Assessment.Domain;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Video extends BaseTimeEntity {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "video_id")
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "uploader_id")  // 외래키 이름 설정
    private User uploader;


    @Enumerated(EnumType.STRING)   // DB에 숫자가 아닌 문자열("REFERENCE")로 저장
    private VideoType type;

    private String videoPath;
    private AnalysisStatus analysisStatus;


    @Builder
    public Video(User uploader,String videoPath, VideoType type) {
        this.uploader = uploader;
        this.videoPath = videoPath;
        this.type = type;
    }
}