package SeSAC.Dance_Assessment.Dto.PracticeLog;

/**
 * 안무 구간 지정 요청.
 *
 * <p>네 값 모두 선택이다. 다만 <b>양쪽 시작 시각이 함께 있어야</b> 정렬 정확도가
 * 올라간다 — 한쪽만 지정하면 두 영상 사이의 시작 시점 차이가 그대로 남는다.
 *
 * <p>끝 시각은 앞뒤 여백이 많을 때만 받으면 된다. 실측상 시작 시각만으로도
 * 대부분의 이득을 얻고 끝 시각의 추가 이득은 4.7%p였다.
 *
 * <p>주의: 프론트의 트림 UI는 <b>정밀해야 한다.</b> 입력 오차가 ±0.5초를 넘으면
 * 개선분이 사라지고, 정렬 밴드보다 오차가 커지면 성능이 급격히 떨어진다.
 * 드래그만으로는 부족하므로 프레임 단위 미세 조정을 함께 제공할 것.
 */
public record TrimRangeRequest(
        Double referenceStartSec,
        Double referenceEndSec,
        Double practiceStartSec,
        Double practiceEndSec) {
}
