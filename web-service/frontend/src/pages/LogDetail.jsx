import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
    getPracticeLog, updateTrim, analyzeLog, getVideoUrl, getAnalysisProgress,
} from '../api/client';
import VideoTrimmer from '../components/VideoTrimmer';
import { enablePush, disablePush, currentSubscription, pushSupported, isIOS, isStandalone } from '../push';
import SyncedComparison from '../components/SyncedComparison';
import './LogDetail.css';

// 진행 상황 폴링 주기.
//
// 예전에는 5초마다 상세를 다시 불러 상태만 봤다. 3분 동안 화면에 변화가
// 하나도 없어서 멈춘 것과 구분이 안 됐다. 지금은 단계를 물어보므로 조금 더
// 자주 확인한다 — 응답이 작고(수백 바이트) 분석 서버 부하도 없다.
const PROGRESS_POLL_MS = 2000;

// 단계 안에서의 세부 진행은 서버도 모른다. 단계가 바뀐 뒤 흐른 시간으로
// 단계 끝에 **점근**하게만 움직인다 — 끝을 넘지 않으므로 "다 찼는데 안 끝난다"는
// 인상은 주지 않고, 그러면서도 막대가 멈춰 있지 않다.
const STAGE_EASE_SEC = 45;

/**
 * 화면에 그릴 진행률.
 *
 * 서버는 "지금 어느 단계인지"와 그 단계의 시작·끝 퍼센트만 안다. 단계 안에서
 * 얼마나 왔는지는 아무도 모른다 — 포즈 추출은 중간 보고를 하지 않는다.
 * 그래서 단계 끝에 **점근**만 시킨다. 끝을 넘지 않으니 거짓말이 아니고,
 * 막대가 멈춰 있지도 않다.
 */
function computeProgressPct(progress, stageStartedAtMs) {
    if (!progress || progress.pct == null) return 0;
    const lo = progress.pct;
    const hi = progress.nextPct ?? lo;
    const sec = Math.max(0, (Date.now() - stageStartedAtMs) / 1000);
    return lo + (hi - lo) * (1 - Math.exp(-sec / STAGE_EASE_SEC));
}

function safeParse(json, fallback) {
    if (!json) return fallback;
    try {
        return JSON.parse(json);
    } catch {
        return fallback;
    }
}

export default function LogDetail() {
    const { id } = useParams();
    const [log, setLog] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [starting, setStarting] = useState(false);
    const [progress, setProgress] = useState(null);
    const [selectedIssue, setSelectedIssue] = useState(null);
    // 시간 순 / 우선순위 순. 기본은 시간 순이다 — 안무는 순서대로 연습하는
    // 것이라, 심각도 순으로 늘어놓으면 영상 앞뒤를 계속 오가야 한다.
    const [order, setOrder] = useState('time');
    // 막대를 부드럽게 움직이기 위한 로컬 시계
    const [tick, setTick] = useState(0);
    // null=확인 전, true=구독됨, false=꺼짐
    const [pushOn, setPushOn] = useState(null);
    const [pushNote, setPushNote] = useState('');
    const stageStartedAt = useRef(0);
    const prevStatus = useRef(null);

    // WAITING 상태에서 구간을 다시 지정할 때 쓰는 로컬 값
    const [refStart, setRefStart] = useState(null);
    const [refEnd, setRefEnd] = useState(null);
    const [pracStart, setPracStart] = useState(null);
    const [pracEnd, setPracEnd] = useState(null);

    const loadLog = useCallback(async () => {
        try {
            const data = await getPracticeLog(id);
            setLog(data);
            setRefStart(data.referenceStartSec ?? null);
            setRefEnd(data.referenceEndSec ?? null);
            setPracStart(data.practiceStartSec ?? null);
            setPracEnd(data.practiceEndSec ?? null);
            setError('');
        } catch (err) {
            setError(err.message || '기록을 불러오지 못했습니다.');
        } finally {
            setLoading(false);
        }
    }, [id]);

    useEffect(() => {
        loadLog();
    }, [loadLog]);

    // PROCESSING 동안 진행 단계를 폴링한다.
    //
    // 이 응답에는 Spring이 아는 status도 함께 들어 있어서 완료 감지까지 겸한다.
    // 상세를 통째로 다시 부르는 것보다 가볍다.
    //
    // 탭이 백그라운드에 있으면 브라우저가 setInterval을 1분에 한 번 수준으로
    // 늦춘다. 분석이 3분 가까이 걸려 그 사이 다른 탭을 보는 것이 자연스러운데,
    // 돌아왔을 때 아직 "분석 중"으로 보이면 멈춘 것처럼 느껴진다.
    // → 탭이 다시 보이는 순간 한 번 즉시 갱신한다.
    useEffect(() => {
        if (log?.status !== 'PROCESSING') return;
        let cancelled = false;

        const check = async () => {
            try {
                const p = await getAnalysisProgress(id);
                if (cancelled) return;
                setProgress(p);
                if (p.status !== 'PROCESSING') await loadLog();
            } catch {
                // 진행 조회는 없어도 되는 정보다. 막히면 상세로 완료를 확인한다.
                if (!cancelled) await loadLog();
            }
        };

        check();
        const timer = setInterval(check, PROGRESS_POLL_MS);
        const onVisible = () => { if (!document.hidden) check(); };
        document.addEventListener('visibilitychange', onVisible);

        return () => {
            cancelled = true;
            clearInterval(timer);
            document.removeEventListener('visibilitychange', onVisible);
        };
    }, [log?.status, loadLog, id]);

    // 알림 구독 상태 확인
    useEffect(() => {
        if (!pushSupported()) { setPushOn(false); return; }
        currentSubscription().then((s) => setPushOn(!!s)).catch(() => setPushOn(false));
    }, []);

    const togglePush = async () => {
        setPushNote('');
        if (pushOn) {
            await disablePush();
            setPushOn(false);
            return;
        }
        const result = await enablePush();
        if (result === 'ok') {
            setPushOn(true);
            return;
        }
        setPushNote({
            denied: '브라우저에서 알림이 차단돼 있습니다. 주소창 옆 설정에서 허용해주세요.',
            'no-key': '서버에 알림이 설정되어 있지 않습니다.',
            unsupported: isIOS() && !isStandalone()
                ? '아이폰에서는 공유 → "홈 화면에 추가"를 한 뒤에 알림을 켤 수 있습니다.'
                : '이 브라우저는 푸시 알림을 지원하지 않습니다.',
            error: '알림을 켜지 못했습니다. 잠시 후 다시 시도해주세요.',
        }[result] ?? '알림을 켜지 못했습니다.');
    };

    // 단계가 바뀐 시각을 기록한다. 막대를 부드럽게 밀기 위해서다.
    useEffect(() => {
        stageStartedAt.current = Date.now();
    }, [progress?.stage]);

    // 분석 중에만 도는 시계. 막대가 멈춰 있으면 진행 자체가 멈춘 것처럼 보인다.
    useEffect(() => {
        if (log?.status !== 'PROCESSING') return;
        const t = setInterval(() => setTick((n) => n + 1), 500);
        return () => clearInterval(t);
    }, [log?.status]);

    // 화면이 열려 있을 때의 알림.
    //
    // **이건 보조 수단이다.** 탭을 닫거나 폰을 잠그면 이 코드는 아예 돌지 않는다.
    // 그 경우를 담당하는 건 서버가 보내는 푸시(서비스 워커)다 — `src/push.js`.
    // 여기서 한 번 더 띄우는 이유는 푸시를 켜지 않은 사용자도 화면을 보고 있으면
    // 바로 알 수 있어야 하기 때문이다. 탭 제목도 같이 바꾼다.
    useEffect(() => {
        const prev = prevStatus.current;
        const cur = log?.status;
        prevStatus.current = cur;
        if (prev !== 'PROCESSING' || cur === 'PROCESSING' || !cur) return;

        const done = cur === 'COMPLETED';
        const title = done ? '분석이 끝났어요' : '분석에 실패했어요';
        const body = done
            ? `다듬을 구간 ${log?.issueCount ?? 0}개를 찾았습니다.`
            : '결과 화면에서 다시 시도할 수 있습니다.';

        document.title = `${done ? '✅' : '⚠️'} ${title}`;
        try {
            if ('Notification' in window && Notification.permission === 'granted') {
                new Notification(title, { body, tag: `log-${id}` });
            }
        } catch {
            // 알림이 막혀 있어도 화면은 정상 동작해야 한다.
        }
    }, [log?.status, log?.issueCount, id]);

    const handleStartAnalysis = async () => {
        setStarting(true);
        setError('');
        // 권한 요청은 사용자 동작 안에서만 가능하다. 여기가 그 자리다.
        // 분석이 3분 걸리므로 시작하는 김에 알림까지 켜두는 것이 자연스럽다.
        try {
            if (pushSupported() && Notification.permission === 'default') {
                const r = await enablePush();
                if (r === 'ok') setPushOn(true);
            }
        } catch { /* 알림을 못 써도 분석은 진행한다 */ }
        try {
            await updateTrim(id, {
                referenceStartSec: refStart,
                referenceEndSec: refEnd,
                practiceStartSec: pracStart,
                practiceEndSec: pracEnd,
            });
            await analyzeLog(id);
            await loadLog();
        } catch (err) {
            setError(err.message || '분석 시작에 실패했습니다.');
        } finally {
            setStarting(false);
        }
    };

    const formatDate = (dateString) => {
        if (!dateString) return '-';
        return new Date(dateString).toLocaleDateString('ko-KR', {
            year: 'numeric', month: 'long', day: 'numeric',
            hour: '2-digit', minute: '2-digit',
        });
    };

    if (loading) {
        return (
            <div className="page">
                <div className="loading"><div className="spinner"></div></div>
            </div>
        );
    }

    if (error && !log) {
        return (
            <div className="page">
                <div className="container">
                    <div className="auth-error">{error}</div>
                    <Link to="/logs" className="btn btn-secondary mt-3">← 목록으로</Link>
                </div>
            </div>
        );
    }

    const topIssuesRaw = safeParse(log?.topIssuesJson, []);
    const syncMap = safeParse(log?.syncMapJson, null);

    // 화면에 뿌릴 순서.
    //
    // **기본은 시간 순이다.** 안무는 순서대로 연습하는 것이라, 심각도 순으로
    // 늘어놓으면 8초 → 24초 → 9초처럼 영상 앞뒤를 계속 오가게 된다.
    // 심각도 정보는 버리지 않고 순위 배지로 남긴다 — 무엇부터 고칠지는
    // 사람이 정할 몫이고, 그러려면 둘 다 보여야 한다.
    // 훅을 쓰지 않는다 — 이 계산은 이른 return(로딩·에러) 뒤에 있어서
    // useMemo를 두면 렌더마다 훅 호출 순서가 달라진다. 항목이 10개뿐이라
    // 매 렌더 정렬해도 비용이 없다.
    const topIssues = (() => {
        const list = topIssuesRaw.map((it, i) => ({ ...it, rank: it.rank ?? i + 1 }));
        return order === 'time'
            ? [...list].sort((a, b) => (a.start_sec ?? 0) - (b.start_sec ?? 0))
            : list;
    })();

    // 이미지 URL은 구간 JSON이 아니라 응답의 별도 배열로 온다. 순서는 구간 순위와
    // 같고, 이미지를 만들지 못한 구간 자리에는 null이 들어 있다.
    const issueImageUrls = log?.issueImageUrls ?? [];
    // tick이 0.5초마다 바뀌면서 이 값이 다시 계산된다.
    void tick;
    const progressPct = computeProgressPct(progress, stageStartedAt.current);

    const unreliableSpans = safeParse(log?.unreliableSpansJson, []);
    const quality = safeParse(log?.qualityJson, null);
    const bothStartsSet = refStart != null && pracStart != null;

    return (
        <div className="log-detail-page page">
            <div className="container">
                <Link to="/logs" className="back-link">← 연습 기록</Link>

                {error && <div className="auth-error mb-3">{error}</div>}

                {/* ===== 상태별 헤드라인 ===== */}
                {log?.status === 'COMPLETED' && (
                    <div className="result-section">
                        <div className="issue-count-display">
                            <span className="issue-count-number">{log.issueCount ?? '-'}</span>
                            <span className="issue-count-label">개 구간에서 다듬을 동작을 찾았어요</span>
                        </div>
                        <p className="analyzed-at">분석 완료: {formatDate(log.analyzedAt)}</p>
                        {log.feedback && <p className="feedback-content">{log.feedback}</p>}
                    </div>
                )}

                {log?.status === 'PROCESSING' && (
                    <div className="pending-section card">
                        <span className="pending-icon">⏳</span>
                        <h2>{progress?.label ?? '분석 준비 중'}</h2>

                        <div className="progress-bar">
                            <div
                                className="progress-fill"
                                style={{ width: `${progressPct}%` }}
                            />
                        </div>
                        <div className="progress-meta">
                            <span>{progressPct.toFixed(0)}%</span>
                            {progress?.elapsedSec != null && (
                                <span>{Math.round(progress.elapsedSec)}초 경과</span>
                            )}
                        </div>

                        <p className="pending-text">
                            {progress?.stage
                                ? '두 영상에서 관절을 하나씩 찾아 맞추는 중입니다. 보통 3분쯤 걸려요.'
                                : '분석 서버에 작업을 맡기는 중입니다.'}
                            <br />
                            <b>이 창을 닫아도 분석은 계속됩니다.</b>
                        </p>

                        <div className="push-toggle">
                            <button className="btn btn-sm btn-outline" onClick={togglePush}>
                                {pushOn ? '🔔 알림 켜짐 (끄기)' : '🔕 끝나면 알림 받기'}
                            </button>
                            {isIOS() && !isStandalone() && (
                                <span className="hint-text">
                                    아이폰은 공유 → “홈 화면에 추가” 후에 알림을 받을 수 있어요
                                </span>
                            )}
                            {pushNote && <span className="push-note">{pushNote}</span>}
                        </div>
                    </div>
                )}

                {log?.status === 'FAILED' && (
                    <div className="pending-section card">
                        <span className="pending-icon">⚠️</span>
                        <h2>분석에 실패했습니다</h2>
                        {log.feedback && <p className="pending-text">{log.feedback}</p>}
                        <button
                            className="btn btn-primary mt-3"
                            onClick={handleStartAnalysis}
                            disabled={starting}
                        >
                            {starting ? '재시도 중...' : '다시 분석하기'}
                        </button>
                    </div>
                )}

                {/* 기준 영상이 없으면 분석 자체가 불가능하다. 지금은 기준 영상
                    업로드가 기록을 만들지 않으므로 이 상태는 드물지만, 기준 영상이
                    지워진 기록 등이 있을 수 있어 분석 버튼을 감춘다 — 눌러도 반드시
                    실패하기 때문이다. */}
                {log?.status === 'WAITING' && !log?.referenceVideoId && (
                    <div className="pending-section card">
                        <span className="pending-icon">📄</span>
                        <h2>분석할 수 없는 기록입니다</h2>
                        <p className="pending-text">
                            비교할 기준 영상이 연결되어 있지 않습니다.
                            자유 연습에서 기준 영상과 연습 영상을 함께 올려주세요.
                        </p>
                        <Link to="/practice" className="btn btn-primary mt-3">
                            자유 연습으로 가기
                        </Link>
                    </div>
                )}

                {/* ===== WAITING: 구간 지정 + 분석 시작 ===== */}
                {log?.status === 'WAITING' && log?.referenceVideoId && (
                    <div className="trim-intro card mb-3">
                        <h3>⏱ 분석을 시작하기 전에 안무 시작 지점을 맞춰주세요</h3>
                        <p className="hint-text">
                            두 영상에서 안무가 실제로 시작하는 순간을 표시하면 정렬 정확도가
                            올라갑니다. 끝 지점은 앞뒤 여백이 많을 때만 지정하면 됩니다.
                        </p>
                        {!bothStartsSet && (
                            <p className="trim-warning">
                                ⚠️ 시작 지점을 지정하지 않으면 정확도가 떨어질 수 있습니다.
                            </p>
                        )}

                        <div className="upload-grid mt-3">
                            {log.referenceVideoId && (
                                <VideoTrimmer
                                    label="📹 기준 영상"
                                    videoSrc={getVideoUrl(log.referenceVideoId)}
                                    startSec={refStart}
                                    endSec={refEnd}
                                    onChangeStart={setRefStart}
                                    onChangeEnd={setRefEnd}
                                />
                            )}
                            {log.practiceVideoId && (
                                <VideoTrimmer
                                    label="🎬 연습 영상"
                                    videoSrc={getVideoUrl(log.practiceVideoId)}
                                    startSec={pracStart}
                                    endSec={pracEnd}
                                    onChangeStart={setPracStart}
                                    onChangeEnd={setPracEnd}
                                />
                            )}
                        </div>

                        <div className="submit-section mt-3">
                            <button
                                className="btn btn-primary btn-lg"
                                onClick={handleStartAnalysis}
                                disabled={starting}
                            >
                                {starting ? '시작하는 중...' : (bothStartsSet ? '분석 시작하기 🚀' : '구간 없이 분석 시작하기')}
                            </button>
                        </div>
                    </div>
                )}

                {/* ===== 품질 경고 ===== */}
                {log?.status === 'COMPLETED' && log.qualityWarning && (
                    <div className="quality-warning card mb-3">
                        ⚠️ {log.qualityWarning}
                    </div>
                )}

                {/* ===== 구간 지정 여부 안내 (완료 상태) ===== */}
                {log?.status === 'COMPLETED' && !(log.referenceStartSec != null && log.practiceStartSec != null) && (
                    <div className="trim-note card mb-3">
                        💡 안무 시작 지점을 지정하지 않고 분석했습니다.
                        정확도를 높이고 싶다면 위쪽 영상에서 시작 지점을 지정한 뒤
                        다시 분석해보세요.
                    </div>
                )}

                {/* ===== 나란히 비교 (이 화면의 주인공) ===== */}
                {log?.status === 'COMPLETED' && log?.referenceVideoId && log?.practiceVideoId && (
                    <SyncedComparison
                        referenceSrc={getVideoUrl(log.referenceVideoId)}
                        practiceSrc={getVideoUrl(log.practiceVideoId)}
                        syncMap={syncMap}
                        issues={topIssues}
                        selectedIssue={selectedIssue}
                        onSelectIssue={setSelectedIssue}
                    />
                )}

                {/* ===== 상위 지적 구간 ===== */}
                {log?.status === 'COMPLETED' && topIssues.length > 0 && (
                    <div className="issues-section card">
                        <div className="issues-head">
                            <h3>💬 다듬으면 좋은 동작 {topIssues.length}개</h3>
                            <div className="order-toggle">
                                <button
                                    className={`btn btn-sm ${order === 'time' ? 'btn-secondary' : 'btn-outline'}`}
                                    onClick={() => setOrder('time')}
                                >
                                    시간 순
                                </button>
                                <button
                                    className={`btn btn-sm ${order === 'severity' ? 'btn-secondary' : 'btn-outline'}`}
                                    onClick={() => setOrder('severity')}
                                >
                                    우선순위 순
                                </button>
                            </div>
                        </div>
                        <p className="hint-text">
                            AI가 고른 후보입니다. <b>무엇부터 고칠지는 직접 정하세요</b> —
                            항목을 누르면 위 비교 화면이 그 구간을 반복 재생합니다.
                            왼쪽 숫자는 심각도 순위예요.
                        </p>
                        <div className="issue-list">
                            {topIssues.map((issue) => {
                              const idx = issue.rank - 1;   // 이미지 슬롯은 심각도 순위 기준
                              const active = selectedIssue?.rank === issue.rank;
                              return (
                                <div
                                    key={issue.rank}
                                    className={`issue-item${active ? ' active' : ''}`}
                                    onClick={() => setSelectedIssue(active ? null : issue)}
                                >
                                    <div className="issue-rank">{issue.rank}</div>
                                    <div className="issue-body">
                                        <div className="issue-top">
                                            <span className="issue-group">{issue.group}</span>
                                            <span className="issue-time">
                                                {issue.start_sec?.toFixed(1)}s ~ {issue.end_sec?.toFixed(1)}s
                                            </span>
                                        </div>
                                        <p className="issue-message">{issue.message}</p>
                                        {issueImageUrls[idx] && (
                                            <img
                                                className="issue-image"
                                                src={issueImageUrls[idx]}
                                                alt={`${issue.group} 비교 (왼쪽 기준, 오른쪽 내 영상)`}
                                                loading="lazy"
                                            />
                                        )}
                                        <div className="issue-meta">
                                            <span>심각도 {issue.severity?.toFixed(1)}x</span>
                                            <span>평균 오차 {issue.mean_error_deg?.toFixed(0)}°</span>
                                        </div>
                                    </div>
                                    <div className="issue-actions">
                                        <button
                                            className={`btn btn-sm ${active ? 'btn-secondary' : 'btn-outline'}`}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setSelectedIssue(active ? null : issue);
                                            }}
                                        >
                                            {active ? '반복 중' : '이 구간 보기'}
                                        </button>
                                        {/* 이미지 URL은 구간 JSON이 아니라 응답의
                                            issueImageUrls에서 온다. 저장된 것은 키뿐이고
                                            서명 URL은 조회 시점에 새로 만들어지기 때문이다
                                            (서명 URL을 저장하면 곧 만료돼 열리지 않는다). */}
                                        {issueImageUrls[idx] && (
                                            <a
                                                className="btn btn-sm btn-secondary"
                                                href={issueImageUrls[idx]}
                                                target="_blank"
                                                rel="noreferrer"
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                크게 보기
                                            </a>
                                        )}
                                    </div>
                                </div>
                              );
                            })}
                        </div>
                    </div>
                )}

                {/* ===== 확인 어려움 구간 ===== */}
                {log?.status === 'COMPLETED' && unreliableSpans.length > 0 && (
                    <div className="unreliable-section card">
                        <h3>🤔 확인이 어려웠던 구간</h3>
                        <p className="hint-text">{log.unreliableNote}</p>
                        <div className="unreliable-list">
                            {unreliableSpans.map((span, idx) => (
                                <span key={idx} className="badge badge-info">
                                    {span.start_sec?.toFixed(1)}s ~ {span.end_sec?.toFixed(1)}s
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                {/* ===== 품질 지표 ===== */}
                {log?.status === 'COMPLETED' && quality && (
                    <div className="quality-section card">
                        <h3>📊 분석 품질</h3>
                        <div className="quality-grid">
                            <div className="quality-item">
                                <span className="quality-label">채점된 구간 비율</span>
                                <span className="quality-value">{quality.scored_pct?.toFixed(1)}%</span>
                            </div>
                            <div className="quality-item">
                                <span className="quality-label">기준 영상 관절 검출률</span>
                                <span className="quality-value">
                                    {(quality.reference_joint_valid_ratio * 100)?.toFixed(1)}%
                                </span>
                            </div>
                            <div className="quality-item">
                                <span className="quality-label">연습 영상 관절 검출률</span>
                                <span className="quality-value">
                                    {(quality.practice_joint_valid_ratio * 100)?.toFixed(1)}%
                                </span>
                            </div>
                        </div>
                    </div>
                )}

                {/* ===== 원본 영상 =====
                    나란히 비교가 있으면 평소엔 필요 없다. 전체를 처음부터 보고
                    싶을 때만 펴서 보게 접어둔다. */}
                <details className="raw-videos card">
                    <summary>원본 영상 따로 보기</summary>
                    <div className="videos-section">
                        <div className="video-card">
                            <h3>📹 기준 영상</h3>
                            {log?.referenceVideoId ? (
                                <video controls preload="none" className="video-player"
                                    src={getVideoUrl(log.referenceVideoId)}>
                                    브라우저가 비디오 태그를 지원하지 않습니다.
                                </video>
                            ) : <p className="no-video">기준 영상 정보 없음</p>}
                        </div>
                        <div className="video-card">
                            <h3>🎬 연습 영상</h3>
                            {log?.practiceVideoId ? (
                                <video controls preload="none" className="video-player"
                                    src={getVideoUrl(log.practiceVideoId)}>
                                    브라우저가 비디오 태그를 지원하지 않습니다.
                                </video>
                            ) : <p className="no-video">연습 영상 정보 없음</p>}
                        </div>
                    </div>
                </details>

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
