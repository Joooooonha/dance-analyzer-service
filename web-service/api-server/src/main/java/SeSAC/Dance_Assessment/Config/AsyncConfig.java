package SeSAC.Dance_Assessment.Config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.Executor;
import java.util.concurrent.RejectedExecutionException;

/**
 * 분석 작업용 스레드 풀.
 *
 * <p><b>기본 실행기를 쓰면 안 된다.</b> Spring의 {@code @Async} 기본값은
 * {@code SimpleAsyncTaskExecutor}로, 요청마다 스레드를 <b>무제한으로 새로 만든다.</b>
 * 분석 한 건이 맥미니 CPU를 1~2분 점유하는 작업이라, 동시 요청이 몇 개만 들어와도
 * 서로 CPU를 나눠 갖다가 전부 느려지고 결국 아무것도 제때 끝나지 않는다.
 *
 * <p>그래서 <b>동시 실행 수를 1로 제한하고 나머지는 큐에 세운다.</b>
 * 분석은 이미 비동기라 사용자는 대기 화면을 보고 있고, 순서대로 처리되면
 * 앞 사람은 정상 속도로 끝난다. 병렬로 돌려 다 같이 느려지는 것보다 낫다.
 */
@Slf4j
@Configuration
@EnableAsync
public class AsyncConfig {

    /**
     * 동시 분석 수. 맥미니 한 대가 감당할 수 있는 만큼만.
     *
     * <p>분석 내부에서 이미 영상마다 별도 프로세스를 띄우고 MediaPipe가 여러
     * 코어를 쓰므로, 여기서 더 늘리면 코어 경합만 커진다.
     */
    private static final int CONCURRENT_ANALYSES = 1;

    /** 대기열 길이. 넘치면 즉시 거절해서 무한정 쌓이지 않게 한다. */
    private static final int QUEUE_CAPACITY = 20;

    @Bean("analysisExecutor")
    public Executor analysisExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(CONCURRENT_ANALYSES);
        executor.setMaxPoolSize(CONCURRENT_ANALYSES);
        executor.setQueueCapacity(QUEUE_CAPACITY);
        executor.setThreadNamePrefix("analysis-");

        // 큐가 가득 차면 조용히 버리지 않고 예외를 던진다. 사용자에게 "대기 중"을
        // 보여주다가 영영 끝나지 않는 것이 가장 나쁜 결과다.
        executor.setRejectedExecutionHandler((r, e) -> {
            log.warn("[분석 거절] 대기열이 가득 찼습니다 (대기 {}건)", e.getQueue().size());
            throw new RejectedExecutionException("분석 요청이 밀려 있습니다. 잠시 후 다시 시도해주세요.");
        });

        // 종료 시 진행 중인 분석을 중간에 끊지 않는다. 끊기면 결과가
        // PROCESSING에 영원히 멈춘 채로 남는다.
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(300);

        executor.initialize();
        return executor;
    }
}
