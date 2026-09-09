import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Film, Pause, Play } from 'lucide-react';
import './SyncedComparison.css';

/**
 * 기준 영상과 내 영상을 **같은 안무 지점에 맞춰** 나란히 재생한다.
 *
 * 서버에서 비교 영상을 만들어 내려주는 방법도 있었지만 쓰지 않았다.
 * - 렌더링에 분석 시간이 60~90초 더 든다. 지금도 3분 넘게 걸려서 제일 큰 불만이다.
 * - OpenCV가 내보내는 mp4v(MPEG-4 Part 2)는 브라우저가 재생하지 못하는 경우가 많다.
 * - 무엇보다 **다 만들어진 영상은 되감고 반복할 수 없다.** 연습에 필요한 건
 *   "이 두 마디만 0.5배속으로 열 번 보기"인데, 그건 원본 두 개를 직접 돌려야 된다.
 *
 * 대신 서버는 DTW가 찾은 대응표(`syncMap`)만 준다 — 30초 영상 기준 5KB, 만드는
 * 시간은 사실상 0. 맞추는 일은 여기서 한다.
 *
 * **연습 영상이 주인이다.** 사용자가 보는 건 자기 영상이고, 기준 영상이 그것을
 * 따라간다. 반대로 하면 사용자가 자기 영상을 원하는 지점에 둘 수 없다.
 */

// 기준 영상이 이만큼 어긋나면 따라잡기를 포기하고 즉시 그 지점으로 옮긴다.
// 사람이 어긋남을 느끼는 한계(대략 0.1~0.2초)보다 조금 크게 잡았다 —
// 더 좁히면 배속 조정으로 흡수할 수 있는 오차에도 계속 seek이 걸려 화면이 튄다.
const HARD_SEEK_SEC = 0.25;

// 남은 오차를 배속으로 줄이는 정도. 크면 출렁이고, 작으면 못 따라잡는다.
const CHASE_GAIN = 1.2;
const RATE_MIN = 0.25;
const RATE_MAX = 4.0;

const SPEEDS = [0.25, 0.5, 1];

/**
 * 대응표를 "연습 시각 → 기준 시각" 함수로 바꾼다.
 *
 * 표는 0.1초 간격이라 그 사이는 선형 보간한다. 표 밖은 양 끝 값으로 고정한다 —
 * 안무 구간을 지정했다면 그 바깥은 대응 자체가 없기 때문이다.
 */
function buildMapper(pairs) {
    if (!Array.isArray(pairs) || pairs.length < 2) return null;

    const xs = pairs.map((p) => p[0]);
    const ys = pairs.map((p) => p[1]);
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
     * 국소 기울기 = 기준 영상이 연습 영상 대비 몇 배로 흘러야 하는지.
     *
     * 이걸 배속에 반영하지 않으면, 안무를 나보다 빠르게 추는 구간에서 기준 영상이
     * 계속 뒤처지다가 `HARD_SEEK_SEC`에 걸려 툭툭 건너뛴다. 기울기를 미리 반영하면
     * 보정할 오차 자체가 거의 남지 않는다.
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
    const refVideo = useRef(null);
    const pracVideo = useRef(null);
    const rafId = useRef(0);

    const [playing, setPlaying] = useState(false);
    const [speed, setSpeed] = useState(1);
    const [now, setNow] = useState(0);
    const [loop, setLoop] = useState(true);
    const [audio, setAudio] = useState('reference');  // reference | practice | none
    const [ready, setReady] = useState(false);

    const mapper = useMemo(() => buildMapper(syncMap), [syncMap]);

    // 재생 범위. 대응표가 있으면 안무 구간, 없으면 영상 전체.
    const range = useMemo(() => {
        if (!mapper) return null;
        return { start: mapper.start, end: mapper.end };
    }, [mapper]);

    // 반복 구간. 구간을 고르고 '반복'이 켜져 있을 때만.
    // ref로 들고 있는 이유: rAF 루프가 매 프레임 읽는데, state로 두면 루프를
    // 다시 만들어야 해서 재생이 끊긴다.
    const loopSpan = useRef(null);
    useEffect(() => {
        loopSpan.current =
            loop && selectedIssue
                ? { start: selectedIssue.start_sec, end: selectedIssue.end_sec }
                : null;
    }, [loop, selectedIssue]);

    /** 기준 영상을 연습 영상의 현재 위치에 맞춘다. */
    const syncOnce = useCallback((practiceTime, immediate) => {
        const r = refVideo.current;
        if (!r || !mapper) return;
        const target = mapper.at(practiceTime);
        if (!Number.isFinite(target)) return;

        if (immediate || Math.abs(r.currentTime - target) > HARD_SEEK_SEC) {
            r.currentTime = target;
            r.playbackRate = 1;
            return;
        }
        const drift = target - r.currentTime;
        const wanted = mapper.slopeAt(practiceTime) * speed + drift * CHASE_GAIN;
        r.playbackRate = Math.min(RATE_MAX, Math.max(RATE_MIN, wanted || speed));
    }, [mapper, speed]);

    // 재생 중에는 매 프레임 위치를 확인한다.
    //
    // `timeupdate` 이벤트로는 안 된다 — 브라우저가 초당 4번 정도만 쏘기 때문에
    // 그 사이 기준 영상이 최대 0.25초까지 벌어진다. 반복 구간의 끝을 정확히
    // 잡는 것도 이 주기로는 늦는다.
    useEffect(() => {
        if (!playing) return;

        const tick = () => {
            const p = pracVideo.current;
            if (p) {
                const t = p.currentTime;
                setNow(t);

                const span = loopSpan.current;
                if (span && t >= span.end) {
                    p.currentTime = span.start;
                    syncOnce(span.start, true);
                } else if (range && t >= range.end) {
                    p.pause();
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

    // 배속·음소거는 재생 중이 아닐 때도 반영돼야 한다.
    useEffect(() => {
        const p = pracVideo.current;
        if (p) p.playbackRate = speed;
    }, [speed]);

    useEffect(() => {
        const p = pracVideo.current;
        const r = refVideo.current;
        if (p) p.muted = audio !== 'practice';
        if (r) r.muted = audio !== 'reference';
    }, [audio]);

    const seekTo = useCallback((t, alsoPlay) => {
        const p = pracVideo.current;
        if (!p) return;
        const clamped = range
            ? Math.min(Math.max(t, range.start), range.end)
            : Math.max(t, 0);
        p.currentTime = clamped;
        setNow(clamped);
        syncOnce(clamped, true);
        if (alsoPlay && !playing) {
            // 두 영상을 함께 굴린다. 기준 영상도 재생 상태여야 배속으로
            // 따라잡을 수 있다 — seek만으로 맞추면 화면이 계속 튄다.
            p.play().catch(() => {});
            refVideo.current?.play().catch(() => {});
            setPlaying(true);
        }
    }, [range, syncOnce, playing]);

    const toggle = useCallback(() => {
        const p = pracVideo.current;
        const r = refVideo.current;
        if (!p) return;
        if (playing) {
            p.pause();
            r?.pause();
            setPlaying(false);
        } else {
            if (range && (p.currentTime < range.start || p.currentTime >= range.end - 0.05)) {
                p.currentTime = range.start;
            }
            syncOnce(p.currentTime, true);
            p.play().catch(() => {});
            r?.play().catch(() => {});
            setPlaying(true);
        }
    }, [playing, range, syncOnce]);

    // 구간을 고르면 그 시작으로 이동한다.
    useEffect(() => {
        if (selectedIssue) seekTo(selectedIssue.start_sec, true);
        // seekTo는 재생 상태에 따라 새로 만들어지는데, 그때마다 되감기면
        // 재생 중에 위치가 계속 앞으로 튄다. 선택이 바뀔 때만 움직인다.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedIssue]);

    // 스페이스바로 재생/정지. 연습하면서 쓰려면 키보드가 편하다.
    useEffect(() => {
        const onKey = (e) => {
            const tag = e.target?.tagName;
            if (tag === 'INPUT' || tag === 'TEXTAREA') return;
            if (e.code === 'Space') { e.preventDefault(); toggle(); }
            if (e.code === 'ArrowLeft') seekTo((pracVideo.current?.currentTime ?? 0) - 0.5, false);
            if (e.code === 'ArrowRight') seekTo((pracVideo.current?.currentTime ?? 0) + 0.5, false);
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [toggle, seekTo]);

    const onLoaded = useCallback(() => {
        if (pracVideo.current && refVideo.current) {
            setReady(true);
            if (range) {
                pracVideo.current.currentTime = range.start;
                syncOnce(range.start, true);
            }
        }
    }, [range, syncOnce]);

    if (!mapper) {
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
    const refNow = mapper.at(now);

    return (
        <div className="synced card">
            <div className="synced-head">
                <h3 className="heading-icon"><Film size={20} /> 나란히 비교</h3>
                <p className="hint-text">
                    두 영상이 <b>같은 안무 지점</b>에 맞춰 함께 움직입니다.
                    아래 구간을 누르면 그 대목만 반복해서 볼 수 있어요.
                </p>
            </div>

            <div className="synced-videos">
                <div className="synced-pane">
                    <span className="synced-tag ref">기준</span>
                    <video
                        ref={refVideo}
                        src={referenceSrc}
                        preload="auto"
                        playsInline
                        muted={audio !== 'reference'}
                        onLoadedMetadata={onLoaded}
                    />
                    <span className="synced-time">{fmt(refNow)}</span>
                </div>
                <div className="synced-pane">
                    <span className="synced-tag me">내 영상</span>
                    <video
                        ref={pracVideo}
                        src={practiceSrc}
                        preload="auto"
                        playsInline
                        muted={audio !== 'practice'}
                        onLoadedMetadata={onLoaded}
                    />
                    <span className="synced-time">{fmt(now)}</span>
                </div>
            </div>

            {/* 타임라인 — 내 영상 기준. 지적 구간이 어디에 몰려 있는지 한눈에 보인다. */}
            <div className="synced-timeline">
                <div className="synced-track">
                    {issues.map((it, i) => {
                        const left = ((it.start_sec - range.start) / span) * 100;
                        const width = Math.max(((it.end_sec - it.start_sec) / span) * 100, 0.8);
                        const active = selectedIssue && selectedIssue.rank === it.rank;
                        return (
                            <button
                                key={it.rank ?? i}
                                type="button"
                                className={`synced-marker${active ? ' active' : ''}`}
                                style={{ left: `${left}%`, width: `${width}%` }}
                                title={`${it.start_sec.toFixed(1)}s · ${it.message}`}
                                onClick={() => onSelectIssue?.(active ? null : it)}
                            />
                        );
                    })}
                    <div className="synced-playhead" style={{ left: `${pos}%` }} />
                    <input
                        className="synced-scrub"
                        type="range"
                        min={range.start}
                        max={range.end}
                        step={0.02}
                        value={now}
                        onChange={(e) => seekTo(parseFloat(e.target.value), false)}
                        aria-label="재생 위치"
                    />
                </div>
                <div className="synced-times">
                    <span>{fmt(now - range.start)}</span>
                    <span>{fmt(span)}</span>
                </div>
            </div>

            <div className="synced-controls">
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

            {selectedIssue && (
                <div className="synced-selected">
                    <b>{selectedIssue.group}</b> · {selectedIssue.message}
                    <span className="synced-selected-time">
                        {selectedIssue.start_sec.toFixed(1)}s ~ {selectedIssue.end_sec.toFixed(1)}s
                    </span>
                    <button className="btn btn-sm btn-outline" onClick={() => onSelectIssue?.(null)}>
                        선택 해제
                    </button>
                </div>
            )}
        </div>
    );
}
