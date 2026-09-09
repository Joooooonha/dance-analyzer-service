package SeSAC.Dance_Assessment.Service;

import SeSAC.Dance_Assessment.Infrastructure.PracticeLogRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 분석이 끝났음을 사용자에게 알린다.
 *
 * <p>분석 실행부({@link AsyncAnalysisService})와 발송부({@link WebPushService})
 * 사이에 두는 얇은 층이다. 알림을 보내려면 소유자를 알아야 하는데, 그걸 조회하려면
 * 트랜잭션이 필요하고, 분석 실행부는 이제 트랜잭션 밖에서 돌기 때문이다.
 *
 * <p><b>여기서 예외가 새어 나가면 안 된다.</b> 알림이 실패했다고 이미 저장된
 * 분석 결과가 실패로 뒤집히면 안 되기 때문이다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AnalysisNotifier {

    private final PracticeLogRepository practiceLogRepository;
    private final WebPushService webPushService;

    @Transactional(readOnly = true)
    public void analysisFinished(Long practiceLogId, boolean success, Integer issueCount) {
        try {
            Long userId = practiceLogRepository.findById(practiceLogId)
                    .map(l -> l.getUser() != null ? l.getUser().getId() : null)
                    .orElse(null);
            if (userId == null) {
                return;
            }

            String title = success ? "분석이 끝났어요" : "분석에 실패했어요";
            String body = success
                    ? "다듬을 구간 " + (issueCount != null ? issueCount : 0) + "개를 찾았습니다."
                    : "결과 화면에서 다시 시도할 수 있습니다.";

            webPushService.sendToUser(userId, title, body, "/logs/" + practiceLogId);
        } catch (Exception e) {
            log.warn("[알림] 전송 준비 실패 (logId={}): {}", practiceLogId, e.getMessage());
        }
    }
}
