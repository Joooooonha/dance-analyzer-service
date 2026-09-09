package SeSAC.Dance_Assessment;

import SeSAC.Dance_Assessment.Dto.ApiTime;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.time.LocalDateTime;
import java.time.Month;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 서버가 만든 시각이 <b>시간대가 명시된 문자열</b>로 나가는지 지킨다.
 *
 * <p>실제로 겪은 문제라서 테스트로 남긴다. {@code LocalDateTime}을 그대로
 * 내보내니 {@code "2026-09-09T06:42:00"}처럼 시간대 없는 값이 갔고, 브라우저가
 * 그것을 자기 시간대의 벽시계로 읽었다. 운영 서버(EC2)가 UTC로 도는 탓에
 * 한국에서 오후 3시 42분에 한 분석이 화면에 <b>오전 6시 42분</b>으로 찍혔다.
 *
 * <p>두 가지가 동시에 지켜져야 한다:
 * <ol>
 *   <li>{@code ApiTime.utc()}가 UTC로 해석할 것</li>
 *   <li>Jackson이 그걸 <b>숫자(epoch)가 아니라 ISO 문자열</b>로 쓸 것 —
 *       {@code WRITE_DATES_AS_TIMESTAMPS}가 켜지면 {@code 1788936153.585}처럼
 *       나가고 프론트의 {@code new Date(...)}가 깨진다.</li>
 * </ol>
 */
@SpringBootTest
class ApiTimeSerializationTest {

    @Autowired
    ObjectMapper objectMapper;

    @Test
    @DisplayName("서버 기록 시각은 UTC 순간으로 변환된다")
    void convertsToUtcInstant() {
        LocalDateTime stored = LocalDateTime.of(2026, Month.SEPTEMBER, 9, 6, 42, 0);
        assertThat(ApiTime.utc(stored).toString()).isEqualTo("2026-09-09T06:42:00Z");
    }

    @Test
    @DisplayName("null은 그대로 null이다 (분석 전에는 분석 완료 시각이 없다)")
    void nullStaysNull() {
        assertThat(ApiTime.utc(null)).isNull();
    }

    @Test
    @DisplayName("JSON에는 Z가 붙은 ISO 문자열로 실린다 — 숫자가 아니다")
    void serializesAsIsoStringWithZone() throws Exception {
        String json = objectMapper.writeValueAsString(
                ApiTime.utc(LocalDateTime.of(2026, Month.SEPTEMBER, 9, 6, 42, 0)));

        assertThat(json).startsWith("\"").endsWith("\"");   // 숫자가 아니라 문자열
        assertThat(json).contains("2026-09-09T06:42:00");
        assertThat(json).contains("Z");                     // 시간대가 명시됨
    }
}
