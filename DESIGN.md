---
name: ODO
description: 실사용 댄서를 위한 어두운 네온 연습실 — AI가 프로 영상과 내 영상을 비교해 어긋난 동작을 짚어준다
colors:
  bg-primary: "#0a0a0f"
  bg-secondary: "#12121a"
  bg-card: "rgba(255, 255, 255, 0.05)"
  bg-card-hover: "rgba(255, 255, 255, 0.08)"
  signal-pink: "#ff2d75"
  signal-cyan: "#00d9ff"
  signal-purple: "#a855f7"
  text-primary: "#ffffff"
  text-secondary: "rgba(255, 255, 255, 0.7)"
  text-muted: "rgba(255, 255, 255, 0.4)"
  border-color: "rgba(255, 255, 255, 0.1)"
  border-accent: "rgba(255, 45, 117, 0.3)"
  success: "#10b981"
  warning: "#f59e0b"
  error: "#ef4444"
typography:
  display:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "2.5rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "normal"
  headline:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "1.8rem"
    fontWeight: 600
    lineHeight: 1.3
  title:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "1.4rem"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "0.9rem"
    fontWeight: 500
    letterSpacing: "normal"
rounded:
  sm: "12px"
  lg: "20px"
  pill: "999px"
  full: "50%"
spacing:
  xs: "8px"
  sm: "16px"
  md: "20px"
  lg: "24px"
  xl: "32px"
  xxl: "40px"
components:
  button-primary:
    backgroundColor: "{colors.signal-pink}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.sm}"
    padding: "12px 24px"
  button-primary-hover:
    backgroundColor: "{colors.signal-pink}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.sm}"
    padding: "12px 24px"
  button-secondary:
    backgroundColor: "{colors.bg-card}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.sm}"
    padding: "12px 24px"
  button-outline:
    backgroundColor: "transparent"
    textColor: "{colors.signal-pink}"
    rounded: "{rounded.sm}"
    padding: "12px 24px"
  card:
    backgroundColor: "{colors.bg-card}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.lg}"
    padding: "24px"
  badge:
    backgroundColor: "{colors.bg-card}"
    textColor: "{colors.signal-cyan}"
    rounded: "{rounded.pill}"
    padding: "4px 12px"
---

# Design System: ODO

## Overview

**Creative North Star: "The Studio After Hours"**

연습실 불이 꺼진 뒤, 혼자 영상을 되돌려 보며 자기 동작을 맞춰보는 시간. ODO의
화면은 어두운 배경과 네온 포인트로 그 장면을 그대로 옮긴다 — `index.css`가
스스로 적어놓은 컨셉 그대로 "Dark Neon Dance"다. 배경은 거의 검정(`#0a0a0f`)에
가깝고, 그 위에 반투명 유리 카드(backdrop-blur)가 떠 있으며, 신호색(Signal
Pink·Cyan·Purple)이 그라디언트와 네온 글로우로 화면을 밝힌다.

이 정체성 안에는 실제로 관찰되는 색 역할 분담이 하나 있다: **시안(Cyan)은
기준/레퍼런스, 핑크(Pink)는 나의 시도.** 나란히 비교 화면의 태그(`.synced-tag.ref`
= 시안, `.synced-tag.me` = 핑크)와 트리머의 시작/끝 마커(시안/핑크)가 이 규칙을
일관되게 따른다. 이건 장식이 아니라 정보다 — 사용자가 색만 보고 "이건 기준
영상, 이건 내 영상"을 구분한다.

**긴장 메모 — 화려함 vs. 엄밀함.** PRODUCT.md의 첫 번째 원칙은 "엄밀함을 눈에
보이게"다. 그런데 지금 시스템은 헤드라인 숫자(h1, 이슈 개수, 품질 지표)마다
그라디언트 텍스트를 쓰고, 카드 hover마다 네온 글로우가 터진다 — 클럽에 가깝지,
측정 리포트에 가깝지 않다. 이 문서는 지금 구현을 있는 그대로 기록하되, 이
긴장을 숨기지 않는다. 앞으로 `polish`나 `quieter` 작업을 할 때 참고할 절제
방향을 아래 **Colors → Tension Note**에 남겨둔다. 지금 당장 톤을 다시 쓰지는
않는다 — 사용자가 명시적으로 "긴장을 기록하고 메모만 추가"를 선택했다.

**Key Characteristics:**
- 어두운 배경 + 신호색 3종(핑크·시안·퍼플) + 그라디언트
- 평시엔 평평하고 반투명한 유리 카드, hover에만 네온 글로우로 반응 (정적이지 않고 "닿으면 빛난다")
- 헤드라인 숫자는 그라디언트로 클립된 대형 타이포 — 이 제품의 "증거 숫자" 모티프
- 컨트롤(버튼·인풋)은 12px, 컨테이너(카드·업로드존)는 20px — 반경 두 단계
- **아이콘은 현재 전부 이모지다.** 이것은 정체성이 아니라 정리 대상이다 (아래 Don't 참조)

## Colors

배경은 신호색이 빛나 보이도록 존재하는 무대다. 신호색은 세 개뿐이고 각각 역할이 있다.

### Primary
- **Signal Pink** (`#ff2d75`): 주 액션(1차 버튼), 경고/주의, "나의 시도"를 가리키는 색. 가장 많이 등장하는 신호.

### Secondary
- **Signal Cyan** (`#00d9ff`): 포커스 상태, "기준/레퍼런스"를 가리키는 색, 정보성 배지. 핑크와 짝을 이루는 두 번째 신호.

### Tertiary
- **Signal Purple** (`#a855f7`): 단독으로 쓰이지 않고 `signal-gradient`의 중간 정지점으로만 존재한다. 핑크→퍼플→시안 그라디언트를 통해 "두 신호가 하나로 이어진다"는 인상을 만든다.

### Neutral
- **Void Black** (`#0a0a0f`, `bg-primary`): 페이지 배경.
- **Deep Ink** (`#12121a`, `bg-secondary`): 인풋·비디오 컨테이너 등 "안으로 들어간" 표면.
- **Glass Card** (`rgba(255,255,255,0.05)` / hover `0.08`, `bg-card` / `bg-card-hover`): 떠 있는 카드 표면. backdrop-blur(10px)와 항상 짝을 이룬다.
- **White / 70% / 40%** (`text-primary` / `text-secondary` / `text-muted`): 본문 위계 3단.
- **Hairline** (`rgba(255,255,255,0.1)`, `border-color`): 기본 보더.

### Composite: Signal Gradient
`linear-gradient(135deg, #ff2d75, #a855f7, #00d9ff)` — 프리미티브 색이 아니라
합성 값이라 frontmatter에는 올리지 않았다(스펙상 `colors`는 단일 색 값만
허용). 두 곳에 쓰인다: (1) 1차 버튼 배경, (2) 헤드라인 숫자·h1 텍스트를
`background-clip: text`로 클리핑하는 "증거 숫자" 모티프. 세 정지점 색은 위
Primary/Secondary/Tertiary와 동일하다.

### Named Rules
**The Reference/Practice Rule.** 시안은 항상 "기준", 핑크는 항상 "나"를
가리킨다. 새 비교 UI를 만들 때 이 매핑을 뒤집지 않는다 — 사용자가 색으로
구분하는 유일한 단서다.

**The Flat-Until-Touched Rule.** 카드는 평시에 그림자가 없다(`--shadow-card`
토큰은 선언돼 있지만 실제로는 거의 참조되지 않는 죽은 토큰이다). 네온 글로우
(`--shadow-glow`)는 hover·active 같은 반응에서만 나타난다. 정적 화면은 조용하고,
상호작용에만 빛난다.

### Tension Note — 화려함 vs. 엄밀함 (절제 방향 메모)
지금 그라디언트 텍스트는 h1, `issue-count-number`(4rem), `score-value`(레거시),
`issue-badge-value`까지 — 화면에 등장하는 거의 모든 숫자·제목에 걸려 있다.
PRODUCT.md의 "엄밀함을 눈에 보이게" 원칙과 맞추려면, 다음 `quieter`/`polish`
패스에서: (1) 데이터를 담은 숫자(이슈 개수, 품질 지표값)는 그라디언트 대신
`text-primary` 플랫 색 + 굵은 weight로 "측정값"처럼 보이게 하고, (2) 그라디언트는
페이지 h1과 1차 CTA 버튼처럼 "브랜드가 말을 거는" 자리에만 남기는 것을
검토한다. 지금 이 문서는 그 결정을 내리지 않는다 — 현재 구현을 있는 그대로
기록하고, 다음 리파인 작업이 참고할 메모로만 남긴다.

## Typography

**Display/Body/Label Font:** `Inter` (fallback: `-apple-system, BlinkMacSystemFont,
'Segoe UI', sans-serif`)

**주의 — 로드되지 않는 폰트.** `index.css`는 `--font-family`에 Inter를 지정하지만,
`index.html`이나 다른 어디에도 Inter를 실제로 불러오는 `<link>`나 `@import`가
없다. 지금은 조용히 시스템 sans 폴백(macOS는 San Francisco, Windows는 Segoe UI
등)으로 렌더링되고 있다. 토큰상의 의도는 Inter이므로 frontmatter는 선언된 값을
그대로 담았다 — 실제로 Inter를 로드하거나, 폴백이 곧 의도라면 토큰을 정직하게
고칠지는 다음 작업에서 결정한다.

**Character:** 굵은 weight(600~700)의 짧은 제목과, 옅은 회색조(70%/40% 흰색)
본문이 대비를 이룬다. 헤드라인 숫자만 예외적으로 매우 크고(2.5~4rem) 그라디언트로
강조된다.

### Hierarchy
- **Display** (600, 2.5rem, 1.3 line-height): `h1`. 그라디언트 텍스트 클리핑이 기본 적용된다.
- **Headline** (600, 1.8rem, 1.3): `h2`. 섹션 제목.
- **Title** (600, 1.4rem, 1.3): `h3`. 카드/서브섹션 제목.
- **Body** (400, 1rem, 1.6): 본문. `text-secondary`가 기본 문단 색.
- **Label** (500, 0.9rem): 폼 라벨, 메타 텍스트.

### Named Rules
**The Proof Numeral Rule.** 화면에서 가장 중요한 숫자(이슈 개수, 품질 점수)는
본문 타이포 위계를 벗어나 독립적으로 크게(2.5~4rem, 700) 그라디언트 처리된다.
이 숫자들은 장식이 아니라 이 제품이 실제로 증명하는 값이다 — 그래서 시각적으로
가장 크다. (단, 위 Tension Note 참고: 이 처리를 계속 확장할지는 재검토 대상.)

## Layout

**컨테이너:** `max-width: 1200px`, 중앙 정렬, 좌우 패딩 20px.

**헤더:** `position: sticky`, 높이 70px(`--header-height`), 반투명 검정 +
backdrop-blur(10px). 본문(`main-content`)은 헤더 높이만큼 `padding-top`을 받는다.

**페이지:** 상하 패딩 40px, 좌우 20px. 섹션 간 여백은 32~48px.

**그리드:** 카드형 목록은 대부분 `repeat(auto-fit, minmax(X, 1fr))` — X는
맥락에 따라 150px(메타 정보 칩)부터 350px(상세 비교 2단)까지. 고정 컬럼 그리드
(`.grid-2/3/4`)도 유틸리티로 선언돼 있지만 실사용 화면(JSX)에서는 쓰이지 않는
죽은 클래스다.

**반응형 브레이크포인트:**
- `768px`: 헤더 내비게이션 숨김, 대부분의 auto-fit 그리드가 사실상 1열로 줄어듦.
- `720px`: 나란히 비교 화면(`SyncedComparison`)의 좌우 두 영상 패널이 세로로
  쌓이고, 화면 비율이 3:4(세로 영상 기준)에서 16:10으로 바뀐다 — "좁은 화면에서
  좌우로 나누면 동작이 안 보인다"는 실측 판단이 주석으로 남아 있다.
- `600px`: 폼의 2열 행(`form-row`)이 1열로.

## Elevation & Depth

그림자보다 **반투명 + 블러**가 주 깊이 표현이다. 배경의 네온 라디얼 그라디언트
위에 `rgba(255,255,255,0.05)` 카드가 `backdrop-filter: blur(10px)`로 떠 있는
"유리판" 레이어링. 전통적 `box-shadow`는 평시엔 거의 쓰이지 않는다
(`--shadow-card`는 선언만 되고 참조는 드묾).

### Shadow Vocabulary
- **Glow** (`box-shadow: 0 0 20px rgba(255, 45, 117, 0.3)`, `--shadow-glow`):
  hover·active 등 상호작용 응답 전용. 카드 hover, 1차 버튼 hover, 활성 이슈
  구간에 등장. 색은 맥락의 신호색을 따른다(대부분 핑크, 화면별로 시안·퍼플 변형).
- **Ambient Card** (`box-shadow: 0 4px 20px rgba(0,0,0,0.3)`, `--shadow-card`):
  선언은 돼 있으나 관찰된 CSS에서 실제로 참조되는 곳이 없다 — 정리 대상이거나,
  향후 "평시에도 은은한 깊이"가 필요할 때 쓸 수 있는 예비 토큰.

### Named Rules
**The Response-Only Glow Rule.** 네온 글로우는 정적 상태의 장식이 아니라
사용자 행동에 대한 응답이다. 새 컴포넌트에 글로우를 추가할 때는 "이게 hover나
active에 반응하는가"를 먼저 확인한다 — 항상 켜져 있는 글로우는 이 시스템의
문법과 어긋난다.

## Shapes

**두 단계 반경 시스템.** 컨트롤 요소(버튼·인풋·작은 태그)는 12px
(`--border-radius`), 컨테이너(카드·업로드 드롭존·auth 박스·비디오 컨테이너)는
20px(`--border-radius-lg`). 완전한 pill(999px)은 상태 배지·진행률 바·타임라인
트랙에, 완전한 원(50%)은 숫자 배지·아바타·스텝 넘버·스피너에 쓰인다.

보더는 항상 1px 헤어라인(`border-color`)이 기본이고, 강조 상태에서만 신호색
보더(`border-accent`, 핑크 30% 불투명도)로 바뀐다. 점선 보더(`2px dashed`)는
파일 드롭존 전용 문법 — "여기에 놓으세요"라는 뜻으로만 쓰인다.

## Components

### Buttons
- **Shape:** 12px 반경(`--border-radius`), `.btn-lg`/`.btn-sm`은 패딩만 바뀐다.
- **Primary:** Signal Gradient 배경, 흰 텍스트, 패딩 12px 24px. Hover는 `scale(1.02)` + 글로우.
- **Secondary:** 유리 카드 배경(`bg-card`) + 헤어라인 보더. Hover는 `bg-card-hover` + 보더가 시안으로.
- **Outline:** 투명 배경, 핑크 텍스트/보더. Hover는 옅은 핑크 틴트 배경(10% 불투명도).
- **Disabled:** 불투명도 0.5, 커서 `not-allowed`.

### Cards
- **Corner Style:** 20px (`--border-radius-lg`).
- **Background:** `bg-card` (5% 흰색), hover 시 `bg-card-hover` (8%).
- **Shadow Strategy:** 평시 없음 → hover에 Glow(위 Elevation 참고).
- **Border:** 1px 헤어라인 → hover 시 상황에 따라 투명해지거나 신호색 보더로.
- **Internal Padding:** 24px (feature-card는 28px).
- **변형:** `.feature-card`(대시보드, 상단에 hover 시 나타나는 3px 그라디언트 바
  포함), `.assignment-card`/`.log-card`(hover 시 오른쪽으로 4px 밀림 + 화살표 이동).

### Badges
- **Style:** pill 반경(20px 또는 999px 혼용), 4px 12px 패딩, 신호색을 20%
  불투명도 배경 + 해당 신호색 텍스트로.
- **Variants:** success(초록 `#10b981`) / warning(호박 `#f59e0b`) / error(빨강
  `#ef4444`) / info(시안).

### Inputs / Fields
- **Style:** `bg-secondary` 배경, 1px 헤어라인 보더, 12px 반경, 패딩 12px 16px.
- **Focus:** 보더가 시안으로, `box-shadow: 0 0 0 3px rgba(0,217,255,0.1)` 링.
- **Placeholder:** `text-muted`.

### Navigation
- **Header:** sticky, 70px, 반투명 검정 + 블러. 로고 텍스트는 Signal Gradient
  클리핑. 내비 링크는 hover 시 `bg-card` 배경 + 흰 텍스트로. 768px 이하에서
  숨김(현재 모바일 내비 대체 UI 없음 — 아래 Don't 참고).
- **로고:** 실제 로고마크 자산은 없다. 현재는 텍스트("DanceFlow") + 이모지(💃)
  조합뿐이다.

### Signature: Proof Numeral
반경 없는 대형 그라디언트 클립 숫자. 세 가지 크기로 재사용됨: 4rem/700
(`issue-count-number`, 결과 화면의 주인공), 2.5rem/700(`score-value`, 레거시),
1.3rem/700(`issue-badge-value`, 목록의 축약형). 위 Typography → Proof Numeral
Rule 참고.

### Signature: Synced Comparison
이 제품의 핵심 화면. 두 비디오 패널을 나란히(모바일에선 위아래로) 배치하고,
아래 스크럽 가능한 타임라인에 "지적 구간"을 반투명 핑크 마커로 표시, 재생
헤드는 시안 세로선(글로우 포함)으로 그린다. 각 비디오 위 태그는 Reference/Practice
Rule을 따라 시안/핑크로 구분된다.

### Legacy — 확장하지 말 것
- **`.score-display`** (0~100 원형 점수 링, `App.css`): 어떤 JSX에서도 더 이상
  쓰이지 않는다. 제품이 "0~100 점수"에서 "지적 구간 개수"로 지표를 바꾼 뒤
  대체됐다(`LogDetail.css` 주석: "점수 대신 구간 개수 — 환산 상수가 임의값이라
  0~100 점수는 절대값에 의미가 없었다"). 새 화면에 이 패턴을 재사용하지 않는다.
- **`.grid-2` / `.grid-3` / `.grid-4`** (`index.css`): 선언만 되고 실사용
  화면에서는 참조되지 않는 유틸리티.

## Do's and Don'ts

### Do:
- **Do** 시안=기준/레퍼런스, 핑크=나의 시도 매핑을 모든 비교 UI에서 지킨다(The Reference/Practice Rule).
- **Do** 카드·버튼은 평시 평평하게, 글로우는 hover·active 응답으로만 켠다(The Response-Only/Flat-Until-Touched Rule).
- **Do** 반경은 12px(컨트롤)/20px(컨테이너) 두 단계만 쓴다. 세 번째 반경 값을 새로 만들지 않는다.
- **Do** 데이터 숫자(이슈 개수·품질 지표)를 강조할 땐 Proof Numeral 모티프를 재사용하되, Tension Note의 절제 방향을 다음 리파인 패스에서 검토한다.

### Don't:
- **Don't** 장식용·AI 클리셰 이모지를 새로 추가하지 않는다 (PRODUCT.md의 확정된 브랜드 제약). **지금 구현은 이 규칙을 전면적으로 어기고 있다** — 헤더 로고(💃), 모든 페이지 제목(🎯📋📊 등), 모든 빈 상태 아이콘, 업로드 아이콘, 대시보드 피처 카드 아이콘까지 이모지다. 이건 이 디자인 시스템의 정체성이 아니라 **1순위 정리 대상**이다. 아이콘이 필요하면 인라인 SVG나 절제된 타이포/도형으로 바꾼다. (`←`/`→` 같은 방향 화살표 글리프는 장식이 아니라 내비게이션 기능이므로 이 금지에 해당하지 않는다.)
- **Don't** `.score-display`(0~100 원형 점수 링)를 새 화면에 재사용하지 않는다 — 이미 대체된 죽은 패턴이다.
- **Don't** 그라디언트 텍스트 처리를 지금보다 더 확장하지 않는다 — Tension Note 참고, 이미 포화 상태다.
- **Don't** `--font-family`가 Inter를 선언한다고 해서 실제로 Inter가 로드되고 있다고 가정하지 않는다 — 지금은 시스템 폰트 폴백으로 렌더링된다.
- **Don't** 768px 이하에서 내비게이션을 완전히 숨긴 채로 두지 않는다 — 현재 모바일 대체 내비(햄버거 메뉴 등)가 없어 화면이 좁아지면 대시보드/숙제/기록으로 갈 방법이 헤더 로고 클릭(홈)뿐이다. 모바일이 1급 사용 환경이라는 PRODUCT.md 원칙과 맞지 않는다.
