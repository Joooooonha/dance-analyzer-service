import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Crown, Sparkles, Users } from 'lucide-react';
import { signup, setCurrentUser, getTeams } from '../api/client';
import './Auth.css';

export default function Signup() {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        loginId: '',
        password: '',
        passwordConfirm: '',
        nickname: ''
    });
    const [teamMode, setTeamMode] = useState('none'); // 'none', 'join', 'create'
    const [selectedTeamId, setSelectedTeamId] = useState(null);
    const [newTeamName, setNewTeamName] = useState('');
    const [teams, setTeams] = useState([]);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        // 팀 목록 불러오기
        const loadTeams = async () => {
            try {
                const data = await getTeams();
                setTeams(data);
            } catch (err) {
                console.error('팀 목록 로드 실패:', err);
            }
        };
        loadTeams();
    }, []);

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        // 비밀번호 확인
        if (formData.password !== formData.passwordConfirm) {
            setError('비밀번호가 일치하지 않습니다.');
            return;
        }

        setLoading(true);

        try {
            const requestData = {
                loginId: formData.loginId,
                password: formData.password,
                nickname: formData.nickname,
                teamId: teamMode === 'join' ? selectedTeamId : null,
                createTeamName: teamMode === 'create' ? newTeamName : null
            };

            const user = await signup(requestData);
            setCurrentUser(user);
            navigate('/');
        } catch (err) {
            setError(err.message || '회원가입에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-container">
                <div className="auth-header">
                    <span className="auth-icon"><Sparkles size={40} /></span>
                    <h1>회원가입</h1>
                    <p>ODO에 가입하고 춤 연습을 시작하세요</p>
                </div>

                <form className="auth-form" onSubmit={handleSubmit}>
                    {error && <div className="auth-error">{error}</div>}

                    <div className="form-group">
                        <label className="form-label">아이디</label>
                        <input
                            type="text"
                            name="loginId"
                            className="form-input"
                            placeholder="아이디를 입력하세요"
                            value={formData.loginId}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">닉네임</label>
                        <input
                            type="text"
                            name="nickname"
                            className="form-input"
                            placeholder="닉네임을 입력하세요"
                            value={formData.nickname}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">비밀번호</label>
                        <input
                            type="password"
                            name="password"
                            className="form-input"
                            placeholder="비밀번호를 입력하세요"
                            value={formData.password}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">비밀번호 확인</label>
                        <input
                            type="password"
                            name="passwordConfirm"
                            className="form-input"
                            placeholder="비밀번호를 다시 입력하세요"
                            value={formData.passwordConfirm}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label className="form-label">팀 설정</label>
                        <div className="team-options">
                            <div
                                className={`team-option ${teamMode === 'none' ? 'active' : ''}`}
                                onClick={() => setTeamMode('none')}
                            >
                                <span className="team-option-label">무소속</span>
                                <span className="team-option-desc">개인 연습</span>
                            </div>
                            <div
                                className={`team-option ${teamMode === 'join' ? 'active' : ''}`}
                                onClick={() => setTeamMode('join')}
                            >
                                <span className="team-option-label">팀 가입</span>
                                <span className="team-option-desc">기존 팀</span>
                            </div>
                            <div
                                className={`team-option ${teamMode === 'create' ? 'active' : ''}`}
                                onClick={() => setTeamMode('create')}
                            >
                                <span className="team-option-label">팀 생성</span>
                                <span className="team-option-desc">팀장 되기</span>
                            </div>
                        </div>

                        {teamMode === 'join' && (
                            <div className="team-list">
                                {teams.length > 0 ? (
                                    teams.map(team => (
                                        <div
                                            key={team.id}
                                            className={`team-item ${selectedTeamId === team.id ? 'selected' : ''}`}
                                            onClick={() => setSelectedTeamId(team.id)}
                                        >
                                            <span className="team-item-name">{team.name}</span>
                                            <span className="team-item-info">
                                                <span className="icon-inline"><Crown size={13} /> {team.leaderName || '팀장'}</span>
                                                {' · '}
                                                <span className="icon-inline"><Users size={13} /> {team.memberCount}명</span>
                                            </span>
                                        </div>
                                    ))
                                ) : (
                                    <p className="text-center" style={{ color: 'var(--text-muted)' }}>
                                        아직 생성된 팀이 없습니다
                                    </p>
                                )}
                            </div>
                        )}

                        {teamMode === 'create' && (
                            <input
                                type="text"
                                className="form-input mt-2"
                                placeholder="새 팀 이름을 입력하세요"
                                value={newTeamName}
                                onChange={(e) => setNewTeamName(e.target.value)}
                            />
                        )}
                    </div>

                    <button
                        type="submit"
                        className="btn btn-primary btn-lg auth-submit"
                        disabled={loading}
                    >
                        {loading ? '가입 중...' : '가입하기'}
                    </button>
                </form>

                <div className="auth-footer">
                    <p>
                        이미 계정이 있으신가요?{' '}
                        <Link to="/login">로그인</Link>
                    </p>
                </div>
            </div>
        </div>
    );
}
