import { Link } from 'react-router-dom';
import { ClipboardList, History, Plus, Target } from 'lucide-react';
import { getCurrentUser } from '../api/client';
import './Dashboard.css';

export default function Dashboard() {
    const user = getCurrentUser();

    const features = [
        {
            icon: Target,
            title: '자유 연습',
            description: '기준 영상과 연습 영상을 업로드하여 AI 분석을 받아보세요',
            link: '/practice',
            color: 'pink'
        },
        {
            icon: ClipboardList,
            title: '숙제',
            description: user?.teamName
                ? '팀에서 부여한 숙제를 확인하고 제출하세요'
                : '팀에 가입하여 팀 숙제에 참여하세요',
            link: '/assignments',
            color: 'cyan'
        },
        {
            icon: History,
            title: '내 기록',
            description: '지금까지의 연습 기록과 분석 결과를 확인하세요',
            link: '/logs',
            color: 'purple'
        }
    ];

    const leaderFeatures = [
        {
            icon: Plus,
            title: '숙제 생성',
            description: '팀원들에게 새로운 연습 숙제를 부여하세요',
            link: '/assignments/new',
            color: 'pink'
        }
    ];

    return (
        <div className="dashboard page">
            <div className="container">
                <div className="dashboard-welcome">
                    <h1>안녕하세요, {user?.nickname || '댄서'}님!</h1>
                    <p>오늘도 열심히 춤 연습해볼까요?</p>
                </div>

                <section className="dashboard-section">
                    <h2>주요 기능</h2>
                    <div className="feature-grid">
                        {features.map((feature, index) => (
                            <Link
                                key={index}
                                to={feature.link}
                                className={`feature-card feature-${feature.color}`}
                            >
                                <span className="feature-icon"><feature.icon size={32} /></span>
                                <h3 className="feature-title">{feature.title}</h3>
                                <p className="feature-desc">{feature.description}</p>
                                <span className="feature-arrow">→</span>
                            </Link>
                        ))}
                    </div>
                </section>

                {user?.isLeader && (
                    <section className="dashboard-section">
                        <h2>팀장 메뉴</h2>
                        <div className="feature-grid">
                            {leaderFeatures.map((feature, index) => (
                                <Link
                                    key={index}
                                    to={feature.link}
                                    className={`feature-card feature-${feature.color}`}
                                >
                                    <span className="feature-icon"><feature.icon size={32} /></span>
                                    <h3 className="feature-title">{feature.title}</h3>
                                    <p className="feature-desc">{feature.description}</p>
                                    <span className="feature-arrow">→</span>
                                </Link>
                            ))}
                        </div>
                    </section>
                )}

                <section className="dashboard-section">
                    <h2>시작하기</h2>
                    <div className="quick-start">
                        <div className="quick-start-step">
                            <span className="step-number">1</span>
                            <div className="step-content">
                                <h4>기준 영상 준비</h4>
                                <p>따라 할 춤 영상을 준비하세요</p>
                            </div>
                        </div>
                        <div className="quick-start-step">
                            <span className="step-number">2</span>
                            <div className="step-content">
                                <h4>연습 영상 촬영</h4>
                                <p>기준 영상을 보고 따라 춤을 춰보세요</p>
                            </div>
                        </div>
                        <div className="quick-start-step">
                            <span className="step-number">3</span>
                            <div className="step-content">
                                <h4>AI 분석 받기</h4>
                                <p>두 영상을 업로드하면 점수와 피드백을 받을 수 있어요</p>
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
}
