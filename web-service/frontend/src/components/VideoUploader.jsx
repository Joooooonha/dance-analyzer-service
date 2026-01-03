import './VideoUploader.css';
import { useState, useRef } from 'react';

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

    const handleChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            onSelect(file);
        }
    };

    return (
        <div
            className={`video-uploader ${isDragging ? 'dragging' : ''} ${selectedFile ? 'has-file' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={handleClick}
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
                    <span className="file-icon">🎬</span>
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
                    <span className="upload-icon">📹</span>
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
