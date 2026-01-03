import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getAssignment, uploadVideo, getCurrentUser, getSubmissions, getMySubmissions } from '../api/client';
import VideoUploader from '../components/VideoUploader';
import './AssignmentDetail.css';

export default function AssignmentDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const user = getCurrentUser();

    const [assignment, setAssignment] = useState(null);
    const [submissions, setSubmissions] = useState([]);
    const [mySubmissions, setMySubmissions] = useState([]); // [NEW] 내 제출 이력
    const [loading, setLoading] = useState(true);
    const [practiceFile, setPracticeFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        const loadData = async () => {
            try {
                const assignmentData = await getAssignment(id);
                setAssignment(assignmentData);

                // 팀장이면 제출 현황도 불러오기
                if (user?.isLeader) {
                    try {
                        const submissionsData = await getSubmissions(id);
                        setSubmissions(submissionsData);
                    } catch (e) {
                        // 팀장이 아니거나 권한이 없으면 무시
                    }
                }

                // [NEW] 내 제출 이력 불러오기 (팀원의 경우)
                if (!user?.isLeader) {
                    try {
                        const myData = await getMySubmissions(id);
                        setMySubmissions(myData);
                    } catch (e) {
                        // 제출 이력이 없으면 무시
                    }
                }
            } catch (err) {
                setError(err.message || '숙제를 불러오지 못했습니다.');
            } finally {
                setLoading(false);
            }
        };
        loadData();
    }, [id, user?.isLeader]);

    const handleSubmit = async () => {
        if (!practiceFile) {
            setError('연습 영상을 선택해주세요.');
            return;
        }

        setUploading(true);
        setError('');

        try {
            const formData = new FormData();
            formData.append('title', `숙제 ${id} 제출`);
            formData.append('type', 'PRACTICE');
            formData.append('file', practiceFile);
            formData.append('assignmentId', id);

            await uploadVideo(formData);
            alert('제출이 완료되었습니다!');
            navigate('/logs');
        } catch (err) {
            setError(err.message || '제출에 실패했습니다.');
        } finally {
            setUploading(false);
        }
    };

    const formatDate = (dateString) => {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('ko-KR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    if (loading) {
        return (
            <div className="page">
                <div className="loading">
                    <div className="spinner"></div>
                </div>
            </div>
        );
    }

    if (error && !assignment) {
        return (
            <div className="page">
                <div className="container">
                    <div className="auth-error">{error}</div>
                    <Link to="/assignments" className="btn btn-secondary mt-3">
                        ← 목록으로
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="assignment-detail-page page">
            <div className="container">
                <Link to="/assignments" className="back-link">← 숙제 목록</Link>

                <div className="assignment-info card">
                    <h1>{assignment?.title}</h1>
                    <div className="assignment-meta-detail">
                        <div className="meta-item">
                            <span className="meta-label">출제자</span>
                            <span className="meta-value">👑 {assignment?.writerName}</span>
                        </div>
                        <div className="meta-item">
                            <span className="meta-label">시작일</span>
                            <span className="meta-value">{formatDate(assignment?.startDate)}</span>
                        </div>
                        <div className="meta-item">
                            <span className="meta-label">마감일</span>
                            <span className="meta-value">{formatDate(assignment?.dueDate)}</span>
                        </div>
                    </div>
                </div>

                <div className="detail-grid">
                    {/* [MODIFIED] placeholder를 실제 video 태그로 교체 */}
                    <section className="reference-section card">
                        <h2>📹 기준 영상</h2>
                        <p className="hint-text">이 영상을 보고 따라 연습하세요</p>
                        {assignment?.targetVideoId ? (
                            <video
                                controls
                                className="video-player"
                                src={`http://localhost:8080/videos/${assignment.targetVideoId}?userId=${user?.id || ''}`}
                            >
                                브라우저가 비디오 태그를 지원하지 않습니다.
                            </video>
                        ) : (
                            <p className="no-video">기준 영상 정보 없음</p>
                        )}
                    </section>

                    {!user?.isLeader ? (
                        <section className="submit-section card">
                            <h2>🎯 숙제 제출</h2>
                            <p className="hint-text">기준 영상을 보고 연습한 영상을 제출하세요</p>

                            {error && <div className="auth-error mb-2">{error}</div>}

                            <VideoUploader
                                label="연습 영상 선택"
                                selectedFile={practiceFile}
                                onSelect={setPracticeFile}
                            />

                            <button
                                className="btn btn-primary btn-lg mt-3"
                                onClick={handleSubmit}
                                disabled={!practiceFile || uploading}
                                style={{ width: '100%' }}
                            >
                                {uploading ? '제출 중...' : '제출하기'}
                            </button>

                            {/* [NEW] 내 제출 이력 */}
                            {mySubmissions.length > 0 && (
                                <div className="my-submissions mt-4">
                                    <h3>📝 내 제출 이력</h3>
                                    <div className="submission-list">
                                        {mySubmissions.map(sub => (
                                            <Link
                                                key={sub.logId}
                                                to={`/logs/${sub.logId}`}
                                                className="submission-item"
                                            >
                                                <div className="submission-info">
                                                    <span className="submission-date">
                                                        {formatDate(sub.createdAt)}
                                                    </span>
                                                </div>
                                                <span className={`badge badge-${sub.status === 'COMPLETED' ? 'success' :
                                                    sub.status === 'PROCESSING' ? 'warning' : 'info'
                                                    }`}>
                                                    {sub.status === 'COMPLETED' ? `${sub.totalScore}점` : sub.status}
                                                </span>
                                            </Link>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </section>
                    ) : (
                        <section className="submissions-section card">
                            <h2>👥 제출 현황</h2>
                            <p className="hint-text">팀원들의 제출 상태를 확인하세요</p>

                            {submissions.length === 0 ? (
                                <div className="empty-state">
                                    <span className="empty-state-icon">📭</span>
                                    <p className="empty-state-text">아직 제출한 팀원이 없습니다</p>
                                </div>
                            ) : (
                                <div className="submission-list">
                                    {submissions.map(sub => (
                                        <div key={sub.logId} className="submission-item">
                                            <div className="submission-info">
                                                <span className="submission-name">{sub.NickName}</span>
                                                <span className="submission-date">
                                                    {formatDate(sub.submittedAt)}
                                                </span>
                                            </div>
                                            <span className={`badge badge-${sub.videoStatus === 'COMPLETED' ? 'success' :
                                                sub.videoStatus === 'PROCESSING' ? 'warning' : 'info'
                                                }`}>
                                                {sub.videoStatus}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </section>
                    )}
                </div>
            </div>
        </div>
    );
}
