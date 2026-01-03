package SeSAC.Dance_Assessment;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;
import org.springframework.scheduling.annotation.EnableAsync;

@EnableAsync // [NEW] 비동기 처리 활성화
@EnableJpaAuditing
@SpringBootApplication
public class DanceAssessmentApplication {

	public static void main(String[] args) {
		SpringApplication.run(DanceAssessmentApplication.class, args);
	}

}
