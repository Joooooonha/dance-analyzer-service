import { useContext } from 'react';
import { AuthContext } from './authContext';

/** 현재 로그인 상태를 읽는다. `AuthProvider` 안에서만 쓸 수 있다. */
export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth는 AuthProvider 안에서만 쓸 수 있습니다.');
    return ctx;
}
