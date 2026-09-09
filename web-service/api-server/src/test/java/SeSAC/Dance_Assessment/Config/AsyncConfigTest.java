package SeSAC.Dance_Assessment.Config;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.test.context.ActiveProfiles;

import java.util.concurrent.Executor;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 분석 스레드 풀이 실제로 제한돼 있는지 확인한다.
 *
 * <p>Spring의 {@code @Async} 기본 실행기({@code SimpleAsyncTaskExecutor})는
 * 요청마다 스레드를 <b>무제한 생성한다.</b> 분석 한 건이 CPU를 1~2분 점유하므로
 * 제한이 풀리면 동시 요청 몇 개만으로 서버가 사실상 멈춘다.
 * 설정이 조용히 원복되는 것을 막기 위해 고정한다.
 */
@SpringBootTest
@ActiveProfiles("dev")
class AsyncConfigTest {

    @Autowired
    @Qualifier("analysisExecutor")
    Executor executor;

    @Test
    @DisplayName("분석 실행기는 동시 실행 수와 대기열이 모두 제한돼 있다")
    void analysisExecutorIsBounded() {
        assertThat(executor).isInstanceOf(ThreadPoolTaskExecutor.class);
        ThreadPoolTaskExecutor pool = (ThreadPoolTaskExecutor) executor;

        // 무제한이면 Integer.MAX_VALUE에 가깝다
        assertThat(pool.getMaxPoolSize()).isLessThanOrEqualTo(2);
        assertThat(pool.getCorePoolSize()).isLessThanOrEqualTo(2);

        // 대기열도 유한해야 한다. 무한 큐면 요청이 끝없이 쌓여
        // 사용자는 영영 끝나지 않는 "분석 중"을 본다.
        assertThat(pool.getThreadPoolExecutor().getQueue().remainingCapacity())
                .isLessThan(Integer.MAX_VALUE);
    }

    @Test
    @DisplayName("분석 전용 스레드 풀을 쓴다 (요청 처리 스레드와 분리)")
    void usesDedicatedPool() {
        ThreadPoolTaskExecutor pool = (ThreadPoolTaskExecutor) executor;
        assertThat(pool.getThreadNamePrefix()).isEqualTo("analysis-");
    }
}
