import { useState, useRef } from 'react';
import api from '../services/api';

const UploadModal = ({ onClose, onSuccess }) => {
    const [file, setFile] = useState(null);
    const [title, setTitle] = useState('');
    const [category, setCategory] = useState('newspaper');
    const [uploading, setUploading] = useState(false);
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

        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile && droppedFile.type === 'application/pdf') {
            setFile(droppedFile);
            if (!title) {
                setTitle(droppedFile.name.replace('.pdf', ''));
            }
        } else {
            setError('Please drop a PDF file');
        }
    };

    const handleFileSelect = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setFile(selectedFile);
            if (!title) {
                setTitle(selectedFile.name.replace('.pdf', ''));
            }
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!file || !title.trim()) {
            setError('Please select a file and enter a title');
            return;
        }

        setError('');
        setUploading(true);

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('title', title.trim());
            formData.append('category', category);

            await api.post('/publications/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

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
                                accept=".pdf,application/pdf"
                                onChange={handleFileSelect}
                                style={{ display: 'none' }}
                            />

                            {!file ? (
                                <>
                                    <div className="dropzone-icon">📄</div>
                                    <p className="dropzone-text">
                                        Drag and drop your PDF here
                                    </p>
                                    <p className="dropzone-hint">
                                        or click to browse
                                    </p>
                                </>
                            ) : (
                                <div className="dropzone-file" onClick={e => e.stopPropagation()}>
                                    <span className="dropzone-file-icon">📰</span>
                                    <span className="dropzone-file-name">{file.name}</span>
                                    <span style={{ color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
                                        {formatFileSize(file.size)}
                                    </span>
                                    <button
                                        type="button"
                                        className="dropzone-file-remove"
                                        onClick={() => setFile(null)}
                                    >
                                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                            <path d="M18 6L6 18M6 6l12 12" />
                                        </svg>
                                    </button>
                                </div>
                            )}
                        </div>

                        {/* Title Input */}
                        <div className="input-group" style={{ marginTop: '1rem' }}>
                            <label htmlFor="title">Title</label>
                            <input
                                id="title"
                                type="text"
                                className="input"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                placeholder="Publication title"
                                required
                            />
                        </div>

                        {/* Category Select */}
                        <div className="input-group">
                            <label htmlFor="category">Category</label>
                            <select
                                id="category"
                                className="input"
                                value={category}
                                onChange={(e) => setCategory(e.target.value)}
                            >
                                <option value="newspaper">Newspaper</option>
                                <option value="magazine">Magazine</option>
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
                            disabled={uploading || !file}
                        >
                            {uploading ? 'Uploading...' : 'Upload'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default UploadModal;
