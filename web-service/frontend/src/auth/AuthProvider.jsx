import { useEffect, useState, useCallback } from 'react';
import { AuthContext } from './authContext';
import { fetchCurrentUser, setCurrentUser, logout as apiLogout } from '../api/client';

/**
 * 로그인 상태를 **서버에 물어봐서** 판단한다.
 *
 * **왜 localStorage만 보면 안 되는가.** 인증 토큰은 httpOnly 쿠키에 있어서
 * 자바스크립트가 읽을 수 없다(그게 이 방식의 요점이다 — XSS로 탈취되지 않는다).
 * 그래서 "로그인했는지"를 프론트가 스스로 알 방법이 없다.
 *
 * 소셜 로그인이 이 문제를 그대로 드러냈다. 카카오/네이버 인증이 끝나면 서버가
 * 쿠키를 굽고 프론트로 리다이렉트하는데, **localStorage에는 아무것도 안 남는다.**
 * 화면은 여전히 로그아웃 상태로 보이고, 로그인 버튼을 다시 눌러도 이미 인증된
 * 상태라 즉시 되돌아와 아무 일도 일어나지 않는 것처럼 보였다.
 * (서버 로그에는 "로그인 성공"이 여러 번 찍혔다.)
 *
 * → 앱이 뜰 때 `/api/users/me`를 한 번 호출해 확인한다. 쿠키가 유효하면 사용자
 *   정보가 오고, 없으면 401이 온다. 이것이 유일하게 신뢰할 수 있는 판단이다.
 */
export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    // 확인이 끝나기 전에는 로그인 여부를 알 수 없다. 이 상태를 구분하지 않으면
    // 확인 중에 로그인한 사용자가 로그인 화면으로 튕겨나갔다 돌아온다.
    const [checking, setChecking] = useState(true);

    const refresh = useCallback(async () => {
        try {
            const me = await fetchCurrentUser();
            setUser(me);
            setCurrentUser(me);          // 화면 표시용 캐시 (권한 판단에는 쓰지 않는다)
            return me;
        } catch {
            setUser(null);
            localStorage.removeItem('user');
            return null;
        } finally {
            setChecking(false);
        }
    }, []);

    useEffect(() => { refresh(); }, [refresh]);

    const logout = useCallback(async () => {
        await apiLogout();
        setUser(null);
    }, []);

    return (
        <AuthContext.Provider value={{ user, checking, refresh, logout }}>
            {children}
        </AuthContext.Provider>
    );
}
