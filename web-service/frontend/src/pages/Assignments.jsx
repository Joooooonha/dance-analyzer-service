import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Calendar, ClipboardList, Crown, Inbox, Plus, Users } from 'lucide-react';
import { getAssignments, getCurrentUser } from '../api/client';
import './Assignments.css';

export default function Assignments() {
    const [assignments, setAssignments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const user = getCurrentUser();

    useEffect(() => {
        const loadAssignments = async () => {
            try {
                const data = await getAssignments();
                setAssignments(data);
            } catch (err) {
                setError(err.message || '숙제 목록을 불러오지 못했습니다.');
            } finally {
                setLoading(false);
            }
        };
        loadAssignments();
    }, []);

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('ko-KR', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const getStatus = (startDate, dueDate) => {
        const now = new Date();
        const start = new Date(startDate);
        const due = new Date(dueDate);

        if (now < start) return { label: '예정', color: 'info' };
        if (now > due) return { label: '마감', color: 'error' };
        return { label: '진행 중', color: 'success' };
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
        <div className="assignments-page page">
            <div className="container">
                <div className="page-header flex-between">
                    <div>
                        <h1 className="heading-icon"><ClipboardList size={26} /> 숙제</h1>
                        <p>팀에서 부여한 연습 숙제 목록입니다</p>
                    </div>
                    {user?.isLeader && (
                        <Link to="/assignments/new" className="btn btn-primary">
                            <Plus size={16} /> 숙제 생성
                        </Link>
                    )}
                </div>

                {error && <div className="auth-error">{error}</div>}

                {!user?.teamName ? (
                    <div className="empty-state">
                        <span className="empty-state-icon"><Users size={48} /></span>
                        <h3 className="empty-state-title">팀에 소속되어 있지 않습니다</h3>
                        <p className="empty-state-text">
                            팀에 가입하면 팀 숙제를 확인할 수 있습니다
                        </p>
                    </div>
                ) : assignments.length === 0 ? (
                    <div className="empty-state">
                        <span className="empty-state-icon"><Inbox size={48} /></span>
                        <h3 className="empty-state-title">아직 숙제가 없습니다</h3>
                        <p className="empty-state-text">
                            {user?.isLeader
                                ? '팀원들에게 새로운 숙제를 생성해보세요'
                                : '팀장이 숙제를 생성하면 여기에 표시됩니다'}
                        </p>
                    </div>
                ) : (
                    <div className="assignment-list">
                        {assignments.map(assignment => {
                            const status = getStatus(assignment.startDate, assignment.dueDate);
                            return (
                                <Link
                                    key={assignment.assignmentId}
                                    to={`/assignments/${assignment.assignmentId}`}
                                    className="assignment-card"
                                >
                                    <div className="assignment-card-header">
                                        <h3 className="assignment-title">{assignment.title}</h3>
                                        <span className={`badge badge-${status.color}`}>
                                            {status.label}
                                        </span>
                                    </div>
                                    <div className="assignment-meta">
                                        <span className="icon-inline"><Crown size={14} /> {assignment.writerName}</span>
                                        <span className="icon-inline"><Calendar size={14} /> {formatDate(assignment.dueDate)} 마감</span>
                                    </div>
                                    <div className="assignment-arrow">→</div>
                                </Link>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
