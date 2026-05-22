import { useState, useRef } from 'react';
import api from '../services/api';

const UploadModal = ({ onClose, onSuccess }) => {
    const [files, setFiles] = useState([]);
    const [category, setCategory] = useState('newspaper');
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 });
    const [fileProgress, setFileProgress] = useState(0);
    const [error, setError] = useState('');
    const [dragActive, setDragActive] = useState(false);
    const fileInputRef = useRef(null);

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        const droppedFiles = Array.from(e.dataTransfer.files).filter(f => 
            f.type === 'application/pdf' || 
            f.name.toLowerCase().endsWith('.cbz') || 
            f.name.toLowerCase().endsWith('.cbr')
        );
        if (droppedFiles.length > 0) {
            setFiles(prev => [...prev, ...droppedFiles]);
            setError('');
        } else {
            setError('Please drop valid PDF, CBZ, or CBR files');
        }
    };

    const handleFileSelect = (e) => {
        const selectedFiles = Array.from(e.target.files).filter(f => 
            f.type === 'application/pdf' || 
            f.name.toLowerCase().endsWith('.cbz') || 
            f.name.toLowerCase().endsWith('.cbr')
        );
        if (selectedFiles.length > 0) {
            setFiles(prev => [...prev, ...selectedFiles]);
            setError('');
        }
    };

    const removeFile = (indexToRemove) => {
        setFiles(files.filter((_, index) => index !== indexToRemove));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (files.length === 0) {
            setError('Please select at least one file');
            return;
        }

        setError('');
        setUploading(true);
        setUploadProgress({ current: 0, total: files.length });

        try {
            for (let i = 0; i < files.length; i++) {
                setUploadProgress(prev => ({ ...prev, current: i + 1 }));
                setFileProgress(0);

                const formData = new FormData();
                formData.append('file', files[i]);
                // We omit title so the backend extracts it
                formData.append('category', category);

                await api.post('/publications/', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                    onUploadProgress: (progressEvent) => {
                        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                        setFileProgress(percentCompleted);
                    }
                });
            }

            onSuccess();
        } catch (err) {
            setError(err.response?.data?.detail || 'Upload failed. Please try again.');
        } finally {
            setUploading(false);
        }
    };

    const formatFileSize = (bytes) => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2 className="modal-title">Upload Publication</h2>
                    <button className="modal-close" onClick={onClose}>
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M18 6L6 18M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="modal-body">
                        {error && <div className="login-error">{error}</div>}

                        {/* Dropzone */}
                        <div
                            className={`dropzone ${dragActive ? 'active' : ''}`}
                            onDragEnter={handleDrag}
                            onDragLeave={handleDrag}
                            onDragOver={handleDrag}
                            onDrop={handleDrop}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".pdf,application/pdf,.cbz,.cbr"
                                multiple
                                onChange={handleFileSelect}
                                style={{ display: 'none' }}
                            />

                            {files.length === 0 ? (
                                <>
                                    <div className="dropzone-icon">📄</div>
                                    <p className="dropzone-text">
                                        Drag and drop PDF, CBZ, or CBR files here
                                    </p>
                                    <p className="dropzone-hint">
                                        or click to browse
                                    </p>
                                </>
                            ) : (
                                <div className="dropzone-file-list" onClick={e => e.stopPropagation()}>
                                    {files.map((file, idx) => (
                                        <div key={idx} className="dropzone-file">
                                            <span className="dropzone-file-icon">📰</span>
                                            <span className="dropzone-file-name">{file.name}</span>
                                            <span style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
                                                {formatFileSize(file.size)}
                                            </span>
                                            {!uploading && (
                                                <button
                                                    type="button"
                                                    className="dropzone-file-remove"
                                                    onClick={() => removeFile(idx)}
                                                >
                                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                        <path d="M18 6L6 18M6 6l12 12" />
                                                    </svg>
                                                </button>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Category Select */}
                        <div className="input-group" style={{ marginTop: '1rem' }}>
                            <label htmlFor="category">Default Category (Auto-overridden for comics)</label>
                            <select
                                id="category"
                                className="input"
                                value={category}
                                onChange={(e) => setCategory(e.target.value)}
                            >
                                <option value="newspaper">Newspaper</option>
                                <option value="magazine">Magazine</option>
                                <option value="book">Book</option>
                                <option value="other">Other</option>
                            </select>
                        </div>
                    </div>

                    <div className="modal-footer">
                        <button type="button" className="btn btn-secondary" onClick={onClose}>
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={uploading || files.length === 0}
                            style={{ position: 'relative', overflow: 'hidden' }}
                        >
                            {uploading && (
                                <div style={{ 
                                    position: 'absolute', left: 0, top: 0, bottom: 0, 
                                    width: `${fileProgress}%`, 
                                    backgroundColor: 'rgba(255,255,255,0.2)',
                                    transition: 'width 0.2s ease' 
                                }} />
                            )}
                            <span style={{ position: 'relative', zIndex: 1 }}>
                                {uploading 
                                    ? fileProgress === 100 
                                        ? `Processing (${uploadProgress.current}/${uploadProgress.total})...`
                                        : `Uploading (${uploadProgress.current}/${uploadProgress.total}) - ${fileProgress}%` 
                                    : `Upload ${files.length > 0 ? files.length + ' Files' : ''}`}
                            </span>
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default UploadModal;
