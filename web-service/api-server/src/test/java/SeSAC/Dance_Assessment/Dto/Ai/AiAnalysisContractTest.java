package SeSAC.Dance_Assessment.Dto.Ai;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.InputStream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Spring DTO가 Python AI 서버의 실제 응답을 제대로 읽는지 검증한다.
 *
 * <p><b>이 테스트가 필요한 이유:</b> 두 서버는 JSON 필드 이름으로만 연결돼 있고,
 * Jackson은 모르는 필드를 만나면 조용히 null로 둔다. {@code @JsonProperty} 하나만
 * 틀려도 컴파일도 통과하고 요청도 200으로 끝나는데 화면에만 값이 안 나온다.
 * 그래서 <b>실제로 돌린 응답</b>을 고정해 두고 필드가 채워지는지 확인한다.
 *
 * <p>{@code ai-analyze-response-sample.json}은 natural1 영상 쌍을 구간 지정과 함께
 * 실제 분석한 결과다 (지적 구간 47개, 이미지 10개를 서명 URL로 업로드).
 */
class AiAnalysisContractTest {

    private static final String SAMPLE = "/ai-analyze-response-sample.json";

    private AiAnalysisResponse readSample() throws Exception {
        // 서비스와 같은 조건으로 읽는다. 모르는 필드가 있어도 죽지 않아야 한다
        // (AI 서버가 필드를 추가해도 Spring이 멈추면 안 되므로).
        ObjectMapper mapper = new ObjectMapper()
                .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);
        try (InputStream in = getClass().getResourceAsStream(SAMPLE)) {
            assertThat(in).as("샘플 응답 파일이 있어야 한다").isNotNull();
            return mapper.readValue(in, AiAnalysisResponse.class);
        }
    }

    @Test
    @DisplayName("응답 최상위 필드가 모두 매핑된다 — 점수 필드는 더 이상 없다")
    void topLevelFieldsAreMapped() throws Exception {
        AiAnalysisResponse res = readSample();

        assertThat(res.getStatus()).isEqualTo("success");
        assertThat(res.getIssueCount()).isEqualTo(47);
        assertThat(res.getMessage()).isNotBlank();

        // 구간 목록과 품질 지표가 null이면 필드명이 어긋난 것이다
        assertThat(res.getTopIssues()).hasSize(10);
        assertThat(res.getQuality()).isNotNull();
        assertThat(res.getTrim()).isNotNull();
        assertThat(res.getUnreliableSpans()).isNotNull();
    }

    @Test
    @DisplayName("구간 하나가 화면에 필요한 값을 전부 갖는다")
    void issueCarriesEverythingTheScreenNeeds() throws Exception {
        IssueInfo first = readSample().getTopIssues().get(0);

        assertThat(first.getRank()).isEqualTo(1);
        assertThat(first.getGroup()).isNotBlank();          // 왼팔 / 오른다리 / 상체 ...
        assertThat(first.getMessage()).isNotBlank();        // "왼쪽 팔꿈치를 더 펴세요"
        assertThat(first.getStartSec()).isNotNull();
        assertThat(first.getEndSec()).isGreaterThan(first.getStartSec());
        assertThat(first.getDurationSec()).isNotNull();
        assertThat(first.getSeverity()).isPositive();
        assertThat(first.getMeanErrorDeg()).isPositive();
        assertThat(first.getParts()).isNotEmpty();

        // 같은 부위 이름이 중복되면 화면에서 같은 말이 두 번 나온다
        assertThat(first.getParts()).doesNotHaveDuplicates();
    }

    @Test
    @DisplayName("[핵심] 이미지는 URL이 아니라 슬롯 번호로 온다")
    void imagesComeBackAsSlots() throws Exception {
        AiAnalysisResponse res = readSample();

        // 분석 서버는 저장소 자격증명이 없어 자기가 올린 객체의 키를 모른다.
        // 그래서 URL이 아니라 "몇 번 슬롯에 올렸는지"만 알려주고,
        // 키를 아는 Spring이 슬롯 → 키로 되돌린다.
        for (IssueInfo issue : res.getTopIssues()) {
            assertThat(issue.getImageSlot()).isNotNull();
            assertThat(issue.getImageSlot()).isBetween(0, res.getTopIssues().size() - 1);
            // 키는 Spring이 나중에 채운다. 응답 시점에는 비어 있어야 한다.
            assertThat(issue.getImageKey()).isNull();
        }

        // 슬롯이 겹치면 두 구간이 같은 이미지를 가리키게 된다
        assertThat(res.getTopIssues().stream().map(IssueInfo::getImageSlot))
                .doesNotHaveDuplicates();
    }

    @Test
    @DisplayName("대표 프레임으로 양쪽 영상을 각각 점프시킬 수 있다")
    void representativeAllowsJumpingBothVideos() throws Exception {
        IssueRepresentative rep = readSample().getTopIssues().get(0).getRepresentative();

        assertThat(rep).as("대표 프레임이 있어야 영상 점프가 가능하다").isNotNull();
        assertThat(rep.getPracticeSec()).isNotNull();
        assertThat(rep.getReferenceSec()).isNotNull();
        assertThat(rep.getPracticeFrame()).isNotNull();
        assertThat(rep.getReferenceFrame()).isNotNull();
        assertThat(rep.getFrameErrorDeg()).isPositive();

        // 두 시각이 다른 것이 정상이다 — 같은 동작이 서로 다른 시점에 있어서
        // 정렬하는 것이므로, 두 값이 늘 같다면 정렬이 반영되지 않은 것이다.
        assertThat(rep.getPracticeSec()).isNotEqualTo(rep.getReferenceSec());
    }

    @Test
    @DisplayName("품질 지표가 매핑되고, 정렬 신뢰도를 사칭하는 필드가 없다")
    void qualityIsMapped() throws Exception {
        AlignmentQuality q = readSample().getQuality();

        assertThat(q.getScoredPct()).isBetween(0.0, 100.0);
        assertThat(q.getMeanErrorDeg()).isPositive();
        assertThat(q.getPracticeJointValidRatio()).isBetween(0.0, 1.0);
        assertThat(q.getReferenceJointValidRatio()).isBetween(0.0, 1.0);
        assertThat(q.getGlobalOffsetSec()).isNotNull();

        // 이 샘플은 검출이 잘 된 영상이라 경고가 없어야 한다
        assertThat(q.getWarning()).isNull();
    }

    @Test
    @DisplayName("구간 지정이 실제로 적용됐음을 응답으로 확인할 수 있다")
    void trimEchoReportsApplied() throws Exception {
        TrimEcho trim = readSample().getTrim();

        assertThat(trim.getApplied()).isTrue();
        assertThat(trim.getReferenceStartSec()).isNotNull();
        assertThat(trim.getPracticeStartSec()).isNotNull();
        // 끝 시각은 선택이라 이 샘플에서는 비어 있다
        assertThat(trim.getReferenceEndSec()).isNull();
    }

    @Test
    @DisplayName("확인 어려움 구간을 다시 직렬화해도 같은 값이 두 번 나가지 않는다")
    void unreliableSpanDoesNotDuplicateKeys() throws Exception {
        AiAnalysisResponse res = readSample();
        assertThat(res.getUnreliableSpans()).isNotEmpty();

        UnreliableSpan span = res.getUnreliableSpans().get(0);
        assertThat(span.getStartSec()).isNotNull();
        assertThat(span.getNumFrames()).isNotNull();

        // 이 목록은 DB에 JSON 문자열로 저장돼 프론트로 그대로 나간다.
        // 필드 이름을 잘못 두면 {"nframes":3, ..., "n_frames":3}처럼 같은 값이
        // 두 키로 나가는 일이 실제로 있었다.
        String json = new ObjectMapper().writeValueAsString(span);
        assertThat(json).contains("\"n_frames\"");
        assertThat(json).doesNotContain("\"nframes\"");
        assertThat(json).doesNotContain("\"numFrames\"");
    }

    @Test
    @DisplayName("요청 DTO는 지정하지 않은 구간 필드를 아예 보내지 않는다")
    void requestOmitsNullTrimFields() throws Exception {
        String json = new ObjectMapper().writeValueAsString(AiAnalysisRequest.builder()
                .referenceVideoUrl("https://storage.example/ref?sig=x")
                .practiceVideoUrl("https://storage.example/prac?sig=y")
                .build());

        // AI 서버는 "미지정"과 "0초"를 다르게 처리한다. null을 0으로 보내면
        // 영상 맨 앞부터 안무가 시작한다고 잘못 알려주는 셈이 된다.
        assertThat(json).doesNotContain("reference_start_sec");
        assertThat(json).doesNotContain("practice_start_sec");
        assertThat(json).contains("\"top_issues\":10");
        assertThat(json).contains("\"generate_video\":false");
    }

    @Test
    @DisplayName("요청에 로컬 파일 경로가 아니라 URL이 실린다")
    void requestCarriesUrlsNotPaths() throws Exception {
        String json = new ObjectMapper().writeValueAsString(AiAnalysisRequest.builder()
                .referenceVideoUrl("https://storage.example/ref?sig=x")
                .practiceVideoUrl("https://storage.example/prac?sig=y")
                .imageUploadUrls(java.util.List.of("https://storage.example/img0?sig=z"))
                .build());

        // 예전에는 서버 로컬 경로를 보냈다. Spring이 EC2로, 분석이 맥미니로
        // 갈라지는 순간 그 경로는 어느 쪽에서도 열리지 않는다.
        assertThat(json).contains("reference_video_url");
        assertThat(json).contains("practice_video_url");
        assertThat(json).contains("image_upload_urls");
        assertThat(json).doesNotContain("video_path");
    }
}
