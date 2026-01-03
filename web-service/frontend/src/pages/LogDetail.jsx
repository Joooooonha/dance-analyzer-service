import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getPracticeLog, analyzeLog } from '../api/client';
import './LogDetail.css';

export default function LogDetail() {
    const { id } = useParams();
    const [log, setLog] = useState(null);
    const [loading, setLoading] = useState(true);
    const [analyzing, setAnalyzing] = useState(false);
    const [error, setError] = useState('');

    const loadLog = async () => {
        try {
            const data = await getPracticeLog(id);
            setLog(data);
        } catch (err) {
            setError(err.message || '기록을 불러오지 못했습니다.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadLog();
    }, [id]);

    const handleAnalyze = async () => {
        setAnalyzing(true);
        try {
            await analyzeLog(id);
            await loadLog(); // 분석 후 다시 불러오기
        } catch (err) {
            setError(err.message || '분석에 실패했습니다.');
        } finally {
            setAnalyzing(false);
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

    const getScoreClass = (score) => {
        if (!score && score !== 0) return '';
        if (score >= 90) return 'excellent';
        if (score >= 70) return 'good';
        if (score >= 50) return 'average';
        return 'poor';
    };

    const getScoreMessage = (score) => {
        if (!score && score !== 0) return '';
        if (score >= 90) return '완벽해요! 🎉';
        if (score >= 70) return '잘했어요! 👍';
        if (score >= 50) return '조금만 더! 💪';
        return '열심히 연습해봐요! 🔥';
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

    if (error && !log) {
        return (
            <div className="page">
                <div className="container">
                    <div className="auth-error">{error}</div>
                    <Link to="/logs" className="btn btn-secondary mt-3">
                        ← 목록으로
                    </Link>
                </div>
            </div>
        );
    }

    return (
        <div className="log-detail-page page">
            <div className="container">
                <Link to="/logs" className="back-link">← 연습 기록</Link>

                {log?.status === 'COMPLETED' && log?.totalScore !== null ? (
                    <div className="result-section">
                        <div className={`score-display-large ${getScoreClass(log.totalScore)}`}>
                            <span className="score-number">{log.totalScore}</span>
                            <span className="score-max">/ 100</span>
                        </div>
                        <h2 className="score-message">{getScoreMessage(log.totalScore)}</h2>
                        <p className="analyzed-at">
                            분석 완료: {formatDate(log.analyzedAt)}
                        </p>
                    </div>
                ) : (
                    <div className="pending-section card">
                        <span className="pending-icon">⏳</span>
                        <h2>분석 {log?.status === 'PROCESSING' ? '진행 중' : '대기 중'}</h2>
                        {log?.status === 'WAITING' && (
                            <button
                                className="btn btn-primary mt-3"
                                onClick={handleAnalyze}
                                disabled={analyzing}
                            >
                                {analyzing ? '분석 중...' : '분석 시작하기'}
                            </button>
                        )}
                        {log?.status === 'PROCESSING' && (
                            <p className="pending-text">AI가 동작을 분석하고 있습니다...</p>
                        )}
                    </div>
                )}

                {log?.feedback && (
                    <div className="feedback-section card">
                        <h3>💬 AI 피드백</h3>
                        <p className="feedback-content">{log.feedback}</p>
                    </div>
                )}

                {/* [NEW] 비교 영상 */}
                {log?.comparisonVideoUrl && (
                    <div className="comparison-video-section card">
                        <h3>🎬 비교 영상</h3>
                        <p className="hint-text">기준 영상과 연습 영상을 나란히 비교한 영상입니다</p>
                        <video
                            controls
                            className="video-player"
                            src={log.comparisonVideoUrl}
                        >
                            브라우저가 비디오 태그를 지원하지 않습니다.
                        </video>
                    </div>
                )}

                {/* [NEW] 오류 관절 정보 */}
                {log?.topErrorJointsJson && (
                    <div className="error-joints-section card">
                        <h3>🦴 주의가 필요한 관절</h3>
                        <p className="hint-text">정확도가 낮았던 관절 부위입니다</p>
                        <div className="error-list">
                            {JSON.parse(log.topErrorJointsJson).map((joint, idx) => (
                                <div key={idx} className={`error-item severity-${joint.severity?.toLowerCase()}`}>
                                    <span className="error-name">{joint.joint_name}</span>
                                    <span className="error-score">{Math.round(joint.average_similarity * 100)}%</span>
                                    <span className={`badge badge-${joint.severity === 'HIGH' ? 'error' : joint.severity === 'MEDIUM' ? 'warning' : 'info'}`}>
                                        {joint.severity}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* [NEW] 오류 프레임 정보 */}
                {log?.topErrorFramesJson && (
                    <div className="error-frames-section card">
                        <h3>📸 문제가 있는 구간</h3>
                        <p className="hint-text">동작이 일치하지 않았던 구간입니다</p>
                        <div className="frame-grid">
                            {JSON.parse(log.topErrorFramesJson).slice(0, 6).map((frame, idx) => (
                                <div key={idx} className="frame-item">
                                    <img
                                        src={frame.comparison_image_url}
                                        alt={`프레임 ${frame.frame_number}`}
                                        className="frame-image"
                                    />
                                    <div className="frame-info">
                                        <span className="frame-time">{frame.timestamp_sec?.toFixed(1)}초</span>
                                        <span className="frame-score">{Math.round(frame.average_similarity * 100)}%</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* [MODIFIED] placeholder를 실제 video 태그로 교체 */}
                <div className="videos-section">
                    <div className="video-card card">
                        <h3>📹 기준 영상</h3>
                        {log?.referenceVideoId ? (
                            <video
                                controls
                                className="video-player"
                                src={`http://localhost:8080/videos/${log.referenceVideoId}?userId=${log.userId || ''}`}
                            >
                                브라우저가 비디오 태그를 지원하지 않습니다.
                            </video>
                        ) : (
                            <p className="no-video">기준 영상 정보 없음</p>
                        )}
                    </div>
                    <div className="video-card card">
                        <h3>🎬 연습 영상</h3>
                        {log?.practiceVideoId ? (
                            <video
                                controls
                                className="video-player"
                                src={`http://localhost:8080/videos/${log.practiceVideoId}?userId=${log.userId || ''}`}
                            >
                                브라우저가 비디오 태그를 지원하지 않습니다.
                            </video>
                        ) : (
                            <p className="no-video">연습 영상 정보 없음</p>
                        )}
                    </div>
                </div>

                <div className="detail-info card">
                    <h3>📋 상세 정보</h3>
                    <div className="info-grid">
                        <div className="info-item">
                            <span className="info-label">기록 ID</span>
                            <span className="info-value">{log?.logId}</span>
                        </div>
                        <div className="info-item">
                            <span className="info-label">제출 시간</span>
                            <span className="info-value">{formatDate(log?.createdAt)}</span>
                        </div>
                        <div className="info-item">
                            <span className="info-label">분석 상태</span>
                            <span className="info-value">{log?.status}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
