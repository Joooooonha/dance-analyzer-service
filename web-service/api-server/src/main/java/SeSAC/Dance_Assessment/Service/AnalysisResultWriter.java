package SeSAC.Dance_Assessment.Service;

import SeSAC.Dance_Assessment.Domain.AnalysisResult;
import SeSAC.Dance_Assessment.Domain.AnalysisStatus;
import SeSAC.Dance_Assessment.Domain.PracticeLog;
import SeSAC.Dance_Assessment.Domain.Video;
import SeSAC.Dance_Assessment.Dto.Ai.AiAnalysisResponse;
import SeSAC.Dance_Assessment.Dto.Ai.IssueInfo;
import SeSAC.Dance_Assessment.Infrastructure.AnalysisResultRepository;
import SeSAC.Dance_Assessment.Infrastructure.PracticeLogRepository;
import SeSAC.Dance_Assessment.Storage.StorageKeys;
import SeSAC.Dance_Assessment.Storage.StorageService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;

/**
 * 분석 실행 중의 DB 쓰기를 <b>짧은 트랜잭션</b>으로 나눠 담당한다.
 *
 * <p><b>왜 분리했나.</b> 예전에는 {@code AsyncAnalysisService.analyzeAsync} 전체에
 * {@code @Transactional}이 붙어 있었다. 그 안에서 분석 서버를 3분 넘게 기다리므로:
 *
 * <ol>
 *   <li><b>진행률이 0%에서 움직이지 않았다.</b> 시작할 때 기록한
 *       {@code analysisJobId}가 메서드가 끝나야 커밋되는데, 진행률 조회는 별도
 *       트랜잭션이라 그때까지 {@code null}로 보인다. 작업 표식이 맞지 않으니
 *       진행 단계를 버렸고, 화면은 계속 0%였다.</li>
 *   <li>DB 커넥션 하나를 3분 넘게 붙잡고 있었다. 아무 질의도 하지 않으면서.</li>
 * </ol>
 *
 * <p>이제 분석 서버 호출은 트랜잭션 <b>밖</b>에서 일어나고, DB 쓰기는 여기 있는
 * 짧은 메서드들이 각자 커밋한다. 자기 자신을 호출하면 Spring 프록시를 거치지
 * 않아 {@code @Transactional}이 무시되므로 <b>반드시 별도 빈이어야 한다.</b>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AnalysisResultWriter {

    private final PracticeLogRepository practiceLogRepository;
    private final AnalysisResultRepository analysisResultRepository;
    private final StorageService storage;
    private final ObjectMapper objectMapper;

    /**
     * 분석 서버에 넘길 것들. 트랜잭션 밖에서 써야 하므로 엔티티가 아니라 값만 담는다.
     */
    public record AnalysisJob(
            String referenceDownloadUrl,
            String practiceDownloadUrl,
            Double referenceStartSec,
            Double referenceEndSec,
            Double practiceStartSec,
            Double practiceEndSec,
            List<String> imageKeys,
            List<String> imageUploadUrls) {
    }

    /**
     * 결과 엔티티를 찾거나 새로 만든다. 재분석이면 기존 행을 덮어쓴다.
     *
     * <p>호출자의 트랜잭션에 참여한다({@code REQUIRED}).
     */
    @Transactional
    public AnalysisResult findOrCreateResult(PracticeLog practiceLog) {
        return analysisResultRepository.findByPracticeLogId(practiceLog.getId())
                .orElseGet(() -> analysisResultRepository.save(AnalysisResult.builder()
                        .practiceLog(practiceLog)
                        .status(AnalysisStatus.WAITING)
                        .build()));
    }

    /**
     * 분석 시작을 <b>즉시 커밋</b>하고, 분석 서버에 넘길 값을 만들어 돌려준다.
     *
     * <p>즉시 커밋이 핵심이다 — 이게 커밋돼야 진행률 조회가 작업 표식을 볼 수 있다.
     *
     * @return 분석에 필요한 값들. 기준 영상이 없어 분석할 수 없으면 {@code null}
     */
    @Transactional
    public AnalysisJob begin(Long practiceLogId, String jobId, String runId, int topIssues) {
        PracticeLog practiceLog = practiceLogRepository.findById(practiceLogId)
                .orElseThrow(() -> new IllegalArgumentException("기록 없음: " + practiceLogId));

        Video reference = practiceLog.getReferenceVideo();
        Video practice = practiceLog.getPracticeVideo();
        if (reference == null || practice == null) {
            log.warn("[비동기 분석 스킵] 영상이 갖춰지지 않음: {}", practiceLogId);
            return null;
        }

        findOrCreateResult(practiceLog).markProcessing(jobId);

        // 결과물을 올릴 슬롯을 미리 발급한다. 구간이 몇 개 나올지는 분석 전에
        // 알 수 없으므로 상위 개수만큼 만들어 두고, 분석 서버가 쓴 만큼만 쓴다.
        // 이렇게 하면 맥미니에 저장소 자격증명을 두지 않아도 된다.
        List<String> imageKeys = new ArrayList<>();
        List<String> imageUploadUrls = new ArrayList<>();
        for (int slot = 0; slot < topIssues; slot++) {
            String key = StorageKeys.issueImage(practiceLogId, runId, slot);
            imageKeys.add(key);
            imageUploadUrls.add(storage.createUploadUrl(key, "image/jpeg"));
        }

        return new AnalysisJob(
                storage.createDownloadUrl(reference.getObjectKey()),
                storage.createDownloadUrl(practice.getObjectKey()),
                reference.getChoreographyStartSec(), reference.getChoreographyEndSec(),
                practice.getChoreographyStartSec(), practice.getChoreographyEndSec(),
                imageKeys, imageUploadUrls);
    }

    /**
     * 분석 결과를 저장한다.
     *
     * <p>구간 목록·품질 지표는 JSON 문자열로 보관한다. 조회 조건으로 쓸 일이 없고
     * 구조가 앞으로 바뀔 수 있어 정규화 이득이 없다.
     */
    @Transactional
    public void complete(Long practiceLogId, AiAnalysisResponse response, List<String> imageKeys) {
        AnalysisResult result = analysisResultRepository.findByPracticeLogId(practiceLogId)
                .orElseThrow(() -> new IllegalStateException("결과 행 없음: " + practiceLogId));

        // 분석 서버는 자기가 올린 객체의 키를 모른다(서명 URL만 받았다).
        // 슬롯 번호를 키로 되돌려 구간마다 붙여준다.
        if (response.getTopIssues() != null) {
            for (IssueInfo issue : response.getTopIssues()) {
                Integer slot = issue.getImageSlot();
                if (slot != null && slot >= 0 && slot < imageKeys.size()) {
                    issue.attachImageKey(imageKeys.get(slot));
                }
            }
        }

        result.updateSegmentResult(
                response.getIssueCount(),
                response.getMessage(),
                null,   // 비교 영상은 만들지 않는다 (sync_map으로 대체)
                toJson(response.getTopIssues()),
                toJson(response.getUnreliableSpans()),
                response.getUnreliableNote(),
                toJson(response.getQuality()),
                response.getQuality() != null ? response.getQuality().getWarning() : null,
                toJson(response.getSyncMap()));
    }

    @Transactional
    public void fail(Long practiceLogId, String reason) {
        analysisResultRepository.findByPracticeLogId(practiceLogId)
                .ifPresent(r -> r.markFailed("분석 실패: " + reason));
    }

    private String toJson(Object obj) {
        if (obj == null) {
            return null;
        }
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (Exception e) {
            // 직렬화가 실패해도 분석 자체는 성공한 것이므로 null로 두고 넘어간다.
            log.warn("[결과 직렬화 실패] {}", e.getMessage());
            return null;
        }
    }
}
