/**
 * API Client - 백엔드 통신 유틸리티
 */

const API_BASE_URL = 'http://localhost:8080';

/**
 * 로컬 스토리지에서 현재 사용자 정보 가져오기
 */
export const getCurrentUser = () => {
  const userStr = localStorage.getItem('user');
  if (userStr) {
    return JSON.parse(userStr);
  }
  return null;
};

/**
 * 사용자 정보 저장
 */
export const setCurrentUser = (user) => {
  localStorage.setItem('user', JSON.stringify(user));
};

/**
 * 로그아웃
 */
export const logout = () => {
  localStorage.removeItem('user');
};

/**
 * 기본 fetch 래퍼
 */
const fetchAPI = async (endpoint, options = {}) => {
  const user = getCurrentUser();

  const headers = {
    ...options.headers,
  };

  // JSON 요청인 경우 Content-Type 추가
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  // 로그인된 사용자가 있으면 X-User-Id 헤더 추가
  if (user && user.id) {
    headers['X-User-Id'] = user.id.toString();
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `HTTP ${response.status}`);
  }

  // 응답이 비어있는 경우 처리
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }

  return response.text();
};

// ============ Auth API ============

/**
 * 회원가입
 */
export const signup = async (data) => {
  return fetchAPI('/api/auth/signup', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

/**
 * 로그인
 */
export const login = async (loginId, password) => {
  return fetchAPI('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ loginId, password }),
  });
};

/**
 * 현재 사용자 정보 조회
 */
export const fetchCurrentUser = async () => {
  return fetchAPI('/api/users/me');
};

// ============ Team API ============

/**
 * 팀 목록 조회
 */
export const getTeams = async () => {
  return fetchAPI('/teams');
};

/**
 * 팀 생성
 */
export const createTeam = async (name) => {
  return fetchAPI('/teams', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
};

// ============ Assignment API ============

/**
 * 숙제 목록 조회
 */
export const getAssignments = async () => {
  return fetchAPI('/assignments');
};

/**
 * 숙제 상세 조회
 */
export const getAssignment = async (id) => {
  return fetchAPI(`/assignments/${id}`);
};

/**
 * 숙제 생성
 */
export const createAssignment = async (data) => {
  return fetchAPI('/assignments', {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

/**
 * 숙제 제출 현황 조회 (팀장용)
 */
export const getSubmissions = async (assignmentId) => {
  return fetchAPI(`/assignments/${assignmentId}/submissions`);
};

/**
 * [NEW] 내 제출 이력 조회
 */
export const getMySubmissions = async (assignmentId) => {
  return fetchAPI(`/assignments/${assignmentId}/my-submissions`);
};

// ============ Video API ============

/**
 * 영상 업로드
 */
export const uploadVideo = async (formData) => {
  return fetchAPI('/videos', {
    method: 'POST',
    body: formData, // FormData는 Content-Type 자동 설정
  });
};

/**
 * 영상 URL 가져오기
 * 
 * [MODIFIED] 쿼리 파라미터로 userId를 추가
 * 이유: <video src="URL"> 태그에서는 HTTP 헤더를 설정할 수 없으므로
 *       백엔드에서 쿼리 파라미터로도 인증을 받을 수 있도록 수정됨
 */
export const getVideoUrl = (videoId) => {
  const user = getCurrentUser();
  const userId = user?.id || '';
  return `${API_BASE_URL}/videos/${videoId}?userId=${userId}`;
};

/**
 * 영상 삭제
 */
export const deleteVideo = async (videoId) => {
  return fetchAPI(`/videos/${videoId}`, {
    method: 'DELETE',
  });
};

// ============ Practice Log API ============

/**
 * 연습 기록 목록 조회
 */
export const getPracticeLogs = async (page = 0, size = 10) => {
  return fetchAPI(`/practice-logs?page=${page}&size=${size}`);
};

/**
 * 연습 기록 상세 조회
 */
export const getPracticeLog = async (logId) => {
  return fetchAPI(`/practice-logs/${logId}`);
};

/**
 * 분석 요청
 */
export const analyzeLog = async (logId) => {
  return fetchAPI(`/practice-logs/${logId}/analyze`, {
    method: 'POST',
  });
};
