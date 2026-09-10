// 연습 기록(PracticeLog)의 상태값 → 한국어 라벨.
//
// Logs.jsx에 있던 매핑을 여기로 옮겼다. LogDetail.jsx의 "상세 정보" 패널이
// `log.status`를 영어 원문(COMPLETED/PROCESSING/...) 그대로 노출하고 있었는데,
// 분석 대기를 안심시켜야 할 바로 그 화면에서 "이거 미완성 아닌가" 하는
// 인상을 주는 게 가장 눈에 띄는 문제였다 — 두 화면이 각자 매핑을 들고
// 있다가 어긋나는 것도 막는다.
export function getStatusLabel(status) {
    switch (status) {
        case 'COMPLETED': return '완료';
        case 'PROCESSING': return '분석 중';
        case 'WAITING': return '대기 중';
        case 'FAILED': return '실패';
        default: return status;
    }
}
