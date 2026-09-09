import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getCurrentUser, getPracticeLogs } from '../api/client';
import './Dashboard.css';

// 안무 카운트보드 세계관 (surface brief: web-service-frontend-src-pages-dashboard-jsx).
// 아이콘+제목+설명 카드 그리드 대신, 댄서가 이미 손으로 쓰는 카운트 표기를
// 그대로 인터페이스로 옮긴다. 상단 스트립은 "최근 분석" 실데이터로 채운다 —
// critique에서 지적된 "진입 화면에 증거 신호가 없다"는 문제를 여기서 없앤다.
export default function Dashboard() {
    const user = getCurrentUser();
    const [recentLog, setRecentLog] = useState(null);
    const [logsLoaded, setLogsLoaded] = useState(false);
    const [hasAnyLog, setHasAnyLog] = useState(true); // 로딩 중엔 첫 사용자 안내가 깜빡이지 않도록 낙관적 기본값

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const data = await getPracticeLogs(0, 1);
                if (cancelled) return;
                const content = data?.content ?? [];
                setRecentLog(content[0] ?? null);
                setHasAnyLog(content.length > 0);
            } catch {
                // 요약 스트립은 없어도 화면이 정상 동작해야 하는 보조 정보다.
            } finally {
                if (!cancelled) setLogsLoaded(true);
            }
        })();
        return () => { cancelled = true; };
    }, []);

    const cells = [
        {
            number: '01',
            title: '자유 연습',
            desc: '기준 영상과 연습 영상을 업로드하여 AI 분석을 받아보세요',
            link: '/practice',
        },
        {
            number: '02',
            title: '숙제',
            desc: user?.teamName
                ? '팀에서 부여한 숙제를 확인하고 제출하세요'
                : '팀에 가입하면 팀 숙제에 참여할 수 있어요',
            link: '/assignments',
        },
        {
            number: '03',
            title: '내 기록',
            desc: '지금까지의 연습 기록과 분석 결과를 확인하세요',
            link: '/logs',
        },
    ];

    return (
        <div className="dashboard page dashboard-countboard">
            <div className="container">
                <header className="cb-header">
                    <h1>안녕하세요, {user?.nickname || '댄서'}님</h1>
                </header>

                {/* ===== 카운트 요약 스트립 — 이 화면의 증거 ===== */}
                <section className={`cb-strip${logsLoaded && recentLog?.status === 'COMPLETED' && recentLog.issueCount != null ? ' cb-strip-has-count' : ''}`}>
                    {!logsLoaded ? (
                        <span className="cb-strip-status">불러오는 중…</span>
                    ) : recentLog?.status === 'COMPLETED' && recentLog.issueCount != null ? (
                        <>
                            <span className="cb-strip-number">{recentLog.issueCount}</span>
                            <span className="cb-strip-label">
                                최근 분석 · 다듬을 구간
                                <Link to={`/logs/${recentLog.logId}`} className="cb-strip-link">자세히 보기</Link>
                            </span>
                        </>
                    ) : recentLog?.status === 'PROCESSING' ? (
                        <span className="cb-strip-status">
                            최근 분석이 진행 중이에요
                            <Link to={`/logs/${recentLog.logId}`} className="cb-strip-link">보러 가기</Link>
                        </span>
                    ) : recentLog?.status === 'WAITING' ? (
                        <span className="cb-strip-status">
                            구간 지정을 기다리는 기록이 있어요
                            <Link to={`/logs/${recentLog.logId}`} className="cb-strip-link">이어서 하기</Link>
                        </span>
                    ) : recentLog?.status === 'FAILED' ? (
                        <span className="cb-strip-status">
                            최근 분석이 실패했어요
                            <Link to={`/logs/${recentLog.logId}`} className="cb-strip-link">다시 시도하기</Link>
                        </span>
                    ) : (
                        <span className="cb-strip-status">첫 분석을 기다리는 빈 칸이에요</span>
                    )}
                </section>

                {/* ===== 다음 할 일 — 카운트보드 칸 ===== */}
                <section className="cb-cells">
                    {cells.map((cell) => (
                        <Link key={cell.number} to={cell.link} className="cb-cell">
                            <span className="cb-cell-number">{cell.number}</span>
                            <span className="cb-cell-title">{cell.title}</span>
                            <span className="cb-cell-desc">{cell.desc}</span>
                        </Link>
                    ))}
                </section>

                {user?.isLeader && (
                    <section className="cb-cells cb-cells-leader">
                        <Link to="/assignments/new" className="cb-cell">
                            <span className="cb-cell-number">+</span>
                            <span className="cb-cell-title">숙제 생성</span>
                            <span className="cb-cell-desc">팀원들에게 새로운 연습 숙제를 부여하세요</span>
                        </Link>
                    </section>
                )}

                {/* 첫 기록이 없는 사용자에게만 — 모두에게 영원히 반복되던 정적 안내를 없앴다 */}
                {logsLoaded && !hasAnyLog && (
                    <section className="cb-guide">
                        <h2>처음이신가요?</h2>
                        <ol className="cb-guide-list">
                            <li>따라 할 <b>기준 영상</b>을 준비하세요.</li>
                            <li>기준 영상을 보고 따라 춘 <b>연습 영상</b>을 촬영하세요.</li>
                            <li>두 영상을 올리면 AI가 다듬을 구간을 짚어드려요.</li>
                        </ol>
                        <Link to="/practice" className="cb-guide-cta">자유 연습 시작하기</Link>
                    </section>
                )}
            </div>
        </div>
    );
}
