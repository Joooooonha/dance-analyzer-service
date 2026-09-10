import './VideoUploader.css';
import { useState, useRef } from 'react';
import { FileVideo, Upload } from 'lucide-react';

export default function VideoUploader({
    label,
    accept = 'video/*',
    onSelect,
    selectedFile
}) {
    const [isDragging, setIsDragging] = useState(false);
    const inputRef = useRef(null);

    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('video/')) {
            onSelect(file);
        }
    };

    const handleClick = () => {
        inputRef.current?.click();
    };

    // 마우스로만 열리던 파일 선택창을 키보드로도 열 수 있게 한다 — 이 드롭존이
    // 자유 연습/숙제 제출의 첫 단계라 여기서 막히면 키보드 사용자는 아예
    // 시작을 못 한다.
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleClick();
        }
    };

    const handleChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            onSelect(file);
        }
    };

    return (
        <div
            className={`video-uploader ${isDragging ? 'dragging' : ''} ${selectedFile ? 'has-file' : ''}`}
            role="button"
            tabIndex={0}
            aria-label={selectedFile ? `${label}: ${selectedFile.name} 선택됨, 다시 선택하려면 활성화하세요` : `${label} 파일 선택`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={handleClick}
            onKeyDown={handleKeyDown}
        >
            <input
                ref={inputRef}
                type="file"
                accept={accept}
                onChange={handleChange}
                hidden
            />

            {selectedFile ? (
                <div className="file-preview">
                    <span className="file-icon"><FileVideo size={40} /></span>
                    <div className="file-info">
                        <span className="file-name">{selectedFile.name}</span>
                        <span className="file-size">
                            {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                        </span>
                    </div>
                    <button
                        className="btn btn-sm btn-secondary"
                        onClick={(e) => {
                            e.stopPropagation();
                            onSelect(null);
                        }}
                    >
                        변경
                    </button>
                </div>
            ) : (
                <div className="upload-prompt">
                    <span className="upload-icon"><Upload size={48} color="var(--accent-cyan)" /></span>
                    <p className="upload-text">
                        <strong>{label}</strong>
                        <br />
                        클릭하거나 파일을 드래그하세요
                    </p>
                </div>
            )}
        </div>
    );
}
