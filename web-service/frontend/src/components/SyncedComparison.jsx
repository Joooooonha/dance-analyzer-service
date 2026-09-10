import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Film, Pause, Play } from 'lucide-react';
import './SyncedComparison.css';

/**
 * 기준 영상과 내 영상을 **같은 안무 지점에 맞춰** 나란히 재생한다.
 *
 * **기준 영상이 주인이다.** 기준 영상은 손대지 않은 속도로 흐르고, 내 영상이
 * 늘어나거나 줄어들며 따라간다. 정답은 기준 영상이니 그것을 왜곡하면 무엇이
 * 맞는 박자인지 알 수 없게 된다. 반대로 내 영상이 빨라지고 느려지는 것 자체가
 * **어디서 박자가 어긋났는지**를 그대로 보여준다.
 *
 * - 내 영상이 1보다 빠르게 감긴다 = 그 대목에서 내가 **느렸다** (기준이 먼저 나갔다)
 * - 1보다 느리게 감긴다 = 내가 **빨랐다**
 *
 * 서버에서 비교 영상을 만들어 내려주는 방법도 있었지만 쓰지 않았다.
 * - 렌더링에 분석 시간이 60~90초 더 든다.
 * - OpenCV가 내보내는 mp4v(MPEG-4 Part 2)는 브라우저가 재생하지 못하는 경우가 많다.
 * - 무엇보다 **다 만들어진 영상은 되감고 반복할 수 없다.** 연습에 필요한 건
 *   "이 두 마디만 0.5배속으로 열 번 보기"인데, 그건 원본 두 개를 직접 돌려야 된다.
 *
 * 대신 서버는 DTW가 찾은 대응표(`syncMap`)만 준다 — 30초 영상 기준 5KB, 만드는
 * 시간은 사실상 0. 맞추는 일은 여기서 한다.
 */

// 내 영상이 이만큼 어긋나면 따라잡기를 포기하고 즉시 그 지점으로 옮긴다.
// 사람이 어긋남을 느끼는 한계(대략 0.1~0.2초)보다 조금 크게 잡았다 —
// 더 좁히면 배속으로 흡수할 수 있는 오차에도 계속 seek이 걸려 화면이 튄다.
const HARD_SEEK_SEC = 0.25;

// 남은 오차를 배속으로 줄이는 정도. 크면 출렁이고, 작으면 못 따라잡는다.
const CHASE_GAIN = 1.2;
const RATE_MIN = 0.25;
const RATE_MAX = 4.0;

const SPEEDS = [0.25, 0.5, 1];

// 박자 어긋남 그래프의 최소 눈금(초). 잘 맞춘 영상에서 ±0.05초짜리 흔들림이
// 화면 가득 차 보이면 "많이 틀렸다"고 오해하게 된다.
const DEVIATION_MIN_SCALE_SEC = 0.3;

/** 단조 증가하는 (x, y) 표를 선형 보간 함수로 만든다. */
function interpolator(xs, ys) {
    const n = xs.length;
    const at = (t) => {
        if (t <= xs[0]) return ys[0];
        if (t >= xs[n - 1]) return ys[n - 1];
        let lo = 0;
        let hi = n - 1;
        while (hi - lo > 1) {
            const mid = (lo + hi) >> 1;
            if (xs[mid] <= t) lo = mid;
            else hi = mid;
        }
        const span = xs[hi] - xs[lo];
        const f = span > 1e-9 ? (t - xs[lo]) / span : 0;
        return ys[lo] + (ys[hi] - ys[lo]) * f;
    };

    /**
     * 국소 기울기 = y가 x 대비 몇 배로 흘러야 하는지.
     *
     * 이걸 배속에 반영하지 않으면, 내가 기준보다 느리게 춘 구간에서 내 영상이
     * 계속 뒤처지다가 `HARD_SEEK_SEC`에 걸려 툭툭 건너뛴다. 기울기를 미리
     * 반영하면 보정할 오차 자체가 거의 남지 않는다.
     */
    const slopeAt = (t) => {
        const d = 0.25;
        const lo = Math.max(xs[0], t - d);
        const hi = Math.min(xs[n - 1], t + d);
        const dt = hi - lo;
        return dt > 1e-6 ? (at(hi) - at(lo)) / dt : 1;
    };

    return { at, slopeAt, start: xs[0], end: xs[n - 1] };
}

/**
 * 대응표를 양방향 함수로 바꾼다.
 *
 * `syncMap`은 `[[연습 시각, 기준 시각], ...]`이고 둘 다 단조 증가한다.
 * 재생은 기준 영상이 주도하므로 **기준 → 연습** 방향이 주로 쓰이고,
 * 지적 구간(연습 시각 기준)을 타임라인에 얹을 때 **연습 → 기준**을 쓴다.
 */
function buildMappers(pairs) {
    if (!Array.isArray(pairs) || pairs.length < 2) return null;

    const pracToRef = interpolator(pairs.map((p) => p[0]), pairs.map((p) => p[1]));

    // 기준 시각이 같은 점이 여러 개일 수 있다(기준 영상이 멈춘 듯한 구간에서
    // 내 동작만 진행된 경우). 그대로 두면 역함수가 정의되지 않으므로 평균을 쓴다.
    const byRef = new Map();
    for (const [prac, ref] of pairs) {
        const cur = byRef.get(ref);
        if (cur) { cur.sum += prac; cur.n += 1; }
        else byRef.set(ref, { sum: prac, n: 1 });
    }
    const refXs = [...byRef.keys()].sort((a, b) => a - b);
    const refToPrac = interpolator(refXs, refXs.map((r) => {
        const v = byRef.get(r);
        return v.sum / v.n;
    }));

    return { pracToRef, refToPrac };
}

const fmt = (s) => {
    if (!Number.isFinite(s)) return '0:00.0';
    const m = Math.floor(s / 60);
    const r = s - m * 60;
    return `${m}:${r.toFixed(1).padStart(4, '0')}`;
};

export default function SyncedComparison({
    referenceSrc,
    practiceSrc,
    syncMap,
    issues = [],
    selectedIssue = null,
    onSelectIssue,
}) {
    const refVideo = useRef(null);     // 주인. 손대지 않은 속도로 흐른다
    const pracVideo = useRef(null);    // 따라가는 쪽. 늘어나고 줄어든다
    const containerRef = useRef(null); // 화면 밖에서 구간을 고르면 여기로 스크롤한다
    const rafId = useRef(0);

    const [playing, setPlaying] = useState(false);
    const [speed, setSpeed] = useState(1);
    const [now, setNow] = useState(0);          // 기준 영상 시각
    const [rate, setRate] = useState(1);        // 지금 내 영상이 감기는 배속
    const [loop, setLoop] = useState(true);
    const [audio, setAudio] = useState('reference');  // reference | practice | none
    const [ready, setReady] = useState(false);

    const mappers = useMemo(() => buildMappers(syncMap), [syncMap]);

    // 재생 범위 — **기준 영상 시각** 기준이다.
    const range = useMemo(() => {
        if (!mappers) return null;
        return { start: mappers.refToPrac.start, end: mappers.refToPrac.end };
    }, [mappers]);

    // 지적 구간은 연습 영상 시각으로 저장돼 있다. 타임라인이 기준 시각이므로 옮긴다.
    const issueSpans = useMemo(() => {
        if (!mappers) return [];
        return issues.map((it) => ({
            issue: it,
            start: mappers.pracToRef.at(it.start_sec),
            end: mappers.pracToRef.at(it.end_sec),
        }));
    }, [issues, mappers]);

    /**
     * 박자 어긋남 곡선.
     *
     * 기준 영상이 t초 흐르는 동안 나는 몇 초를 썼는가 − t. 양수면 내가 그만큼
     * **더 걸렸다**(느렸다), 음수면 **덜 걸렸다**(빨랐다). 시작점을 0으로 맞춰
     * 촬영 시작 시점 차이는 제거한다 — 그건 박자 문제가 아니다.
     */
    const deviation = useMemo(() => {
        if (!mappers || !range) return null;
        const N = 200;
        const p0 = mappers.refToPrac.at(range.start);
        const pts = [];
        let peak = DEVIATION_MIN_SCALE_SEC;
        for (let i = 0; i <= N; i++) {
            const r = range.start + ((range.end - range.start) * i) / N;
            const d = (mappers.refToPrac.at(r) - p0) - (r - range.start);
            pts.push([r, d]);
            peak = Math.max(peak, Math.abs(d));
        }
        return { pts, peak };
    }, [mappers, range]);

    // 반복 구간(기준 시각). rAF 루프가 매 프레임 읽으므로 state가 아니라 ref로 든다 —
    // state로 두면 루프를 다시 만들어야 해서 재생이 끊긴다.
    const loopSpan = useRef(null);
    useEffect(() => {
        if (!loop || !selectedIssue || !mappers) {
            loopSpan.current = null;
            return;
        }
        loopSpan.current = {
            start: mappers.pracToRef.at(selectedIssue.start_sec),
            end: mappers.pracToRef.at(selectedIssue.end_sec),
        };
    }, [loop, selectedIssue, mappers]);

    /** 내 영상을 기준 영상의 현재 위치에 맞춘다. */
    const syncOnce = useCallback((refTime, immediate) => {
        const p = pracVideo.current;
        if (!p || !mappers) return;
        const target = mappers.refToPrac.at(refTime);
        if (!Number.isFinite(target)) return;

        if (immediate || Math.abs(p.currentTime - target) > HARD_SEEK_SEC) {
            p.currentTime = target;
            p.playbackRate = speed;
            setRate(1);
            return;
        }
        const drift = target - p.currentTime;
        const slope = mappers.refToPrac.slopeAt(refTime);   // 내 시간 / 기준 시간
        const wanted = slope * speed + drift * CHASE_GAIN;
        p.playbackRate = Math.min(RATE_MAX, Math.max(RATE_MIN, wanted || speed));
        setRate(slope);
    }, [mappers, speed]);

    // 재생 중에는 매 프레임 위치를 확인한다.
    //
    // `timeupdate` 이벤트로는 안 된다 — 브라우저가 초당 4번 정도만 쏘기 때문에
    // 그 사이 두 영상이 최대 0.25초까지 벌어진다. 반복 구간의 끝을 정확히
    // 잡는 것도 이 주기로는 늦는다.
    useEffect(() => {
        if (!playing) return;

        const tick = () => {
            const r = refVideo.current;
            if (r) {
                const t = r.currentTime;
                setNow(t);

                const span = loopSpan.current;
                if (span && t >= span.end) {
                    r.currentTime = span.start;
                    syncOnce(span.start, true);
                } else if (range && t >= range.end) {
                    r.pause();
                    pracVideo.current?.pause();
                    setPlaying(false);
                } else {
                    syncOnce(t, false);
                }
            }
            rafId.current = requestAnimationFrame(tick);
        };

        rafId.current = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(rafId.current);
    }, [playing, syncOnce, range]);

    // 기준 영상의 배속은 사용자가 고른 값 그대로다. 여기만은 왜곡하지 않는다.
    useEffect(() => {
        const r = refVideo.current;
        if (r) r.playbackRate = speed;
    }, [speed]);

    useEffect(() => {
        const p = pracVideo.current;
        const r = refVideo.current;
        if (p) p.muted = audio !== 'practice';
        if (r) r.muted = audio !== 'reference';
    }, [audio]);

    const seekTo = useCallback((refTime, alsoPlay) => {
        const r = refVideo.current;
        if (!r) return;
        const clamped = range
            ? Math.min(Math.max(refTime, range.start), range.end)
            : Math.max(refTime, 0);
        r.currentTime = clamped;
        setNow(clamped);
        syncOnce(clamped, true);
        if (alsoPlay && !playing) {
            // 두 영상을 함께 굴린다. 내 영상도 재생 상태여야 배속으로 따라잡을 수
            // 있다 — seek만으로 맞추면 화면이 계속 튄다.
            r.play().catch(() => {});
            pracVideo.current?.play().catch(() => {});
            setPlaying(true);
        }
    }, [range, syncOnce, playing]);

    const toggle = useCallback(() => {
        const r = refVideo.current;
        const p = pracVideo.current;
        if (!r) return;
        if (playing) {
            r.pause();
            p?.pause();
            setPlaying(false);
        } else {
            if (range && (r.currentTime < range.start || r.currentTime >= range.end - 0.05)) {
                r.currentTime = range.start;
            }
            syncOnce(r.currentTime, true);
            r.play().catch(() => {});
            p?.play().catch(() => {});
            setPlaying(true);
        }
    }, [playing, range, syncOnce]);

    // 구간을 고르면 그 시작으로 이동한다.
    //
    // 아래 지적 구간 목록에서 고르면(critique에서 지적된 P0) 이 카드가
    // 화면 밖일 수 있다 — 영상이 조용히 바뀌어도 눈치챌 방법이 없었다.
    // 카드가 화면에 충분히 보이지 않을 때만 스크롤한다. 안에서 타임라인
    // 마커를 직접 눌렀을 때는 이미 보고 있으니 점프시키지 않는다.
    useEffect(() => {
        if (!selectedIssue || !mappers) return;
        seekTo(mappers.pracToRef.at(selectedIssue.start_sec), true);

        const el = containerRef.current;
        if (el) {
            const rect = el.getBoundingClientRect();
            const visible = rect.top >= 0 && rect.top < window.innerHeight - 200;
            if (!visible) {
                el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
        // seekTo는 재생 상태에 따라 새로 만들어지는데, 그때마다 되감기면
        // 재생 중에 위치가 계속 앞으로 튄다. 선택이 바뀔 때만 움직인다.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedIssue]);

    // 스페이스바로 재생/정지. 연습하면서 쓰려면 키보드가 편하다.
    useEffect(() => {
        const onKey = (e) => {
            const tag = e.target?.tagName;
            if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
            if (e.code === 'Space') { e.preventDefault(); toggle(); }
            if (e.code === 'ArrowLeft') seekTo((refVideo.current?.currentTime ?? 0) - 0.5, false);
            if (e.code === 'ArrowRight') seekTo((refVideo.current?.currentTime ?? 0) + 0.5, false);
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [toggle, seekTo]);

    const onLoaded = useCallback(() => {
        if (refVideo.current && pracVideo.current) {
            setReady(true);
            if (range) {
                refVideo.current.currentTime = range.start;
                syncOnce(range.start, true);
            }
        }
    }, [range, syncOnce]);

    if (!mappers || !range) {
        return (
            <div className="synced card">
                <p className="synced-empty">
                    이 분석에는 동작 대응표가 없어 나란히 비교를 할 수 없습니다.
                    다시 분석하면 만들어집니다.
                </p>
            </div>
        );
    }

    const span = range.end - range.start;
    const pos = span > 0 ? ((now - range.start) / span) * 100 : 0;
    const pracNow = mappers.refToPrac.at(now);
    const devNow = (pracNow - mappers.refToPrac.at(range.start)) - (now - range.start);

    // 지금 이 대목에서 내가 느렸는지 빨랐는지. 5% 안쪽은 "맞음"으로 본다 —
    // 그보다 작은 차이는 사람이 의도한 것이 아니라 추정 오차에 가깝다.
    const tempo = rate > 1.05 ? 'slow' : rate < 0.95 ? 'fast' : 'ok';
    const tempoText = { slow: '느림', fast: '빠름', ok: '맞음' }[tempo];

    return (
        <div className="synced card" ref={containerRef}>
            <div className="synced-head">
                <h3 className="heading-icon"><Film size={20} /> 나란히 비교</h3>
                <p className="hint-text">
                    <b>기준 영상은 원래 속도 그대로</b> 흐르고, 내 영상이 늘어나거나
                    줄어들며 따라갑니다. 내 영상이 빨리 감기면 그 대목에서 내가
                    느렸던 것이고, 느리게 감기면 빨랐던 것입니다.
                </p>
            </div>

            <div className="synced-videos">
                <div className="synced-pane">
                    <span className="synced-tag ref">기준 · 원래 속도</span>
                    <video
                        ref={refVideo}
                        src={referenceSrc}
                        preload="auto"
                        playsInline
                        muted={audio !== 'reference'}
                        onLoadedMetadata={onLoaded}
                    />
                    <span className="synced-time">{fmt(now)}</span>
                </div>
                <div className="synced-pane">
                    <span className="synced-tag me">
                        내 영상 · <span className={`synced-rate ${tempo}`}>{rate.toFixed(2)}x {tempoText}</span>
                    </span>
                    <video
                        ref={pracVideo}
                        src={practiceSrc}
                        preload="auto"
                        playsInline
                        muted={audio !== 'practice'}
                        onLoadedMetadata={onLoaded}
                    />
                    <span className="synced-time">{fmt(pracNow)}</span>
                </div>
            </div>

            {/* 편차 그래프와 타임라인은 같은 시간축·같은 순간(재생헤드)을 가리키는데
                각자 따로 그려지면 둘이 같은 걸 나타낸다는 게 보이지 않는다
                (critique에서 지적된 P2). .synced-scope로 묶고, 두 구역을 관통하는
                가이드선 하나로 "지금 이 순간"을 한 번만 표시한다. 범례 텍스트는
                가이드선이 글자를 가로지르지 않도록 scope 바깥, 아래 줄로 뺐다. */}
            <div className="synced-scope">
                {/* 박자 어긋남 — 기준 대비 내가 얼마나 앞섰는지/뒤처졌는지의 누적 차이 */}
                {deviation && (
                    <div className="synced-deviation">
                        <svg viewBox="0 0 1000 60" preserveAspectRatio="none" aria-hidden="true">
                            <line className="dev-zero" x1="0" y1="30" x2="1000" y2="30" />
                            <polyline
                                className="dev-line"
                                points={deviation.pts.map(([r, d]) => {
                                    const x = ((r - range.start) / span) * 1000;
                                    const y = 30 - (d / deviation.peak) * 26;
                                    return `${x.toFixed(1)},${y.toFixed(1)}`;
                                }).join(' ')}
                            />
                        </svg>
                    </div>
                )}

                {/* 타임라인 — 기준 영상 시각. 지적 구간이 어디에 몰려 있는지 한눈에 보인다. */}
                <div className="synced-track">
                    {issueSpans.map(({ issue, start, end }, i) => {
                        const left = ((start - range.start) / span) * 100;
                        const width = Math.max(((end - start) / span) * 100, 0.8);
                        const active = selectedIssue && selectedIssue.rank === issue.rank;
                        return (
                            <button
                                key={issue.rank ?? i}
                                type="button"
                                className={`synced-marker${active ? ' active' : ''}`}
                                style={{ left: `${left}%`, width: `${width}%` }}
                                title={`기준 ${start.toFixed(1)}s · ${issue.message}`}
                                onClick={() => onSelectIssue?.(active ? null : issue)}
                            />
                        );
                    })}
                    <input
                        className="synced-scrub"
                        type="range"
                        min={range.start}
                        max={range.end}
                        step={0.02}
                        value={now}
                        onChange={(e) => seekTo(parseFloat(e.target.value), false)}
                        aria-label="재생 위치 (기준 영상 기준)"
                    />
                </div>

                {/* 그래프의 dev-head와 타임라인의 playhead가 따로 그려지던 걸 하나로 —
                    두 구역을 관통하는 세로선 하나가 "지금"이다. */}
                <div className="synced-guide" style={{ left: `${pos}%` }} />
            </div>

            {deviation && (
                <div className="synced-dev-legend">
                    <span>↑ 내가 빨랐음</span>
                    <span className={`dev-now ${tempo}`}>
                        지금 {devNow >= 0 ? '+' : ''}{devNow.toFixed(2)}초
                        {devNow > 0.05 ? ' 뒤처짐' : devNow < -0.05 ? ' 앞섬' : ''}
                    </span>
                    <span>↓ 내가 느렸음</span>
                </div>
            )}

            <div className="synced-times">
                <span>{fmt(now - range.start)}</span>
                <span>{fmt(span)}</span>
            </div>

            {/* 재생 관련(전송)과 소리 출처(입력)는 상호작용 종류가 다르다 — 한 줄에
                구분 없이 섞여 있으면 "재생"을 찾는 데도 6개를 다 훑어야 한다
                (critique에서 지적된 P1). 두 묶음으로 시각적으로 나눈다. */}
            <div className="synced-controls">
                <div className="synced-controls-transport">
                    <button className="btn btn-primary" onClick={toggle} disabled={!ready}>
                        {playing ? <><Pause size={16} /> 정지</> : <><Play size={16} /> 재생</>}
                    </button>

                    <div className="synced-speed">
                        {SPEEDS.map((s) => (
                            <button
                                key={s}
                                className={`btn btn-sm ${speed === s ? 'btn-secondary' : 'btn-outline'}`}
                                onClick={() => setSpeed(s)}
                            >
                                {s}x
                            </button>
                        ))}
                    </div>

                    <label className="synced-check">
                        <input
                            type="checkbox"
                            checked={loop}
                            onChange={(e) => setLoop(e.target.checked)}
                        />
                        고른 구간 반복
                    </label>
                </div>

                <div className="synced-controls-audio">
                    <select
                        className="synced-audio"
                        value={audio}
                        onChange={(e) => setAudio(e.target.value)}
                        aria-label="소리"
                    >
                        <option value="reference">기준 영상 소리</option>
                        <option value="practice">내 영상 소리</option>
                        <option value="none">음소거</option>
                    </select>
                </div>
            </div>

            {selectedIssue && (
                <div className="synced-selected">
                    <b>{selectedIssue.group}</b> · {selectedIssue.message}
                    <span className="synced-selected-time">
                        내 영상 {selectedIssue.start_sec.toFixed(1)}s ~ {selectedIssue.end_sec.toFixed(1)}s
                    </span>
                    <button className="btn btn-sm btn-outline" onClick={() => onSelectIssue?.(null)}>
                        선택 해제
                    </button>
                </div>
            )}
        </div>
    );
}
