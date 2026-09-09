import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Cpu, Film, Target, Timer, UploadCloud, Video } from 'lucide-react';
import VideoUploader from '../components/VideoUploader';
import VideoTrimmer from '../components/VideoTrimmer';
import { uploadVideo, updateTrim, analyzeLog, getVideoUrl } from '../api/client';
import './Practice.css';

// 'select'    영상 두 개 선택
// 'uploading' 업로드 중
// 'trim'      안무 구간 지정
// 'starting'  분석 시작 요청 중 (202 받으면 바로 결과 페이지로 이동)
const STEP = { SELECT: 'select', UPLOADING: 'uploading', TRIM: 'trim', STARTING: 'starting' };

export default function Practice() {
    const navigate = useNavigate();
    const [referenceFile, setReferenceFile] = useState(null);
    const [practiceFile, setPracticeFile] = useState(null);
    const [step, setStep] = useState(STEP.SELECT);
    const [error, setError] = useState('');
    // 저장소로 직접 올리므로 수십 MB가 브라우저에서 나간다. 진행률이 없으면
    // 멈춘 것처럼 보인다.
    const [progress, setProgress] = useState(0);

    // 업로드 결과 (구간 지정 단계에서 사용)
    const [referenceVideoId, setReferenceVideoId] = useState(null);
    const [practiceVideoId, setPracticeVideoId] = useState(null);
    const [logId, setLogId] = useState(null);

    // 구간 지정 값 (초). 끝 시각은 선택이라 기본 null.
    const [refStart, setRefStart] = useState(null);
    const [refEnd, setRefEnd] = useState(null);
    const [pracStart, setPracStart] = useState(null);
    const [pracEnd, setPracEnd] = useState(null);

    const handleUpload = async () => {
        if (!referenceFile || !practiceFile) {
            setError('두 영상을 모두 선택해주세요.');
            return;
        }

        setError('');
        setProgress(0);
        setStep(STEP.UPLOADING);

        try {
            // 파일은 저장소로 직접 올라가고 백엔드를 거치지 않는다.
            // 기준 영상 업로드에는 연습 기록이 생기지 않는다(logId가 null).
            const refUpload = await uploadVideo(
                referenceFile, 'REFERENCE', {},
                (r) => setProgress(r * 0.5));

            const practiceUpload = await uploadVideo(
                practiceFile, 'PRACTICE', { referenceVideoId: refUpload.videoId },
                (r) => setProgress(0.5 + r * 0.5));

            if (!practiceUpload.logId) {
                throw new Error('연습 기록이 만들어지지 않았습니다. 다시 시도해주세요.');
            }

            setReferenceVideoId(refUpload.videoId);
            setPracticeVideoId(practiceUpload.videoId);
            // 서버가 내려준 logId를 그대로 쓴다. 예전에는 videoId를 logId로
            // 유추했는데, 두 값이 나란히 늘어난다는 보장이 없어 위험했다.
            setLogId(practiceUpload.logId);
            setStep(STEP.TRIM);
        } catch (err) {
            setError(err.message || '업로드에 실패했습니다.');
            setStep(STEP.SELECT);
        }
    };

    const handleStartAnalysis = async () => {
        setError('');
        setStep(STEP.STARTING);

        try {
            // 지정하지 않은 값은 null로 그대로 두면 client.js의 updateTrim이
            // 필드 자체를 요청에서 뺀다.
            await updateTrim(logId, {
                referenceStartSec: refStart,
                referenceEndSec: refEnd,
                practiceStartSec: pracStart,
                practiceEndSec: pracEnd,
            });

            // 202를 받으면 바로 이동한다 — 분석 완료까지 기다리지 않는다.
            // 실제 진행 상황은 결과 페이지에서 폴링한다.
            await analyzeLog(logId);

            navigate(`/logs/${logId}`);
        } catch (err) {
            setError(err.message || '분석 시작에 실패했습니다.');
            setStep(STEP.TRIM);
        }
    };

    const bothStartsSet = refStart != null && pracStart != null;

    return (
        <div className="practice-page page">
            <div className="container">
                <div className="page-header">
                    <h1 className="heading-icon"><Target size={26} /> 자유 연습</h1>
                    <p>
                        기준 영상과 연습 영상을 업로드하고, 안무가 시작하는 지점을
                        <br />
                        맞춰주면 AI가 동작을 비교해 틀린 구간을 짚어드립니다
                    </p>
                </div>

                {error && <div className="auth-error mb-3">{error}</div>}

                {step === STEP.SELECT && (
                    <>
                        <div className="upload-grid">
                            <div className="upload-section">
                                <h3 className="heading-icon"><Video size={20} /> 기준 영상 (Reference)</h3>
                                <p className="upload-hint">따라 할 원본 안무 영상</p>
                                <VideoUploader
                                    label="기준 영상 선택"
                                    selectedFile={referenceFile}
                                    onSelect={setReferenceFile}
                                />
                            </div>

                            <div className="upload-section">
                                <h3 className="heading-icon"><Film size={20} /> 연습 영상 (Practice)</h3>
                                <p className="upload-hint">기준 영상을 보고 따라 춘 영상</p>
                                <VideoUploader
                                    label="연습 영상 선택"
                                    selectedFile={practiceFile}
                                    onSelect={setPracticeFile}
                                />
                            </div>
                        </div>

                        <div className="submit-section">
                            <button
                                className="btn btn-primary btn-lg"
                                onClick={handleUpload}
                                disabled={!referenceFile || !practiceFile}
                            >
                                업로드하고 구간 지정하기 →
                            </button>
                        </div>
                    </>
                )}

                {step === STEP.UPLOADING && (
                    <div className="analyzing-state">
                        <div className="analyzing-animation">
                            <span className="analyzing-icon pulse"><UploadCloud size={64} /></span>
                            <h2>영상 업로드 중...</h2>
                            <p>{Math.round(progress * 100)}%</p>
                            <div className="upload-progress">
                                <div
                                    className="upload-progress-bar"
                                    style={{ width: `${Math.round(progress * 100)}%` }}
                                />
                            </div>
                        </div>
                    </div>
                )}

                {step === STEP.TRIM && (
                    <>
                        <div className="trim-intro card mb-3">
                            <h3 className="heading-icon"><Timer size={20} /> 안무 시작 지점을 맞춰주세요</h3>
                            <p className="hint-text">
                                두 영상에서 안무가 실제로 시작하는 순간을 같이 표시하면 정렬
                                정확도가 크게 올라갑니다. 끝 지점은 앞뒤 여백이 많을 때만
                                지정하면 됩니다 — 없어도 분석됩니다.
                            </p>
                            {!bothStartsSet && (
                                <p className="trim-warning icon-row">
                                    <AlertTriangle size={16} />
                                    시작 지점을 지정하지 않고 분석하면 두 영상의 녹화 시작
                                    시점 차이가 그대로 남아 정확도가 떨어집니다.
                                </p>
                            )}
                        </div>

                        <div className="upload-grid">
                            <VideoTrimmer
                                label="기준 영상"
                                videoSrc={getVideoUrl(referenceVideoId)}
                                startSec={refStart}
                                endSec={refEnd}
                                onChangeStart={setRefStart}
                                onChangeEnd={setRefEnd}
                            />
                            <VideoTrimmer
                                label="연습 영상"
                                videoSrc={getVideoUrl(practiceVideoId)}
                                startSec={pracStart}
                                endSec={pracEnd}
                                onChangeStart={setPracStart}
                                onChangeEnd={setPracEnd}
                            />
                        </div>

                        <div className="submit-section">
                            <button
                                className="btn btn-primary btn-lg"
                                onClick={handleStartAnalysis}
                            >
                                {bothStartsSet ? '분석 시작하기' : '구간 없이 분석 시작하기'}
                            </button>
                        </div>
                    </>
                )}

                {step === STEP.STARTING && (
                    <div className="analyzing-state">
                        <div className="analyzing-animation">
                            <span className="analyzing-icon pulse"><Cpu size={64} /></span>
                            <h2>분석을 시작하는 중...</h2>
                            <p>곧 결과 페이지로 이동합니다</p>
                            <div className="spinner mt-3"></div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
