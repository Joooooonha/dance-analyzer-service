package SeSAC.Dance_Assessment.Dto.Ai;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * Python AI 서버 {@code POST /analyze} 요청 DTO.
 *
 * <p>구간(trim) 필드는 전부 선택이지만, <b>양쪽 시작 시각을 함께 보내는 것이
 * 핵심</b>이다. 두 영상의 녹화 시작 시점이 다르면 정렬 밴드를 좁힐 수 없어
 * DTW가 멀리 떨어진 "포즈가 비슷한" 지점으로 도망갈 수 있다. 시작 시각이
 * 확정되면 좁은 밴드로 국소 워핑만 허용할 수 있다.
 *
 * <p>끝 시각은 선택이다 — 실측상 추가 이득이 4.7%p로 작았다. UI에서는 시작점을
 * 우선 안내하고 끝점은 여백이 많을 때만 받으면 된다.
 *
 * <p>{@code null}인 필드는 직렬화에서 제외한다. AI 서버가 "미지정"과 "0초"를
 * 다르게 처리하므로 0을 보내면 안 된다.
 */
@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@JsonInclude(JsonInclude.Include.NON_NULL)
public class AiAnalysisRequest {

    /**
     * 기준 영상을 <b>내려받을 수 있는 서명된 URL</b>.
     *
     * <p>예전에는 서버 로컬 경로(`/Users/.../x.mp4`)를 보냈다. Spring이 EC2로,
     * 분석이 맥미니로 갈라지는 순간 그 경로는 어느 쪽에서도 열리지 않는다.
     */
    @JsonProperty("reference_video_url")
    private String referenceVideoUrl;

    @JsonProperty("practice_video_url")
    private String practiceVideoUrl;

    @JsonProperty("reference_start_sec")
    private Double referenceStartSec;

    @JsonProperty("reference_end_sec")
    private Double referenceEndSec;

    @JsonProperty("practice_start_sec")
    private Double practiceStartSec;

    @JsonProperty("practice_end_sec")
    private Double practiceEndSec;

    /**
     * 진행률을 물어볼 때 "내가 맡긴 그 작업이 맞는지" 확인하는 표식.
     *
     * <p>분석 서버는 동시에 한 건만 돌리므로 진행 상황도 한 건분만 들고 있다.
     * 표식이 없으면 다른 사용자의 분석 진행률을 자기 것으로 보여주게 된다.
     */
    @JsonProperty("job_id")
    private String jobId;

    /** 돌려받을 상위 지적 구간 수 */
    @JsonProperty("top_issues")
    @Builder.Default
    private Integer topIssues = 10;

    /** 구간별 비교 이미지 생성 */
    @JsonProperty("generate_images")
    @Builder.Default
    private Boolean generateImages = true;

    /**
     * 정렬된 나란히 비교 영상 생성.
     * <p><b>항상 false다.</b> 렌더링에 60~90초가 더 드는데, 응답의 sync_map으로
     * 화면이 원본 두 개를 맞춰 돌릴 수 있어 결과물이 오히려 낫다.
     */
    @JsonProperty("generate_video")
    @Builder.Default
    private Boolean generateVideo = false;

    /**
     * 결과 이미지를 올릴 서명된 PUT URL들. 순서 = 지적 구간 순위(0부터).
     *
     * <p><b>분석 서버에 저장소 자격증명을 주지 않기 위한 설계다.</b> 맥미니는
     * 집에 있는 홈서버라 EC2보다 통제가 약한데, 거기에 R2 쓰기 키를 두면
     * 그 기기가 뚫렸을 때 버킷 전체가 위험해진다. 대신 이 요청에 필요한 만큼의
     * 짧은 URL만 미리 발급해서 넘긴다 — 뚫려도 얻는 것이 만료될 URL 몇 개뿐이다.
     *
     * <p>구간이 몇 개 나올지는 분석 전에 알 수 없으므로 {@code topIssues}개를
     * 미리 발급하고, 분석 서버가 쓴 만큼만 사용한 뒤 어느 슬롯을 썼는지 알려준다.
     */
    @JsonProperty("image_upload_urls")
    private List<String> imageUploadUrls;

    /** 비교 영상을 올릴 서명된 PUT URL. {@code generateVideo}가 true일 때만. */
    @JsonProperty("video_upload_url")
    private String videoUploadUrl;
}
