# Dance-Assessment API 명세서

## 개요

이 문서는 Dance-Assessment 프로젝트의 REST API 명세를 정의합니다.

**기본 URL**: `http://localhost:8080`

**공통 헤더**:
| 헤더 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `X-User-Id` | Long | ✅ | 요청하는 사용자의 ID |

---

## 1. 팀 API (Team)

### 1.1 팀 생성

팀장이 새 팀을 생성합니다.

- **URL**: `/teams`
- **Method**: `POST`
- **설명**: 새로운 팀을 생성하고 요청한 사용자를 팀장으로 설정합니다.

#### 요청 헤더

| 헤더 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `X-User-Id` | Long | ✅ | 팀장이 될 사용자 ID |

#### 요청 본문

```json
{
  "name": "팀 이름"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `name` | String | ✅ | 팀 이름 |

#### 응답

**성공 (200 OK)**:
```json
1
```
> 생성된 팀의 ID를 반환합니다.

---

## 2. 숙제 API (Assignment)

### 2.1 숙제 생성

팀장이 팀원들에게 연습 숙제를 생성합니다.

- **URL**: `/assignments`
- **Method**: `POST`
- **설명**: 기준 영상을 지정하여 새 숙제를 생성합니다.

#### 요청 헤더

| 헤더 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `X-User-Id` | Long | ✅ | 숙제를 생성하는 사용자(팀장) ID |

#### 요청 본문

```json
{
  "targetVideoId": 1,
  "title": "숙제 제목",
  "startDate": "2024-01-01T09:00:00",
  "dueDate": "2024-01-07T23:59:59"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `targetVideoId` | Long | ✅ | 기준 영상 ID (팀장이 올린 영상) |
| `title` | String | ✅ | 숙제 제목 |
| `startDate` | LocalDateTime | ✅ | 숙제 시작일시 (ISO 8601 형식) |
| `dueDate` | LocalDateTime | ✅ | 숙제 마감일시 (ISO 8601 형식) |

#### 응답

**성공 (200 OK)**:
```json
1
```
> 생성된 숙제의 ID를 반환합니다.

---

### 2.2 숙제 목록 조회

사용자가 속한 팀의 전체 숙제 목록을 조회합니다.

- **URL**: `/assignments`
- **Method**: `GET`
- **설명**: 요청한 사용자가 속한 팀의 모든 숙제를 조회합니다.

#### 요청 헤더

| 헤더 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `X-User-Id` | Long | ✅ | 조회하는 사용자 ID |

#### 응답

**성공 (200 OK)**:
```json
[
  {
    "assignmentId": 1,
    "title": "숙제 제목",
    "startDate": "2024-01-01T09:00:00",
    "dueDate": "2024-01-07T23:59:59",
    "writerName": "팀장닉네임",
    "targetVideoId": 1
  }
]
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `assignmentId` | Long | 숙제 ID |
| `title` | String | 숙제 제목 |
| `startDate` | LocalDateTime | 숙제 시작일시 |
| `dueDate` | LocalDateTime | 숙제 마감일시 |
| `writerName` | String | 숙제를 낸 사람(팀장) 닉네임 |
| `targetVideoId` | Long | 기준 영상 ID |

---

## 3. 연습 기록 API (PracticeLog)

### 3.1 연습 기록 목록 조회

사용자의 연습 기록을 페이지네이션으로 조회합니다.

- **URL**: `/practice-logs`
- **Method**: `GET`
- **설명**: 사용자의 연습 영상 제출 기록을 조회합니다. 최신순으로 정렬됩니다.

#### 요청 헤더

| 헤더 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `X-User-Id` | Long | ✅ | 조회하는 사용자 ID |

#### 쿼리 파라미터

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `page` | Integer | ❌ | 0 | 페이지 번호 (0부터 시작) |
| `size` | Integer | ❌ | 10 | 페이지당 항목 수 |
| `sort` | String | ❌ | createdAt,desc | 정렬 기준 |

#### 응답

**성공 (200 OK)**:
```json
{
  "content": [
    {
      "logId": 1,
      "createdDate": "2024-01-05T15:30:00",
      "title": "연습 영상 1",
      "score": 85,
      "status": "COMPLETED"
    }
  ],
  "totalPages": 5,
  "totalElements": 50,
  "number": 0,
  "size": 10
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `logId` | Long | 연습 기록 ID |
| `createdDate` | LocalDateTime | 생성일시 |
| `title` | String | 영상 제목 |
| `score` | Integer | AI 분석 점수 (0~100) |
| `status` | AnalysisStatus | 분석 상태 (`WAITING`, `PROCESSING`, `COMPLETED`, `FAILED`) |

---

### 3.2 연습 기록 분석 요청

연습 기록에 대한 AI 분석을 요청합니다.

- **URL**: `/practice-logs/{logId}/analyze`
- **Method**: `POST`
- **설명**: 특정 연습 기록에 대해 AI 서버에 동작 분석을 요청합니다.

#### 경로 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `logId` | Long | ✅ | 분석할 연습 기록 ID |

#### 요청 헤더

| 헤더 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `X-User-Id` | Long | ✅ | 요청하는 사용자 ID |

#### 응답

**성공 (200 OK)**:
```json
{
  "video_id": 1,
  "score": 85,
  "feedback": "전반적으로 동작이 정확합니다. 팔 동작에서 약간의 개선이 필요합니다.",
  "status": "COMPLETED"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `video_id` | Long | 분석된 영상 ID |
| `score` | Integer | AI 분석 점수 (0~100) |
| `feedback` | String | AI 분석 피드백 내용 |
| `status` | String | 분석 결과 상태 |

---

## 4. 영상 API (Video)

### 4.1 영상 업로드

사용자가 연습 영상을 업로드합니다.

- **URL**: `/videos`
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **설명**: 연습 영상 파일을 서버에 업로드합니다.

#### 요청 헤더

| 헤더 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `X-User-Id` | Long | ✅ | 업로드하는 사용자 ID |

#### 요청 본문 (form-data)

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `title` | String | ✅ | 영상 제목 |
| `type` | VideoType | ✅ | 영상 타입 (`ORIGINAL`, `PRACTICE`) |
| `file` | MultipartFile | ✅ | 업로드할 영상 파일 |
| `assignmentId` | Long | ❌ | 연결할 숙제 ID (연습 영상인 경우) |

#### 응답

**성공 (200 OK)**:
```json
1
```
> 업로드된 영상의 ID를 반환합니다.

**실패 (400 Bad Request)**:
```json
"업로드 실패: 유저를 찾을 수 없습니다."
```

**실패 (500 Internal Server Error)**:
```json
"업로드 실패: 서버 파일 저장 중 오류 (상세 에러 메시지)"
```

---

### 4.2 영상 재생

업로드된 영상을 재생합니다.

- **URL**: `/videos/{videoId}`
- **Method**: `GET`
- **설명**: 영상 파일을 스트리밍으로 반환합니다.

#### 경로 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `videoId` | Long | ✅ | 재생할 영상 ID |

#### 요청 헤더

| 헤더 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `X-User-Id` | Long | ✅ | 시청하는 사용자 ID |

#### 응답

**성공 (200 OK)**:
- **Content-Type**: `video/mp4`
- **Content-Disposition**: `inline; filename="video.mp4"`
- **Body**: 영상 바이너리 데이터

**실패 (403 Forbidden)**:
> 권한이 없는 경우 (같은 팀이 아닌 경우)

**실패 (404 Not Found)**:
> 영상이 존재하지 않거나 파일을 찾을 수 없는 경우

---

### 4.3 영상 삭제

업로드된 영상을 삭제합니다.

- **URL**: `/videos/{videoId}`
- **Method**: `DELETE`
- **설명**: 영상 파일과 데이터베이스 레코드를 삭제합니다.

#### 경로 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `videoId` | Long | ✅ | 삭제할 영상 ID |

#### 요청 헤더

| 헤더 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `X-User-Id` | Long | ✅ | 삭제 요청하는 사용자 ID |

#### 응답

**성공 (200 OK)**:
```json
"영상이 정상적으로 삭제되었습니다."
```

**실패 (403 Forbidden)**:
```json
"삭제 실패: 본인의 영상만 삭제할 수 있습니다."
```

**실패 (404 Not Found)**:
> 영상이 존재하지 않는 경우

---

### 4.4 영상 분석 요청 (테스트용, 미사용)

> ⚠️ **주의**: 이 API는 테스트 목적으로만 존재하며, 실제로는 `/practice-logs/{logId}/analyze` API를 사용합니다.

- **URL**: `/videos/{videoId}/analyze`
- **Method**: `POST`
- **설명**: 영상에 대한 AI 분석을 요청합니다.

#### 경로 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `videoId` | Long | ✅ | 분석할 영상 ID |

#### 응답

**성공 (200 OK)**:
```json
{
  "video_id": 1,
  "score": 85,
  "feedback": "분석 결과 피드백",
  "status": "COMPLETED"
}
```

---

## 에러 코드 정리

| HTTP 상태 코드 | 설명 |
|----------------|------|
| 200 OK | 요청 성공 |
| 400 Bad Request | 잘못된 요청 (파라미터 누락, 유효성 검증 실패 등) |
| 403 Forbidden | 권한 없음 (본인 영상이 아니거나 같은 팀이 아닌 경우) |
| 404 Not Found | 리소스를 찾을 수 없음 |
| 500 Internal Server Error | 서버 내부 오류 |

---

## 데이터 타입 참조

### VideoType (영상 타입)

| 값 | 설명 |
|-----|------|
| `ORIGINAL` | 기준 영상 (팀장이 업로드하는 원본 안무 영상) |
| `PRACTICE` | 연습 영상 (팀원이 숙제로 제출하는 영상) |

### AnalysisStatus (분석 상태)

| 값 | 설명 |
|-----|------|
| `WAITING` | 분석 대기 중 |
| `PROCESSING` | 분석 진행 중 |
| `COMPLETED` | 분석 완료 |
| `FAILED` | 분석 실패 |

---

## API 사용 예시

### cURL 예시

#### 팀 생성
```bash
curl -X POST http://localhost:8080/teams \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"name": "댄스팀A"}'
```

#### 영상 업로드
```bash
curl -X POST http://localhost:8080/videos \
  -H "X-User-Id: 1" \
  -F "title=연습영상1" \
  -F "type=PRACTICE" \
  -F "file=@/path/to/video.mp4" \
  -F "assignmentId=1"
```

#### 숙제 목록 조회
```bash
curl -X GET http://localhost:8080/assignments \
  -H "X-User-Id: 1"
```

#### 연습 기록 분석 요청
```bash
curl -X POST http://localhost:8080/practice-logs/1/analyze \
  -H "X-User-Id: 1"
```
