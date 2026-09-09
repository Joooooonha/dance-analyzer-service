---
name: ODO
description: 안무 카운트보드 — 댄서가 손으로 세던 카운트를 앱이 대신 짚어준다 (연습장 크림지 + 형광펜 강조)
colors:
  cb-paper: "#f5f1e8"
  cb-paper-card: "#fbf9f3"
  cb-ink: "#2c2a26"
  cb-ink-secondary: "rgba(44, 42, 38, 0.68)"
  cb-ink-muted: "rgba(44, 42, 38, 0.44)"
  cb-rule: "rgba(44, 42, 38, 0.16)"
  cb-highlight: "#f5e211"
  cb-highlight-soft: "rgba(245, 226, 17, 0.4)"
  cb-highlight-wash: "#f8f0a8"
  cb-cyan: "#026a7d"
typography:
  display:
    fontFamily: "'Noto Sans KR', Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "1.6rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "normal"
  numeral:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "3rem"
    fontWeight: 700
    lineHeight: 1
    fontFeature: "tabular-nums"
  title:
    fontFamily: "'Noto Sans KR', Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "1.15rem"
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: "'Noto Sans KR', Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "0.9rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "'Noto Sans KR', Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "0.85rem"
    fontWeight: 700
    letterSpacing: "0.04em"
  script-accent:
    fontFamily: "'Nanum Pen Script', cursive"
    fontSize: "1.5rem"
    fontWeight: 400
    lineHeight: 1.3
rounded:
  sm: "4px"
spacing:
  xs: "8px"
  sm: "16px"
  md: "20px"
  lg: "24px"
  xl: "28px"
  xxl: "32px"
components:
  cell:
    backgroundColor: "{colors.cb-paper-card}"
    textColor: "{colors.cb-ink}"
    rounded: "{rounded.sm}"
    padding: "22px 24px 24px"
  cell-hover:
    backgroundColor: "{colors.cb-highlight-wash}"
    textColor: "{colors.cb-ink}"
    rounded: "{rounded.sm}"
    padding: "22px 24px 24px"
  strip:
    backgroundColor: "{colors.cb-paper-card}"
    textColor: "{colors.cb-ink}"
    rounded: "{rounded.sm}"
    padding: "20px 24px"
  guide-cta:
    backgroundColor: "{colors.cb-ink}"
    textColor: "{colors.cb-paper}"
    rounded: "{rounded.sm}"
    padding: "10px 20px"
---

# Design System: ODO

## Overview

**Creative North Star: "안무 카운트보드" (Choreography Count Board)**

`ODO`의 대시보드는 아이콘+제목+설명 카드 그리드라는 이 카테고리의 기본값을 거부한다. 댄서가 이미 손으로 세던 카운트를 앱이 대신 짚어주는 판이다: 연습장 크림지(`#f5f1e8`) 배경 위에 흑연 잉크(`#2c2a26`) 텍스트, 형광펜 옐로(`#f5e211`) 단 하나의 강조색. 유리 카드도, 네온 글로우도, 아이콘도 없다 — 종이 판 하나를 두르고 칸 사이를 헤어라인으로만 가른다.

이 세계관은 finish review를 거치며 초기 방향에서 두 가지가 정정됐다: (1) 칸마다 개별 그림자를 주는 대신 판 전체를 감싸고 `grid gap`을 잉크색으로 채워 헤어라인만 남기는 **공유 격자**로 바뀌었고, (2) hover 반응은 그림자나 들어올림이 아니라 그 자리를 형광펜으로 한 번 덮어씌운 듯한 배경 전환(`--cb-highlight-wash`, 불투명)으로 표현한다 — 카운트 스트립 숫자 밑에 깔리는 얇은 스윕(`--cb-highlight-soft`, 반투명)과는 다른 토큰이다. 이 둘을 섞으면 격자선과 탁하게 섞여 대비가 무너지기 때문에 의도적으로 분리했다.

시안(기준/레퍼런스)·핑크(나의 시도) 기능색 매핑은 옛 네온 시스템에서 넘어온 정보 색이다. 이 화면에는 아직 비교 배지가 없어 시안만 링크 hover·포커스 링에 쓰이고(크림 배경에서 4.5:1을 내도록 눌러 재조정: `#026a7d`), 핑크는 자리가 없다 — 비교 화면이 이 세계관으로 옮겨올 때 함께 다뤄질 몫이다.

**Key Characteristics:**
- 연습장 크림 배경 + 흑연 잉크 텍스트 + 형광펜 옐로 단일 강조, 시안은 기능색으로만 잔류
- 카드 그리드가 아니라 하나의 공유 판 — 칸 사이는 1px 헤어라인, 개별 그림자 없음
- Hover/focus는 그림자가 아니라 불투명 형광펜 워시 배경 전환
- 27px 간격 가는 헤어라인 리페어팅 그래디언트로 만든 노트 격자 텍스처
- 손글씨풍 서체(Nanum Pen Script)는 화면 전체에서 딱 한 곳(`처음이신가요?` 안내 제목)에만 절제해서 등장
- 숫자만 Inter 고정폭(tabular-nums)으로 명시 고정 — Noto Sans KR 서브셋에 라틴 숫자 unicode-range가 없어 방치하면 한글 서체로 끌려가기 때문

## Colors

크림 종이 위에 잉크, 그 위에 단 하나의 형광펜 — 색의 숫자를 줄인 만큼 그 하나가 뜻을 가진다.

### Primary
- **형광펜 옐로 Highlight** (`#f5e211`): 유일한 강조색. 카운트 스트립 링크의 밑줄, `::selection`, 숫자가 갱신될 때의 스윕 애니메이션에 쓰인다. 배경으로는 절대 그대로 깔리지 않는다 — 배경으로 쓸 땐 대비 재계산을 거친 `cb-highlight-wash`(`#f8f0a8`, 불투명)로 갈아탄다.

### Secondary
- **눌린 시안 Cyan** (`#026a7d`): 옛 네온 세계관의 "기준/레퍼런스" 기능색을 크림 배경에서 4.5:1이 나오도록 재조정한 값. 링크 hover, 셀 `focus-visible` 아웃라인에 쓰인다.

### Neutral
- **연습장 크림 Paper** (`#f5f1e8`, `cb-paper`): 페이지 배경.
- **카드 크림 Paper Card** (`#fbf9f3`, `cb-paper-card`): 스트립·칸·안내 박스의 표면 — 배경보다 살짝 밝다.
- **흑연 잉크 Ink** (`#2c2a26`, `cb-ink`): 제목·숫자·본문 강조 텍스트.
- **잉크 68% Ink Secondary** (`rgba(44,42,38,0.68)`): 본문·설명·라벨의 기본 색. 44% 잉크(`cb-ink-muted`)는 본문 텍스트로 쓰기엔 대비가 부족해 테두리류 비-텍스트 용도로만 남는다.
- **헤어라인 Rule** (`rgba(44,42,38,0.16)`): 격자 텍스처, 칸 사이 구분선, 스트립·안내 박스 보더.

### Named Rules
**The One Yellow Rule.** 형광펜 강조는 이 세계관에서 단 하나뿐이다. 새 강조가 필요할 때 두 번째 액센트 색을 만들지 않는다 — 형광펜 위치를 늘리거나(밑줄, 워시, 스윕), 절제된 잉크 굵기로 해결한다.

**The Wash-vs-Soft Rule.** 배경으로 칠하는 형광펜(hover 워시)과 텍스트 밑에 까는 형광펜(숫자 스윕)은 서로 다른 토큰이다 — `cb-highlight-wash`(불투명)는 배경 전용, `cb-highlight-soft`(반투명)는 오버레이 전용. 반투명 값을 배경색으로 그대로 쓰면 밑에 깔린 격자선과 탁하게 섞여 대비가 무너진다.

## Typography

**Body/Display Font:** `Noto Sans KR` (한글, korean 서브셋 셀프호스팅)
**Numeral Font:** `Inter` (라틴/숫자 전용, latin + latin-ext 서브셋)
**Signature Accent Font:** `Nanum Pen Script` (korean 서브셋) — 안내 제목 한 곳에만

**Character:** 한글 워크호스는 Noto Sans KR, 숫자는 Inter로 명시적으로 고정한 이중 서체 체계다. Noto Sans KR의 korean 서브셋에는 라틴 숫자용 unicode-range가 없어, 고정하지 않으면 이 화면에서 가장 중요한 증거 숫자가 조용히 한글 서체로 그려진다 — 그래서 `.cb-strip-number`만 `font-family: Inter, ...`를 다시 선언한다. Nanum Pen Script는 기울인 고딕이 아니라 실제 손글씨 서체이며, 화면 전체에서 단 한 곳(첫 방문자 안내 제목)에만 쓰고 `-1deg` 회전으로 손으로 쓴 인상을 준다.

### Hierarchy
- **Display** (700, 1.6rem, 1.3): `h1` 인사말. 그라디언트 클리핑 없이 순수 잉크색.
- **Numeral** (700, 3rem→2.25rem@480px, 1, tabular-nums, Inter 고정): 카운트 스트립의 증거 숫자. 이 화면의 유일한 대형 타이포.
- **Title** (700, 1.15rem, 1.3): 칸 제목(`cb-cell-title`).
- **Body** (400, 0.9~0.95rem, 1.5): 칸 설명, 스트립 라벨/상태 문구.
- **Label** (700, 0.85rem, letter-spacing 0.04em): 칸 번호(`01`/`02`/`03`) — 대문자 표기 없이 두 자리 숫자로 위계를 만든다.
- **Script Accent** (400, 1.5rem, cursive, -1deg 회전): 안내 박스 제목 한 곳 전용.

### Named Rules
**The Tabular Numeral Rule.** 화면에서 가장 중요한 숫자(지적 구간 개수)는 Inter로 명시 고정하고 `font-variant-numeric: tabular-nums`를 건다. 한글 서체 폴백에 맡기지 않는다 — 자릿수가 바뀌어도 숫자 폭이 흔들리지 않아야 "증거"로 읽힌다.

**The One Script Rule.** 손글씨풍 서체는 화면당 한 곳으로 제한한다. 두 곳 이상에 쓰면 손글씨가 장식이 되어 이 세계관의 절제가 무너진다.

## Layout

칸 그리드는 `repeat(auto-fit, minmax(220px, 1fr))`로 반응형 열 수를 결정하고, 리더 전용 칸(`cb-cells-leader`)은 단일 열·최대폭 340px로 별도 판을 이룬다. 스트립과 칸 판 사이 간격은 32px, 칸 판과 안내 박스 사이는 20px. 페이지 상단 패딩 40px, 하단 60px. 480px 이하에서 스트립이 세로로 쌓이고 증거 숫자가 3rem→2.25rem로 줄어든다.

배경의 27px 간격 헤어라인 리피팅 그래디언트가 노트 격자 텍스처를 만든다 — 텍스트 아래 깔려도 줄당 1px·16% 불투명도라 본문 대비율에 영향이 없다고 확인됐다.

## Elevation & Depth

그림자를 쓰지 않는다. 깊이는 헤어라인 경계와 배경색 전환만으로 표현한다: 칸 판 전체는 `grid gap`을 잉크색 헤어라인으로 채우고 각 칸 배경을 카드 크림으로 덮는 트릭으로, 열 개수가 반응형으로 바뀌어도 인접한 자리에만 선이 생긴다. 상호작용 반응도 그림자나 들어올림 대신 배경색 전환(형광펜 워시)으로만 낸다.

### Named Rules
**The No-Shadow Rule.** 이 세계관에 `box-shadow`는 존재하지 않는다. 깊이·상태·강조는 전부 헤어라인, 배경색 전환, 밑줄 두께로만 표현한다. 옛 네온 세계관의 글로우(`--shadow-glow`)를 이 화면에 들여오지 않는다.

## Shapes

반경은 4px 하나뿐이다(`cb-strip`, `cb-cells`, `cb-cell` 없음—칸 자체는 반경 없이 판의 외곽만 4px, 칸 내부 경계는 직각), 스트립·판·안내 박스·CTA 버튼에 일괄 적용된다. 옛 시스템의 12px/20px 두 단계나 pill/circle 반경은 이 세계관에 없다. 안내 박스만 예외적으로 점선 보더(`1px dashed`)를 쓴다 — 옛 세계관에서 파일 드롭존 전용이던 문법을 "아직 채워지지 않은 자리"라는 같은 의미로 재사용한다.

## Components

### Count Strip (Signature)
카운트 스트립은 이 화면의 증거 컴포넌트다. 배경 `cb-paper-card`, 1px 헤어라인 보더, 4px 반경, 패딩 20px 24px. 최근 분석이 완료 상태면 큰 Inter 숫자(3rem/700)를 형광펜 스윕 애니메이션(0.6s ease-out, `scaleX(0)→1`)과 함께 보여준다. 진행 중/대기/실패/빈 상태는 각각 다른 한 줄 문구로 대체되며 숫자 자리를 비운다 — 상태를 감추지 않는다는 제품 원칙을 그대로 반영한다.

### Count Cells (Signature)
카드가 아니라 판이다. 판 전체(`cb-cells`)가 1px 헤어라인 보더 + 4px 반경 + `overflow: hidden`을 두르고, 개별 칸(`cb-cell`)은 보더나 반경 없이 배경만 카드 크림으로 채운다. 칸 사이 구분은 `grid gap: 1px`을 잉크색으로 채워서 만든다. 아이콘 대신 두 자리 칸 번호(`01`/`02`/`03`)로 구분한다. Hover/focus는 배경이 `cb-highlight-wash`로 전환되고, focus-visible은 추가로 시안 아웃라인(`outline-offset: -2px`)을 얻는다.

### Guide Box
첫 기록이 없는 사용자에게만 나타나는 안내. 배경 `cb-paper-card`, 1px 점선 헤어라인 보더, 4px 반경, 패딩 24px. 제목만 손글씨 서체(Nanum Pen Script, -1deg 회전). CTA는 잉크색 배경 + 크림 텍스트의 솔리드 버튼(4px 반경, 패딩 10px 20px, hover는 opacity 0.82).

### Navigation
칸 자체가 내비게이션 링크다 (`<Link className="cb-cell">`) — 별도 버튼이나 화살표 없이 칸 전체가 클릭 영역이다.

## Do's and Don'ts

### Do:
- **Do** 강조는 형광펜 옐로 하나로 제한한다 (The One Yellow Rule).
- **Do** 배경용 형광펜과 오버레이용 형광펜을 구분한다 — `cb-highlight-wash`는 배경, `cb-highlight-soft`는 텍스트 위 오버레이 (The Wash-vs-Soft Rule).
- **Do** 증거 숫자는 Inter + tabular-nums로 명시 고정한다, 한글 서체 폴백에 맡기지 않는다 (The Tabular Numeral Rule).
- **Do** 깊이는 헤어라인과 배경 전환으로만 표현한다. `box-shadow`를 새로 추가하지 않는다 (The No-Shadow Rule).
- **Do** 손글씨 서체는 화면당 한 곳으로 제한한다 (The One Script Rule).

### Don't:
- **Don't** 칸마다 개별 카드 그림자·라운드·보더를 주지 않는다 — 판 하나 + 헤어라인 구분이 이 세계관의 카드 그리드 대체 문법이다. finish review에서 개별 카드 그림자 시도가 정정된 이력이 있다.
- **Don't** 아이콘(이모지든 SVG든)을 칸 구분에 쓰지 않는다 — 두 자리 칸 번호가 그 역할을 한다. 이모지 자체는 PRODUCT.md의 전면 금지 대상이기도 하다.
- **Don't** 이 화면의 시안 값(`#026a7d`)을 옛 네온 세계관의 시안(`#00d9ff`)과 섞어 쓰지 않는다 — 크림 배경용으로 대비를 다시 계산한 별개 값이다.
- **Don't** Noto Sans KR 서브셋에 숫자를 맡기지 않는다 — korean 서브셋에는 라틴 숫자 unicode-range가 없어 조용히 잘못된 서체로 렌더링된다.

## Migration Status

**이 시스템은 현재 `Dashboard.jsx` 한 화면에만 적용됐다.** 위 토큰·규칙은 안무 카운트보드가 완성된 형태로 도착한 유일한 표면을 기록한 것이며, 앱의 목표 정체성(사용자가 "앱 전체의 정체성을 다시 설계"로 이번 라운드 범위를 선택함)이지 이미 전면 적용된 상태가 아니다.

**아직 옛 "The Studio After Hours"(다크 네온) 세계관을 그대로 쓰는 화면/컴포넌트:**
- `Header` (로고·내비게이션)
- `Login`, `Signup`
- `Practice`
- `Assignments`, `AssignmentDetail`, `AssignmentCreate`
- `Logs`, `LogDetail`
- `SyncedComparison`
- `VideoUploader`, `VideoTrimmer`
- 전역 `index.css` / `App.css`의 `:root` 토큰(`--bg-primary`, `--accent-pink`, `--accent-cyan`, `--accent-gradient`, `--shadow-glow` 등) — grep으로 확인: `--cb-` 프리픽스 토큰은 `Dashboard.css` 밖에서 전혀 참조되지 않는다.

이 화면들에는 이 문서의 `colors`/`typography`/`components` 토큰이 적용되지 않는다 — 여전히 옛 시스템(Signal Pink/Cyan/Purple, 유리 카드, 네온 글로우, Inter 미로드 폴백)을 따른다. 그 옛 시스템의 세부 규칙(색 역할, 반경 2단계, 글로우 문법, 이모지 정리 대상 등)은 이 문서 이전 버전에 전부 기록돼 있었으며, git 이력에서 확인 가능하다 — 해당 화면들이 실제로 이 새 세계관으로 이관되기 전까지는 그 옛 문서의 내용이 이 화면들을 정확히 설명하는 것으로 취급한다. 옛 문서 내용을 지우지 않고 이 섹션으로 대체한 이유는, 다음에 저 화면 중 하나를 여는 에이전트가 이 새 DESIGN.md의 크림/형광펜 토큰을 그 화면에도 이미 적용된 것으로 오인하지 않도록 하기 위함이다.
</content>
