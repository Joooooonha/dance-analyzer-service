import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AlertTriangle, Clock, FileX, History } from 'lucide-react';
import { getPracticeLogs } from '../api/client';
import { getStatusLabel } from '../utils/logStatus';
import './Logs.css';

export default function Logs() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [page, setPage] = useState(0);
    const [totalPages, setTotalPages] = useState(0);

    // AssignmentDetail.jsx의 제출 완료 안내 — alert() 대신 이동해온 화면에
    // 배너로 띄운다. history state에 남기면 새로고침해도 계속 뜨므로,
    // 뜨자마자(또는 닫으면) replace로 지운다.
    const location = useLocation();
    const navigate = useNavigate();
    const [toast, setToast] = useState(location.state?.toast ?? null);
    useEffect(() => {
        if (location.state?.toast) {
            navigate(location.pathname, { replace: true, state: {} });
        }
    }, [location.state, location.pathname, navigate]);

    useEffect(() => {
        const loadLogs = async () => {
            try {
                const data = await getPracticeLogs(page);
                setLogs(data.content || []);
                setTotalPages(data.totalPages || 0);
            } catch (err) {
                setError(err.message || '기록을 불러오지 못했습니다.');
            } finally {
                setLoading(false);
            }
        };
        loadLogs();
    }, [page]);

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('ko-KR', {
            month: 'short',
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

    return (
        <div className="logs-page page">
            <div className="container">
                <div className="page-header">
                    <h1 className="heading-icon"><History size={26} /> 내 연습 기록</h1>
                    <p>지금까지의 연습 기록과 분석 결과입니다</p>
                </div>

                {toast && (
                    <div className="page-toast">
                        <span>{toast}</span>
                        <button type="button" onClick={() => setToast(null)} aria-label="닫기">×</button>
                    </div>
                )}

                {error && <div className="auth-error">{error}</div>}

                {logs.length === 0 ? (
                    <div className="empty-state">
                        <span className="empty-state-icon"><FileX size={48} /></span>
                        <h3 className="empty-state-title">아직 연습 기록이 없습니다</h3>
                        <p className="empty-state-text">
                            자유 연습이나 숙제 제출을 통해 첫 기록을 남겨보세요
                        </p>
                        <Link to="/practice" className="btn btn-primary mt-3">
                            연습 시작하기
                        </Link>
                    </div>
                ) : (
                    <>
                        <div className="logs-list">
                            {logs.map(log => (
                                <Link
                                    key={log.logId}
                                    to={`/logs/${log.logId}`}
                                    className="log-card"
                                >
                                    <div className="log-score">
                                        {log.status === 'COMPLETED' && log.issueCount !== null ? (
                                            <div className="issue-badge">
                                                <span className="issue-badge-value">{log.issueCount}</span>
                                                <span className="issue-badge-label">구간</span>
                                            </div>
                                        ) : log.status === 'FAILED' ? (
                                            /* PROCESSING/WAITING과 같은 시계 아이콘을 쓰면 실패한 세션이
                                               열어보기 전엔 "아직 처리 중"과 구분이 안 됐다(critique P3). */
                                            <div className="issue-badge failed">
                                                <span className="score-icon"><AlertTriangle size={22} /></span>
                                            </div>
                                        ) : (
                                            <div className="issue-badge pending">
                                                <span className="score-icon"><Clock size={22} /></span>
                                            </div>
                                        )}
                                    </div>
                                    <div className="log-info">
                                        <h3 className="log-title">{log.title}</h3>
                                        <div className="log-meta">
                                            <span>{formatDate(log.createdDate)}</span>
                                            <span className={`badge badge-${log.status === 'COMPLETED' ? 'success' :
                                                    log.status === 'PROCESSING' ? 'warning' :
                                                        log.status === 'FAILED' ? 'error' : 'info'
                                                }`}>
                                                {getStatusLabel(log.status)}
                                            </span>
                                        </div>
                                    </div>
                                    <span className="log-arrow">→</span>
                                </Link>
                            ))}
                        </div>

                        {totalPages > 1 && (
                            <div className="pagination">
                                <button
                                    className="btn btn-secondary btn-sm"
                                    disabled={page === 0}
                                    onClick={() => setPage(p => p - 1)}
                                >
                                    이전
                                </button>
                                <span className="page-info">
                                    {page + 1} / {totalPages}
                                </span>
                                <button
                                    className="btn btn-secondary btn-sm"
                                    disabled={page >= totalPages - 1}
                                    onClick={() => setPage(p => p + 1)}
                                >
                                    다음
                                </button>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
