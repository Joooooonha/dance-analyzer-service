package SeSAC.Dance_Assessment.Dto.PracticeLog;

import SeSAC.Dance_Assessment.Domain.AnalysisStatus;
import SeSAC.Dance_Assessment.Dto.Ai.AiProgressResponse;

/**
 * 분석 진행 상황 응답.
 *
 * <p>상세 조회({@code GET /practice-logs/{id}})와 <b>따로 둔 이유</b>: 진행률을
 * 알려면 분석 서버에 물어봐야 하는데, 그걸 상세 조회 안에 넣으면 분석 서버가
 * 꺼져 있을 때 결과 화면 전체가 열리지 않는다. 이미 끝난 분석을 보는 데
 * 분석 서버가 살아 있어야 할 이유는 없다.
 *
 * <p>그래서 이 엔드포인트는 <b>실패해도 되는 부가 정보</b>다. 분석 서버에
 * 닿지 못하면 {@code stage}가 null인 채로 상태만 돌려준다.
 *
 * @param status    Spring이 아는 분석 상태 (권위 있는 값)
 * @param stage     분석 서버가 지금 돌고 있는 단계. 모르면 null
 * @param label     사용자에게 보여줄 단계 문구. 모르면 null
 * @param pct       현재 단계가 시작되는 지점(%)
 * @param nextPct   현재 단계가 끝나는 지점(%). 그 사이는 화면이 알아서 채운다
 * @param elapsedSec 분석 서버 기준 경과 시간(초)
 */
public record AnalysisProgressResponse(
        AnalysisStatus status,
        String stage,
        String label,
        Double pct,
        Double nextPct,
        Double elapsedSec) {

    /** 분석 서버에 닿지 못했거나 다른 작업이 돌고 있을 때. */
    public static AnalysisProgressResponse unknown(AnalysisStatus status) {
        return new AnalysisProgressResponse(status, null, null, null, null, null);
    }

    public static AnalysisProgressResponse of(AnalysisStatus status, AiProgressResponse ai) {
        return new AnalysisProgressResponse(
                status, ai.getStage(), ai.getLabel(),
                ai.getPct(), ai.getNextPct(), ai.getElapsedSec());
    }
}
