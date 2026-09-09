# 배포 — 콘솔 작업 체크리스트

**이 문서는 "박준하가 브라우저에서 직접 해야 하는 일"만 모은 것이다.**
코드로 대신할 수 없는 것들(도메인 구매, 외부 서비스 앱 등록, 키 발급)이라
작업이 막히면 여기부터 확인한다.

- 작업 진행 상황은 `TASKS-SERVICE.md`의 Phase S5를 본다.
- 발급받은 값은 **이 파일에 적지 말 것.** 아래 "값 전달" 절 참고.

---

## 진행 순서

도메인이 다른 모든 등록의 입력값이라 **0번이 먼저**다.
나머지 1~6은 순서 상관없다.

| # | 작업 | 이게 없으면 막히는 것 |
|---|---|---|
| 0 | 도메인 구매 | OAuth redirect URI 등록, HTTPS |
| 1 | R2 버킷 + API 토큰 | 영상 업로드/저장 전체 |
| 2 | 카카오 개발자 앱 등록 | 카카오 로그인 |
| 3 | 네이버 개발자 앱 등록 | 네이버 로그인 |
| 4 | EC2 확인/확장 | Spring + DB 배포 |
| 5 | Tailscale 설치 | EC2 → 맥미니 분석 요청 |
| 6 | 맥미니 서비스 설정 | 재부팅 후 자동 복구 |

> **코드 작업은 도메인 없이도 진행 가능하다.** `localhost` redirect URI로
> 먼저 짜두고, 도메인이 정해지면 설정값만 채운다.

---

## 0. 도메인 — 가비아 구매 + Cloudflare DNS

**실제로 진행한 경로** (Cloudflare Registrar는 신규 등록이 아니라 이전만 가능하고
가격도 더 비쌌다. 등록기관은 어디든 상관없고 **DNS만 Cloudflare로 넘기면**
CDN·HTTPS·프록시는 동일하게 쓸 수 있다.)

- [x] 가비아에서 도메인 구매 → **odostudio.site**
- [x] Cloudflare에 사이트 추가 (Add a Site, Free 플랜) → 배정된 네임서버 확인
- [x] 가비아 DNS 설정에서 네임서버를 Cloudflare 것으로 변경
- [ ] Cloudflare 대시보드에서 상태가 **Active**로 바뀌었는지 확인
      (네임서버 반영에 보통 수십 분, 최대 24시간)
- [ ] SSL/TLS 모드를 **Full (strict)** 로 설정
      — Flexible로 두면 Cloudflare↔EC2 구간이 평문이 된다
- [ ] DNS A 레코드 추가 (EC2 퍼블릭 IP 확정 후, 프록시 ON)

**구조 결정: 단일 도메인 + 경로 분리** (쿠키 인증이 가장 단순해진다)

```
https://odostudio.site/          → 프론트엔드
https://odostudio.site/api/...   → Spring
```

> ⚠️ 가비아에서 산 도메인은 **가비아 DNS 설정 화면이 아니라 Cloudflare 대시보드**에서
> 레코드를 관리하게 된다. 네임서버를 넘긴 뒤에는 가비아 쪽 DNS 레코드는 무시된다.

## 1. Cloudflare R2 — 영상 저장소

- [ ] **R2 → Create bucket** — 이름 예: `dance-videos`
- [ ] 위치: **Asia-Pacific (APAC)**
- [ ] **R2 → Manage API Tokens → Create API Token**
      - 권한: **Object Read & Write**
      - 대상: 위에서 만든 버킷만
- [ ] 발급값 3개 보관: `Access Key ID`, `Secret Access Key`, `Endpoint`
- [ ] **버킷 → Settings → CORS Policy** 등록 (아래 JSON)
- [ ] (선택) **Object lifecycle rules** — 결과 이미지 30일 후 자동 삭제

CORS는 **브라우저가 R2로 직접 업로드**하기 때문에 필수다.
이걸 안 하면 업로드가 CORS 오류로 막힌다.

```json
[
  {
    "AllowedOrigins": ["https://odostudio.site", "http://localhost:5173"],
    "AllowedMethods": ["PUT", "GET"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

> ⚠️ **버킷 Public access는 켜지 않는다.** 공개하면 URL을 아는 누구나 접근할 수 있어
> "본인 또는 같은 팀 기준영상만 조회" 규칙이 무력화된다.
> 조회는 Spring이 권한 확인 후 발급하는 짧은 presigned URL로만 한다.

---

## 2. 카카오 개발자

https://developers.kakao.com → 내 애플리케이션 → 애플리케이션 추가

- [ ] 앱 생성
- [ ] **앱 키 → REST API 키** 복사
- [ ] **앱 설정 → 플랫폼 → Web** 사이트 도메인 등록
      - `https://odostudio.site`
      - `http://localhost:8080`
- [ ] **카카오 로그인 → 활성화 ON**
- [ ] **카카오 로그인 → Redirect URI** 등록
      - `https://odostudio.site/login/oauth2/code/kakao`
      - `http://localhost:8080/login/oauth2/code/kakao`
- [ ] **카카오 로그인 → 동의항목** — 닉네임: **필수 동의**
- [ ] **보안 → Client Secret 생성 → 활성화 ON** → 값 복사

> 💡 **이메일은 요청하지 않는다.** 카카오에서 이메일 제공은 비즈앱 전환이나 검수가
> 필요할 수 있다. 닉네임 + 카카오 고유 ID만으로 계정을 만들도록 설계했다.

> 💡 Redirect URI의 `/login/oauth2/code/kakao`는 Spring Security의 기본 규칙이라
> 임의로 바꾸면 코드도 같이 고쳐야 한다. 그대로 둘 것.

---

## 3. 네이버 개발자

https://developers.naver.com → Application → 애플리케이션 등록

- [ ] 애플리케이션 등록
- [ ] 사용 API: **네이버 로그인**
- [ ] 제공 정보: **닉네임** (필요 최소한만)
- [ ] 환경 추가: **PC 웹**
- [ ] 서비스 URL: `https://odostudio.site`
- [ ] Callback URL 등록
      - `https://odostudio.site/login/oauth2/code/naver`
      - `http://localhost:8080/login/oauth2/code/naver`
- [ ] **Client ID / Client Secret** 복사

---

## 4. AWS EC2 — 새 인스턴스 생성

기존 `finder-server`(t4g.small, 2GB)에 합치지 않고 **새로 만든다.**
2GB에는 Spring+Postgres가 안 들어가고, 합치면 이 프로젝트를 만질 때마다
finder-server가 같이 위험해진다.

- [ ] EC2 → 인스턴스 시작

| 항목 | 값 |
|---|---|
| 이름 | `dance-server` (예시) |
| AMI | **Ubuntu 24.04 LTS — arm64** |
| 인스턴스 유형 | **`t4g.small`** (부족하면 나중에 `t4g.medium`) |
| 리전 | `ap-northeast-2` (서울) |
| 키 페어 | 새로 만들거나 기존 것 재사용 |
| 스토리지 | gp3 20GB |

- [ ] **Elastic IP 할당 후 연결**
      (없으면 인스턴스를 재시작할 때마다 IP가 바뀌어 DNS가 깨진다)
- [ ] 보안 그룹 설정

| 포트 | 소스 | 비고 |
|---|---|---|
| 443 | 0.0.0.0/0 (나중에 Cloudflare 대역으로 좁힘) | HTTPS |
| 80 | 0.0.0.0/0 | HTTPS로 리다이렉트용 |
| 22 | **내 IP만** | SSH |
| ~~8080~~ | **열지 않음** | Spring은 127.0.0.1에만 바인딩 |
| ~~5432~~ | **열지 않음** | Postgres는 localhost만 |

> ⚠️ **ARM(Graviton) 인스턴스다.** AMI를 고를 때 반드시 **arm64**를 선택해야 한다.
> x86 AMI를 고르면 `t4g` 타입 자체가 선택지에 안 뜬다.

- [ ] 생성 후 SSH 접속 확인, 퍼블릭 IP 기록

서버 안에서 하는 패키지 설치·설정은 `deploy/README.md`에 있다.

## 5. Tailscale — EC2 ↔ 맥미니 연결

- [ ] Tailscale 계정 생성 (개인용 무료, GitHub 로그인 가능)
- [ ] **맥미니**에 설치 — https://tailscale.com/download/mac 의 **공식 pkg**
- [ ] **EC2**에 설치: `curl -fsSL https://tailscale.com/install.sh | sh`
- [ ] 두 기기의 Tailscale IP(`100.x.x.x`) 확인 (`tailscale ip -4`)

> ⚠️ 맥미니는 **App Store 버전을 쓰면 안 된다.** App Store 버전은 사용자가 로그인해야
> 연결되므로 재부팅 후 EC2가 맥미니를 찾지 못한다. 공식 pkg는 시스템 데몬으로 동작한다.

이 구조에서 **맥미니는 공인 IP가 필요 없다.** EC2만 Tailscale 내부망으로 접근한다.

---

## 6. 맥미니 — 패키지 설치 + 상시 가동 설정

**환경**: Fedora Linux Asahi Remix 44 (Apple Silicon 위 Linux, aarch64), 8코어 / 16GB

- [x] `sudo dnf install -y git python3.10 python3.10-devel`
- [x] `sudo dnf install -y ffmpeg-free` ⚠️ **필수**
- [ ] 방화벽: Tailscale 존에만 8000 포트 열기
      ```
      sudo firewall-cmd --zone=coco-management --add-port=8000/tcp --permanent
      sudo firewall-cmd --reload
      ```
- [ ] 재부팅 후 자동 시작: `sudo loginctl enable-linger $(whoami)`

> **ffmpeg-free를 빼면 조용히 망가진다.** 영상 회전 메타데이터를 `ffprobe`로
> 읽는데, 없으면 세로로 촬영한 영상이 **옆으로 누운 채** 분석된다.
> 실측 피해: 관절 유효율 0.909 → 0.809, 평균 오차 25도 → 31도, 채점률 85% → 65%.
> 에러가 나지 않아서 결과만 나빠지고 원인을 알 수 없다.

> **Python 3.10을 쓰는 이유**: 기본 파이썬이 3.14인데 torch 휠이 cp310~cp313까지만
> 있다. 3.14로는 설치되지 않는다.



- [ ] 절전 해제: `sudo pmset -a sleep 0 disablesleep 1`
- [ ] AI 서버를 **launchd 서비스로 등록** (plist는 코드 작업 단계에서 전달)
- [ ] 전원/인터넷 상시 연결, 재시작 후 자동 복구 확인 ✅ (이미 설정됨)

> 터미널에서 `uvicorn`을 직접 띄우면 세션이 끊길 때 같이 죽는다. 반드시 서비스로 등록한다.

---

## 7. Cloudflare — 서비스 워커 캐시 한 번 비우기

**설정은 바꿀 필요 없다.** 처음에 "Browser Cache TTL을 Respect Existing Headers로
바꾸라"고 적었는데 틀렸다. Cloudflare는 오리진 헤더를 이미 존중하고 있다.

캐시 우회로 확인하면 오리진 헤더가 그대로 온다:

```bash
curl -sI "https://odostudio.site/sw.js?cachebust=1" | grep -iE "cache-control|cf-cache"
```

```
cache-control: no-cache, no-store, must-revalidate
cf-cache-status: BYPASS
```

문제는 **nginx 설정이 반영되기 전에 캐시된 항목**이 남아 있는 것뿐이다.
(활성 심볼릭 링크가 `odostudio.site.conf`를 가리키는데 확장자 없는 이름으로
복사해서, 한동안 헤더 없이 서빙됐다.) 그동안 Cloudflare가 기본값인
`max-age=14400`으로 캐시해 뒀다.

**할 일**: Cloudflare 대시보드 → 도메인 선택 → **Caching** → **Configuration** →
**Purge Cache** → `Custom Purge`에 `https://odostudio.site/sw.js` 입력.
(`Purge Everything`도 되지만 전체를 비울 이유는 없다.)

**안 해도 된다.** 최대 4시간 뒤 그 항목이 만료되면 그 뒤로는 계속 정상이다.
서비스 워커 스크립트는 브라우저도 대체로 강제 재검증하므로 실제 피해도 크지 않다.

**확인**: 쿼리 없이 요청했을 때 `max-age=14400`이 사라지면 된다.

```bash
curl -sI https://odostudio.site/sw.js | grep -i cache-control
```

---

## 8. GitHub Actions — 배포 자동화

`main`에 web-service 변경이 올라가면 자동으로 빌드·테스트·배포한다.
**맥미니(분석 서버)는 포함되지 않는다** — Tailscale 내부망에 있어 GitHub 러너가
닿을 수 없다. 분석 서버는 로컬에서 `./deploy/deploy-ai-server.sh`로 올린다.

### 시크릿 3개 등록

GitHub 저장소 → **Settings** → **Secrets and variables** → **Actions** →
**New repository secret**.

| 이름 | 값을 얻는 법 |
|---|---|
| `DEPLOY_SSH_KEY` | `pbcopy < ~/.ssh/odo-deploy-key` (개인키 전체) |
| `DEPLOY_HOST` | EC2의 탄력적 IP. `13.125.143.96` |
| `DEPLOY_KNOWN_HOSTS` | `ssh-keyscan -t ed25519,rsa 13.125.143.96 \| pbcopy` |

`DEPLOY_SSH_KEY`는 **배포 전용으로 새로 만든 키**다(`~/.ssh/odo-deploy-key`).
평소 접속에 쓰는 `odo-server-key.pem`을 넣지 않는다 — 그 키가 새면 서버 접근
수단 전체가 한 번에 열린다. 전용 키는 문제가 생기면 EC2의
`~/.ssh/authorized_keys`에서 그 한 줄만 지우면 끝난다.

`DEPLOY_HOST`를 시크릿으로 두는 이유: 이 IP가 알려지면 Cloudflare를 건너뛰고
원본 서버에 직접 붙을 수 있다. 도메인은 Cloudflare IP로만 해석되므로 굳이
드러낼 이유가 없다.

### 러너가 EC2에 닿게 하기 — 둘 중 하나

**첫 배포가 `Connection timed out`으로 실패한다면 여기 때문이다.** EC2 보안 그룹이
22번 포트를 특정 IP(인스턴스 만들 때 고른 "내 IP")에만 열어두는데, GitHub 러너는
매번 다른 IP에서 뜬다.

GitHub이 쓰는 IP 대역을 전부 허용하는 방법은 쓸 수 없다 — 4000개가 넘어 보안 그룹
규칙 한도를 한참 넘는다.

#### 방법 A — Tailscale로 붙기 (권장, 22번을 안 열어도 됨)

EC2는 이미 tailnet에 있다(`odo-ec2` / `100.114.82.112`). 러너를 **임시 노드**로
참여시키면 공개 IP에서 SSH를 열 필요가 없다. 작업이 끝나면 노드는 스스로 사라진다.

1. Tailscale 관리 콘솔 → **Access controls**에서 `tag:ci`를 선언한다.
   ACL의 `tagOwners`에 다음을 추가:

   ```json
   "tagOwners": {
     "tag:ci": ["autogroup:admin"]
   }
   ```

   태그를 미리 선언하지 않으면 그 태그로 노드를 붙일 수 없다.

2. **Settings → Trust credentials** → **Credential** 버튼 → **OAuth**
   (`https://login.tailscale.com/admin/settings/trust-credentials`)
   - Scopes: `auth_keys` **write**
   - Tags: `tag:ci` — `auth_keys` 스코프는 태그 지정이 **필수**다
   - **Generate credential**

   예전에는 `Settings → OAuth clients`였는데 옮겨졌다. 사이드바에 그 이름이
   없으면 **Trust credentials**를 보면 된다.

   ⚠️ **secret은 창을 닫으면 다시 볼 수 없다.** 나오자마자 아래 3단계로 등록할 것.

3. 발급된 두 값을 GitHub 시크릿으로 등록한다:

   ```bash
   gh secret set TS_OAUTH_CLIENT_ID --body "발급받은-client-id"
   gh secret set TS_OAUTH_SECRET --body "발급받은-secret"
   ```

4. `DEPLOY_HOST`와 `DEPLOY_KNOWN_HOSTS`를 **Tailscale 주소**로 바꾼다:

   ```bash
   gh secret set DEPLOY_HOST --body "100.114.82.112"
   gh secret set DEPLOY_KNOWN_HOSTS --body "$(ssh-keyscan -t ed25519,rsa 100.114.82.112 2>/dev/null)"
   ```

   (auth key 대신 OAuth를 쓰는 이유: auth key는 최대 90일이라 어느 날 조용히
   만료돼 배포가 깨진다. OAuth 클라이언트는 만료가 없다.)

#### 방법 B — 보안 그룹에서 22번을 전체 공개

AWS 콘솔 → EC2 → 인스턴스 → 보안 → 보안 그룹 → 인바운드 규칙 편집 →
SSH(22) 소스를 `0.0.0.0/0`으로.

1분이면 되고 시크릿도 그대로 쓴다. 다만 **SSH가 인터넷 전체에 열린다.**
비밀번호 인증이 꺼져 있고 키만 받으므로 뚫릴 가능성은 낮지만, 자동화된
접속 시도가 계속 들어와 로그가 지저분해진다.

워크플로는 두 방법 모두에서 동작한다 — Tailscale 시크릿이 없으면 그 단계를
건너뛰고 공개 IP로 직접 붙는다.

### 확인

등록한 뒤 **Actions** 탭 → **배포 (EC2)** → **Run workflow**로 한 번 돌려본다.
시크릿이 빠져 있으면 첫 단계에서 무엇이 없는지 알려주고 멈춘다.

### 배포가 실패하면

워크플로가 **직전 jar로 자동 롤백**한다. 기동을 40회(약 2분) 확인하고,
끝내 응답이 없으면 `app.jar.bak`을 되돌리고 재시작한 뒤 로그를 남긴다.

### DB 스키마

Flyway가 앱 기동 시점에 알아서 적용한다. 사람이 SQL을 미리 돌릴 필요가 없다.
스키마를 바꿀 때는
`web-service/api-server/src/main/resources/db/migration/V2__....sql`을 추가한다.

---

## 값 전달 — 이건 파일에 적지 말 것

아래 값들은 **비밀키**라 git에 올라가면 안 된다.
`DEPLOY-CONSOLE-TASKS.md`(이 파일)나 코드에 직접 적지 말고,
`web-service/api-server/src/main/resources/application-secret.properties`
(gitignore 대상)에 넣거나 환경변수로 전달한다.

| 항목 | 어디서 | 환경변수 이름 |
|---|---|---|
| 도메인 이름 | Cloudflare | `FRONTEND_REDIRECT_URI`, `CORS_ALLOWED_ORIGINS` |
| R2 버킷 이름 | R2 | `R2_BUCKET` |
| R2 Endpoint | R2 API Token 발급 화면 | `R2_ENDPOINT` |
| R2 Access Key ID | 〃 | `R2_ACCESS_KEY` |
| R2 Secret Access Key | 〃 | `R2_SECRET_KEY` |
| 카카오 REST API 키 | 카카오 개발자 | `KAKAO_CLIENT_ID` |
| 카카오 Client Secret | 〃 | `KAKAO_CLIENT_SECRET` |
| 네이버 Client ID | 네이버 개발자 | `NAVER_CLIENT_ID` |
| 네이버 Client Secret | 〃 | `NAVER_CLIENT_SECRET` |
| ~~EC2 퍼블릭 IP~~ | ✅ **13.125.143.96** (Elastic IP) | Cloudflare DNS A 레코드 |
| ~~맥미니 Tailscale IP~~ | ✅ **100.117.201.13** (`coco-mac-mini`) | `AI_SERVER_URL=http://100.117.201.13:8000` |

배포 시 함께 바꿔야 하는 값 (기본값은 개발용이다):

| 환경변수 | 개발 기본값 | 배포에서 |
|---|---|---|
| `STORAGE_TYPE` | `local` | **`r2`** |
| `COOKIE_SECURE` | `false` | **`true`** (HTTPS 필수) |
| `JWT_SECRET` | 개발용 고정 문자열 | **32바이트 이상 무작위 값** |
| `SPRING_PROFILES_ACTIVE` | `dev` | **`prod`** (로컬 로그인·시드 계정 비활성) |

---

## 관련 문서

- `TASKS-SERVICE.md` — 서비스 작업 전체 (Phase S1~S5)
- `README.md` — 프로젝트 개요
- `docs/analysis-engine-report.md` — 분석 엔진 설계 보고서
