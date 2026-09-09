package SeSAC.Dance_Assessment.Service;

import SeSAC.Dance_Assessment.Domain.AnalysisResult;
import SeSAC.Dance_Assessment.Domain.AnalysisStatus;
import SeSAC.Dance_Assessment.Domain.PracticeLog;
import SeSAC.Dance_Assessment.Domain.Video;
import SeSAC.Dance_Assessment.Dto.PracticeLog.AnalysisAcceptedResponse;
import SeSAC.Dance_Assessment.Dto.PracticeLog.AnalysisProgressResponse;
import SeSAC.Dance_Assessment.Dto.PracticeLog.PracticeLogDetailResponse;
import SeSAC.Dance_Assessment.Dto.PracticeLog.PracticeLogListResponse;
import SeSAC.Dance_Assessment.Dto.PracticeLog.TrimRangeRequest;
import SeSAC.Dance_Assessment.Infrastructure.AnalysisResultRepository;
import SeSAC.Dance_Assessment.Infrastructure.PracticeLogRepository;
import SeSAC.Dance_Assessment.Storage.StorageService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true) // 조회 전용
public class PracticeLogService {

    private final PracticeLogRepository practiceLogRepository;
    private final AnalysisResultRepository analysisResultRepository;
    private final AsyncAnalysisService asyncAnalysisService;
    private final AnalysisResultWriter analysisResultWriter;
    private final AiClientService aiClientService;
    private final StorageService storage;
    private final ObjectMapper objectMapper;

    public Page<PracticeLogListResponse> getMyPracticeLogs(Long userId, Pageable pageable) {
        Page<PracticeLog> logPage = practiceLogRepository.findByUserId(userId, pageable);
        return logPage.map(PracticeLogListResponse::from);
    }

    /**
     * 연습 기록 상세 조회. 분석 결과(구간 피드백)를 포함한다.
     *
     * <p>분석은 비동기라 이 API를 폴링해 {@code status}가 COMPLETED가 되기를
     * 기다리는 것이 정상 흐름이다.
     */
    public PracticeLogDetailResponse getPracticeLogDetail(Long logId, Long userId) {
        PracticeLog log = findOwnedLog(logId, userId);
        AnalysisResult result = log.getAnalysisResult();

        // 결과물 URL은 **조회할 때마다 새로 만든다.** 서명 URL은 만료되므로
        // DB에 넣어두면 얼마 못 가 열리지 않는다. DB에는 키만 저장한다.
        String videoUrl = null;
        List<String> imageUrls = List.of();
        if (result != null) {
            if (result.getComparisonVideoKey() != null) {
                videoUrl = storage.createDownloadUrl(result.getComparisonVideoKey());
            }
            imageUrls = signIssueImages(result.getTopIssuesJson());
        }
        return PracticeLogDetailResponse.from(log, videoUrl, imageUrls);
    }

    /**
     * 저장된 구간 JSON에서 이미지 키를 꺼내 서명 URL로 바꾼다.
     * 이미지를 만들지 못한 구간 자리에는 null이 들어간다(순서를 유지해야 하므로).
     */
    private List<String> signIssueImages(String topIssuesJson) {
        if (topIssuesJson == null || topIssuesJson.isBlank()) {
            return List.of();
        }
        try {
            JsonNode issues = objectMapper.readTree(topIssuesJson);
            List<String> urls = new ArrayList<>();
            for (JsonNode issue : issues) {
                JsonNode key = issue.get("image_key");
                urls.add(key == null || key.isNull()
                        ? null : storage.createDownloadUrl(key.asText()));
            }
            return urls;
        } catch (Exception e) {
            // 이미지가 안 보이는 것뿐이므로 구간 피드백까지 막지는 않는다.
            log.warn("[결과 이미지 URL 생성 실패] {}", e.getMessage());
            return List.of();
        }
    }

    /**
     * 분석을 시작시킨다. <b>결과를 기다리지 않고 즉시 반환한다.</b>
     *
     * <p>분석에 실측 1분 50초~2분 40초가 걸려 HTTP 요청을 붙잡고 있을 수 없다.
     * 호출자는 {@code GET /practice-logs/{logId}}를 폴링해야 한다.
     *
     * @return 접수 결과 (현재 상태와 폴링 대상 안내)
     */
    @Transactional
    public AnalysisAcceptedResponse requestAnalysis(Long logId, Long userId) {
        PracticeLog practiceLog = findOwnedLog(logId, userId);

        if (practiceLog.getReferenceVideo() == null) {
            throw new IllegalStateException("기준 영상이 없어 분석할 수 없습니다. 기준 영상을 먼저 업로드해주세요.");
        }
        if (practiceLog.getPracticeVideo() == null) {
            throw new IllegalStateException("연습 영상이 없어 분석할 수 없습니다.");
        }

        // 이미 돌고 있으면 중복 실행하지 않는다. 한 번에 2~3분씩 CPU를 쓰는
        // 작업이라 버튼 연타로 여러 개가 뜨면 서버가 버티지 못한다.
        AnalysisResult existing = analysisResultRepository.findByPracticeLogId(logId).orElse(null);
        if (existing != null && existing.getStatus() == AnalysisStatus.PROCESSING) {
            return AnalysisAcceptedResponse.alreadyRunning(logId);
        }

        AnalysisResult result = analysisResultWriter.findOrCreateResult(practiceLog);
        result.markProcessing();

        asyncAnalysisService.analyzeAsync(logId);
        return AnalysisAcceptedResponse.accepted(logId, trimApplied(practiceLog));
    }

    /**
     * 영상의 안무 구간을 저장한다.
     *
     * <p>프론트의 트림 UI가 고른 시작/끝 시각이 여기로 들어온다. 영상을 실제로
     * 자르지 않고 타임스탬프만 보관한다.
     */
    @Transactional
    public void updateTrimRange(Long logId, Long userId, TrimRangeRequest request) {
        PracticeLog practiceLog = findOwnedLog(logId, userId);

        if (practiceLog.getPracticeVideo() != null) {
            practiceLog.getPracticeVideo().updateChoreographyRange(
                    request.practiceStartSec(), request.practiceEndSec());
        }
        if (practiceLog.getReferenceVideo() != null) {
            practiceLog.getReferenceVideo().updateChoreographyRange(
                    request.referenceStartSec(), request.referenceEndSec());
        }
    }

    /**
     * 양쪽 시작 시각이 모두 있어야 좁은 밴드가 적용된다. 한쪽만 있으면
     * 전역 오프셋이 남아 이득이 없다.
     */
    private boolean trimApplied(PracticeLog log) {
        Video ref = log.getReferenceVideo();
        Video prac = log.getPracticeVideo();
        return ref != null && prac != null
                && ref.getChoreographyStartSec() != null
                && prac.getChoreographyStartSec() != null;
    }

    /**
     * 분석 진행 단계를 돌려준다.
     *
     * <p><b>상세 조회와 분리한 이유:</b> 진행률을 알려면 분석 서버에 물어봐야 하는데,
     * 그걸 상세 조회에 넣으면 분석 서버가 꺼져 있을 때 결과 화면 전체가 열리지 않는다.
     * 이미 끝난 분석을 보는 데 분석 서버가 살아 있어야 할 이유는 없다.
     *
     * <p>분석 서버에 닿지 못하거나 <b>다른 작업이 돌고 있으면</b> 단계 없이 상태만
     * 돌려준다. 분석 서버는 진행 상황을 한 건분만 들고 있어서, 작업 표식을
     * 대조하지 않으면 남의 진행률을 보여주게 된다.
     */
    public AnalysisProgressResponse getAnalysisProgress(Long logId, Long userId) {
        PracticeLog log = findOwnedLog(logId, userId);
        AnalysisResult result = log.getAnalysisResult();
        AnalysisStatus status = result != null ? result.getStatus() : AnalysisStatus.WAITING;

        if (result == null || status != AnalysisStatus.PROCESSING) {
            return AnalysisProgressResponse.unknown(status);
        }

        return aiClientService.fetchProgress()
                .filter(p -> "running".equals(p.getState()))
                .filter(p -> result.getAnalysisJobId() != null
                        && result.getAnalysisJobId().equals(p.getJobId()))
                .map(p -> AnalysisProgressResponse.of(status, p))
                .orElseGet(() -> AnalysisProgressResponse.unknown(status));
    }

    private PracticeLog findOwnedLog(Long logId, Long userId) {
        PracticeLog practiceLog = practiceLogRepository.findById(logId)
                .orElseThrow(() -> new IllegalArgumentException("기록 없음"));

        if (practiceLog.getUser() == null || !practiceLog.getUser().getId().equals(userId)) {
            throw new IllegalStateException("권한 없음");
        }
        return practiceLog;
    }
}
