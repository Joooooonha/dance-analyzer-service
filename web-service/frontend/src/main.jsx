import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
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
