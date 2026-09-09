package SeSAC.Dance_Assessment.Dto.Ai;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.ToString;

import java.util.List;

/**
 * 틀린 동작 구간 하나.
 *
 * <p>프레임 단위가 아니라 <b>구간 단위</b>다. 같은 부위가 연속으로 틀리면 하나로
 * 묶고, 시간대가 겹치는 같은 신체 그룹(왼팔·오른다리·상체)의 지적도 하나로 합친다.
 * 합치지 않으면 한 순간에 평균 5.4개 부위가 동시에 걸려 사용자가 같은 내용을
 * 여러 번 읽게 된다.
 */
@Getter
@NoArgsConstructor
@ToString
public class IssueInfo {

    @JsonProperty("rank")
    private Integer rank;

    /** 신체 그룹: 왼팔 / 오른팔 / 왼다리 / 오른다리 / 상체 */
    @JsonProperty("group")
    private String group;

    /** 사용자에게 그대로 보여줄 문구. 예: "왼쪽 팔꿈치를 더 펴세요" */
    @JsonProperty("message")
    private String message;

    @JsonProperty("start_sec")
    private Double startSec;

    @JsonProperty("end_sec")
    private Double endSec;

    @JsonProperty("duration_sec")
    private Double durationSec;

    /**
     * 심각도. <b>절대 점수가 아니라 그 영상 자체의 부위별 분포 대비 배수</b>다
     * (1.0 = 그 부위의 중앙값). 부위마다 가동 범위가 달라 각도 수치를 그대로
     * 비교할 수 없기 때문에 이렇게 정규화한다.
     */
    @JsonProperty("severity")
    private Double severity;

    @JsonProperty("mean_error_deg")
    private Double meanErrorDeg;

    /** 이 구간에서 걸린 세부 부위들. 심각한 순서. */
    @JsonProperty("parts")
    private List<String> parts;

    @JsonProperty("representative")
    private IssueRepresentative representative;

    /**
     * 이 구간의 비교 이미지를 어느 업로드 슬롯에 올렸는지 (요청의
     * {@code image_upload_urls} 인덱스). 이미지를 만들지 못했으면 null.
     *
     * <p>분석 서버는 자기가 올린 객체의 <b>키를 모른다</b> — 서명된 URL만 받았기
     * 때문이다. 그래서 URL이 아니라 슬롯 번호를 돌려주고, 키를 아는 Spring이
     * 슬롯 → 키로 되돌린다.
     */
    @JsonProperty("image_slot")
    private Integer imageSlot;

    /**
     * 저장소 객체 키. 분석 서버가 아니라 <b>Spring이</b> 채운다 — 키를 아는 쪽이
     * Spring이기 때문이다. DB에 이 구조 그대로 저장되고, 조회 시점에 이 키로
     * 새 서명 URL을 만든다(서명 URL은 만료되므로 저장하면 안 된다).
     */
    @JsonProperty("image_key")
    private String imageKey;

    public void attachImageKey(String key) {
        this.imageKey = key;
    }
}
