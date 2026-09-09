import { createContext } from 'react';

/**
 * 인증 상태 컨텍스트.
 *
 * 컴포넌트가 아닌 값은 별도 파일에 둔다 — 컴포넌트 파일이 컴포넌트 외의 것을
 * export하면 Vite의 Fast Refresh가 동작하지 않는다.
 */
export const AuthContext = createContext(null);
