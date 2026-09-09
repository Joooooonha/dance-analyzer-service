import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// --font-family가 Inter를 선언하지만 예전에는 실제로 로드하는 곳이 없어
// 시스템 폰트로 조용히 대체되고 있었다. 필요한 굵기만 셀프호스팅으로 불러온다.
//
// Inter에는 한글이 없다 — 한국어 문장은 이 폰트를 걸어도 자동으로 다음
// 폴백(시스템 고딕)으로 렌더링된다. 여기서 실제로 그려지는 건 영문·숫자
// (타임스탬프, "DTW" 같은 용어, 퍼센트 등)뿐이므로 라틴 서브셋만 불러온다 —
// 키릴·그리스·베트남어까지 받으면 브라우저가 요청하지도 않을 파일이 배포
// 산출물에 40개 넘게 딸려온다.
import '@fontsource/inter/latin-400.css'
import '@fontsource/inter/latin-500.css'
import '@fontsource/inter/latin-600.css'
import '@fontsource/inter/latin-700.css'
import '@fontsource/inter/latin-ext-400.css'
import '@fontsource/inter/latin-ext-500.css'
import '@fontsource/inter/latin-ext-600.css'
import '@fontsource/inter/latin-ext-700.css'
import './index.css'
import App from './App.jsx'
import { registerServiceWorker } from './push'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// 서비스 워커를 미리 등록해둔다.
//
// 알림을 켜는 시점에 등록하면 등록이 끝나기를 기다렸다가 권한 요청을 하게 되는데,
// 그 사이에 "사용자 동작" 맥락이 끊겨 브라우저가 권한 창을 무시하는 경우가 있다.
// 실패해도 앱은 정상 동작한다 — 알림만 못 쓴다.
registerServiceWorker()
