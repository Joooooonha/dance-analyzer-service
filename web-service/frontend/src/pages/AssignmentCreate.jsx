import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { uploadVideo, createAssignment } from '../api/client';
import VideoUploader from '../components/VideoUploader';
import './AssignmentCreate.css';

export default function AssignmentCreate() {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        title: '',
        startDate: '',
        dueDate: ''
    });
    const [referenceFile, setReferenceFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!referenceFile) {
            setError('기준 영상을 선택해주세요.');
            return;
        }

        setLoading(true);
        setError('');

        try {
            // 1. 기준 영상 먼저 업로드 (저장소로 직접)
            const upload = await uploadVideo(referenceFile, 'REFERENCE');

            // 2. 숙제 생성
            const assignmentData = {
                targetVideoId: upload.videoId,
                title: formData.title,
                startDate: new Date(formData.startDate).toISOString(),
                dueDate: new Date(formData.dueDate).toISOString()
            };

            await createAssignment(assignmentData);

            alert('숙제가 생성되었습니다!');
            navigate('/assignments');
        } catch (err) {
            setError(err.message || '숙제 생성에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };

    // 현재 시간을 datetime-local 형식으로 변환
    const now = new Date();
    const minDateTime = now.toISOString().slice(0, 16);

    return (
        <div className="assignment-create-page page">
            <div className="container">
                <Link to="/assignments" className="back-link">← 숙제 목록</Link>

                <div className="create-header">
                    <h1 className="heading-icon"><Plus size={26} /> 숙제 생성</h1>
                    <p>팀원들에게 새로운 연습 숙제를 부여하세요</p>
                </div>

                <form className="create-form card" onSubmit={handleSubmit}>
                    {error && <div className="auth-error mb-3">{error}</div>}

                    <div className="form-group">
                        <label className="form-label">숙제 제목</label>
                        <input
                            type="text"
                            name="title"
                            className="form-input"
                            placeholder="예: 1주차 기초 스텝 연습"
                            value={formData.title}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="form-row">
                        <div className="form-group">
                            <label className="form-label">시작일</label>
                            <input
                                type="datetime-local"
                                name="startDate"
                                className="form-input"
                                min={minDateTime}
                                value={formData.startDate}
                                onChange={handleChange}
                                required
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label">마감일</label>
                            <input
                                type="datetime-local"
                                name="dueDate"
                                className="form-input"
                                min={formData.startDate || minDateTime}
                                value={formData.dueDate}
                                onChange={handleChange}
                                required
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label className="form-label">기준 영상</label>
                        <p className="form-hint">팀원들이 따라 연습할 기준 안무 영상</p>
                        <VideoUploader
                            label="기준 영상 선택"
                            selectedFile={referenceFile}
                            onSelect={setReferenceFile}
                        />
                    </div>

                    <div className="form-actions">
                        <Link to="/assignments" className="btn btn-secondary">
                            취소
                        </Link>
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={loading}
                        >
                            {loading ? '생성 중...' : '숙제 생성하기'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
