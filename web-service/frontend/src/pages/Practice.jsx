import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import VideoUploader from '../components/VideoUploader';
import { uploadVideo, analyzeLog } from '../api/client';
import './Practice.css';

export default function Practice() {
    const navigate = useNavigate();
    const [referenceFile, setReferenceFile] = useState(null);
    const [practiceFile, setPracticeFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [error, setError] = useState('');
    const [step, setStep] = useState(1); // 1: 업로드, 2: 분석 중, 3: 완료

    const handleSubmit = async () => {
        if (!referenceFile || !practiceFile) {
            setError('두 영상을 모두 선택해주세요.');
            return;
        }

        setError('');
        setUploading(true);
        setStep(2);

        try {
            // 1. Reference 영상 업로드
            const refFormData = new FormData();
            refFormData.append('title', 'Reference Video');
            refFormData.append('type', 'REFERENCE');
            refFormData.append('file', referenceFile);

            const refVideoId = await uploadVideo(refFormData);

            // 2. Practice 영상 업로드 (referenceVideoId 포함!)
            const practiceFormData = new FormData();
            practiceFormData.append('title', 'Practice Video');
            practiceFormData.append('type', 'PRACTICE');
            practiceFormData.append('file', practiceFile);
            practiceFormData.append('referenceVideoId', refVideoId); // [NEW] 기준 영상 연결

            const practiceVideoId = await uploadVideo(practiceFormData);

            setUploading(false);
            setAnalyzing(true);

            // 3. 분석 요청 
            // 영상 업로드 시 자동으로 PracticeLog가 생성됨
            // practiceVideoId가 아닌 logId가 필요함 (현재는 같은 값으로 처리)
            const analysisResult = await analyzeLog(practiceVideoId);

            setStep(3);

            // 분석 결과 페이지로 이동
            navigate(`/logs/${practiceVideoId}`);

        } catch (err) {
            setError(err.message || '업로드에 실패했습니다.');
            setStep(1);
        } finally {
            setUploading(false);
            setAnalyzing(false);
        }
    };

    return (
        <div className="practice-page page">
            <div className="container">
                <div className="page-header">
                    <h1>🎯 자유 연습</h1>
                    <p>
                        기준 영상과 연습 영상을 업로드하면
                        <br />
                        AI가 동작을 분석하여 점수와 피드백을 제공합니다
                    </p>
                </div>

                {step === 1 && (
                    <>
                        {error && <div className="auth-error mb-3">{error}</div>}

                        <div className="upload-grid">
                            <div className="upload-section">
                                <h3>📹 기준 영상 (Reference)</h3>
                                <p className="upload-hint">따라 할 원본 안무 영상</p>
                                <VideoUploader
                                    label="기준 영상 선택"
                                    selectedFile={referenceFile}
                                    onSelect={setReferenceFile}
                                />
                            </div>

                            <div className="upload-section">
                                <h3>🎬 연습 영상 (Practice)</h3>
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
                                onClick={handleSubmit}
                                disabled={!referenceFile || !practiceFile}
                            >
                                분석 시작하기 🚀
                            </button>
                        </div>
                    </>
                )}

                {step === 2 && (
                    <div className="analyzing-state">
                        <div className="analyzing-animation">
                            {uploading ? (
                                <>
                                    <span className="analyzing-icon pulse">📤</span>
                                    <h2>영상 업로드 중...</h2>
                                    <p>잠시만 기다려주세요</p>
                                </>
                            ) : (
                                <>
                                    <span className="analyzing-icon pulse">🤖</span>
                                    <h2>AI 분석 중...</h2>
                                    <p>동작을 비교하고 있습니다</p>
                                </>
                            )}
                            <div className="spinner mt-3"></div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
