import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/useAuth';
import './Header.css';

export default function Header() {
    const navigate = useNavigate();
    const { user, logout } = useAuth();

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    return (
        <header className="header">
            <div className="header-container">
                <Link to="/" className="logo">
                    <span className="logo-icon">💃</span>
                    <span className="logo-text">DanceFlow</span>
                </Link>

                <nav className="nav">
                    {user ? (
                        <>
                            <Link to="/" className="nav-link">대시보드</Link>
                            <Link to="/practice" className="nav-link">자유 연습</Link>
                            <Link to="/assignments" className="nav-link">숙제</Link>
                            <Link to="/logs" className="nav-link">내 기록</Link>
                        </>
                    ) : null}
                </nav>

                <div className="header-actions">
                    {user ? (
                        <div className="user-menu">
                            <span className="user-info">
                                <span className="user-name">{user.nickname}</span>
                                {user.teamName && (
                                    <span className="user-team">
                                        {user.isLeader ? '👑' : '👤'} {user.teamName}
                                    </span>
                                )}
                            </span>
                            <button onClick={handleLogout} className="btn btn-outline btn-sm">
                                로그아웃
                            </button>
                        </div>
                    ) : (
                        <div className="auth-buttons">
                            <Link to="/login" className="btn btn-secondary btn-sm">로그인</Link>
                            <Link to="/signup" className="btn btn-primary btn-sm">회원가입</Link>
                        </div>
                    )}
                </div>
            </div>
        </header>
    );
}
