import { useEffect, useRef, useState } from 'react';
import './VideoTrimmer.css';

// 30fps 가정. 백엔드 엔진도 fps 정보가 없는 영상에는 이 값으로 대체한다
// (engine/video_utils.py FPS_FALLBACK). 프레임 단위 버튼의 이동 폭으로만
// 쓰이므로, 실제 fps가 조금 달라도 "더 세밀하게 맞추는 보조 수단"일 뿐
// 정확도에 영향을 주지 않는다 — 최종적으로 저장되는 값은 video.currentTime
// (초 단위 실수)이다.
const ASSUMED_FPS = 30;
const FRAME_STEP = 1 / ASSUMED_FPS;

/**
 * 영상 하나에서 안무 시작/끝 시각을 고르는 위젯.
 *
 * 실제로 영상을 자르지 않는다 — 타임스탬프만 골라서 상위 컴포넌트에 전달한다.
 * 정밀도가 중요하다: 시작 시각 오차가 ±0.5초를 넘으면 정렬 개선 효과가
 * 사라지고, 정렬 밴드보다 오차가 커지면 오히려 정확도가 급격히 떨어진다
 * (TASKS-SERVICE.md). 그래서 드래그만으로 끝내지 않고 프레임 단위 버튼을 둔다.
 */
export default function VideoTrimmer({
  label,
  videoSrc,
  startSec,
  endSec,
  onChangeStart,
  onChangeEnd,
}) {
  const videoRef = useRef(null);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;

    const onLoaded = () => setDuration(v.duration || 0);
    const onTime = () => setCurrentTime(v.currentTime);
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);

    v.addEventListener('loadedmetadata', onLoaded);
    v.addEventListener('timeupdate', onTime);
    v.addEventListener('play', onPlay);
    v.addEventListener('pause', onPause);
    return () => {
      v.removeEventListener('loadedmetadata', onLoaded);
      v.removeEventListener('timeupdate', onTime);
      v.removeEventListener('play', onPlay);
      v.removeEventListener('pause', onPause);
    };
  }, [videoSrc]);

  const seekBy = (delta) => {
    const v = videoRef.current;
    if (!v || !duration) return;
    v.currentTime = Math.min(Math.max(v.currentTime + delta, 0), duration);
  };

  const seekTo = (t) => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = Math.min(Math.max(t, 0), duration);
  };

  const togglePlay = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) v.play(); else v.pause();
  };

  // 지점을 찍을 때는 React state(currentTime)가 아니라 **video 엘리먼트의 값을
  // 직접** 읽는다. state는 timeupdate 이벤트로만 갱신되는데, seek 직후에는 아직
  // 이벤트가 오지 않아 이전 값(심하면 0)이 찍힌다. 시작 시각 오차가 ±0.5초를
  // 넘으면 정렬 개선 효과가 사라지므로 이 차이가 그냥 넘길 수준이 아니다.
  const markCurrent = (setter) => {
    const v = videoRef.current;
    if (!v) return;
    setter(v.currentTime);
  };

  const fmt = (t) => {
    if (!Number.isFinite(t)) return '0.00s';
    return `${t.toFixed(2)}s`;
  };

  const pct = (t) => (duration ? Math.min(100, Math.max(0, (t / duration) * 100)) : 0);

  return (
    <div className="video-trimmer">
      <div className="trimmer-header">
        <h4>{label}</h4>
        <span className="trimmer-time">{fmt(currentTime)} / {fmt(duration)}</span>
      </div>

      <video
        ref={videoRef}
        src={videoSrc}
        className="trimmer-video"
        playsInline
      />

      <div className="trimmer-timeline">
        <input
          type="range"
          className="trimmer-seekbar"
          min={0}
          max={duration || 0}
          step={0.01}
          value={currentTime}
          onChange={(e) => seekTo(Number(e.target.value))}
        />
        {startSec != null && (
          <div
            className="trimmer-marker marker-start"
            style={{ left: `${pct(startSec)}%` }}
            title={`시작 ${fmt(startSec)}`}
          />
        )}
        {endSec != null && (
          <div
            className="trimmer-marker marker-end"
            style={{ left: `${pct(endSec)}%` }}
            title={`끝 ${fmt(endSec)}`}
          />
        )}
      </div>

      <div className="trimmer-controls">
        <button type="button" className="btn btn-sm btn-secondary" onClick={togglePlay}>
          {isPlaying ? '⏸' : '▶'}
        </button>
        <button type="button" className="btn btn-sm btn-secondary" onClick={() => seekBy(-1)}>-1초</button>
        <button type="button" className="btn btn-sm btn-secondary" onClick={() => seekBy(-FRAME_STEP)}>-1프레임</button>
        <button type="button" className="btn btn-sm btn-secondary" onClick={() => seekBy(FRAME_STEP)}>+1프레임</button>
        <button type="button" className="btn btn-sm btn-secondary" onClick={() => seekBy(1)}>+1초</button>
      </div>

      <div className="trimmer-marks">
        <div className="trimmer-mark-row">
          <button
            type="button"
            className="btn btn-sm btn-primary"
            onClick={() => markCurrent(onChangeStart)}
          >
            현재 지점을 시작으로
          </button>
          <span className="trimmer-mark-value">
            {startSec != null ? `시작 ${fmt(startSec)}` : '시작 미지정'}
          </span>
        </div>

        <div className="trimmer-mark-row">
          <button
            type="button"
            className="btn btn-sm btn-outline"
            onClick={() => markCurrent(onChangeEnd)}
          >
            현재 지점을 끝으로 (선택)
          </button>
          <span className="trimmer-mark-value">
            {endSec != null ? `끝 ${fmt(endSec)}` : '끝 미지정'}
          </span>
          {endSec != null && (
            <button
              type="button"
              className="btn btn-sm btn-secondary"
              onClick={() => onChangeEnd(null)}
            >
              해제
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
