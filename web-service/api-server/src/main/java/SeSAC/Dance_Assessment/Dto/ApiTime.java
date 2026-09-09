package SeSAC.Dance_Assessment.Dto;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;

/**
 * 서버가 만든 시각을 응답에 실을 때 쓰는 변환.
 *
 * <p><b>{@code LocalDateTime}을 그대로 내보내면 안 된다.</b> 시간대 정보가 없는
 * 값이라 {@code "2026-09-09T06:42:00"} 같은 문자열이 나가고, 브라우저는 그것을
 * 자기 시간대의 벽시계로 읽는다. 운영 서버(EC2)가 UTC로 도는 탓에 한국에서
 * 오후 3시 42분에 한 분석이 화면에 <b>오전 6시 42분</b>으로 찍혔다.
 *
 * <p>UTC임을 명시한 순간(ISO-8601, 끝에 {@code Z})으로 내보내면 브라우저가
 * 알아서 사용자의 지역 시각으로 그린다 — 해외에서 열어도 맞다. 서버 시간대를
 * 한국으로 바꾸는 방법도 있지만, 그러면 저장된 값의 의미가 시점에 따라 달라지고
 * 사용자가 다른 시간대에 있을 때 또 틀린다.
 *
 * <p><b>사용자가 입력한 시각(숙제 마감일 등)에는 쓰지 않는다.</b> 그건 특정
 * 순간이 아니라 "그 지역의 벽시계로 몇 시"라는 뜻이라 성격이 다르다.
 */
public final class ApiTime {

    private ApiTime() {
    }

    /** 서버가 UTC로 기록한 시각 → 시간대가 명시된 순간. */
    public static Instant utc(LocalDateTime t) {
        return t == null ? null : t.toInstant(ZoneOffset.UTC);
    }
}
