import { useState, useEffect } from 'react';
import api from '../services/api';

const PublicationCard = ({ publication, onClick, showProgress = false, onRemove }) => {
    const [imageSrc, setImageSrc] = useState(null);
    const [imageError, setImageError] = useState(false);
    const [loading, setLoading] = useState(true);

    const pubId = publication.external_id || publication.id;

    useEffect(() => {
        let isMounted = true;

        const fetchThumbnail = async () => {
            try {
                // Add a small delay to prevent flooding the server
                await new Promise(resolve => setTimeout(resolve, Math.random() * 500));

                if (!isMounted) return;

                const response = await api.get(`/publications/${pubId}/thumbnail`, {
                    responseType: 'blob',
                    timeout: 10000
                });

                if (isMounted) {
                    if (response.data.size > 0) {
                        const url = URL.createObjectURL(response.data);
                        setImageSrc(url);
                    } else {
                        setImageError(true);
                    }
                    setLoading(false);
                }
            } catch (error) {
                if (isMounted) {
                    if (error.code !== 'ECONNABORTED') {
                        console.error(`Failed to load thumbnail for ${pubId}`, error);
                    }
                    setImageError(true);
                    setLoading(false);
                }
            }
        };

        if (pubId) {
            fetchThumbnail();
        }

        return () => {
            isMounted = false;
            if (imageSrc) {
                URL.revokeObjectURL(imageSrc);
            }
        };
    }, [pubId]);

    const progress = publication.page_count > 0
        ? ((publication.current_page || 1) / publication.page_count) * 100
        : 0;

    const handleRemoveClick = (e) => {
        e.stopPropagation(); // Prevent opening the reader
        if (onRemove) {
            onRemove(pubId);
        }
    };

    return (
        <div className={`publication-card ${publication.is_favorite ? 'is-favorite' : ''}`} onClick={onClick}>
            <div className="publication-cover">
                {!imageError && imageSrc ? (
                    <img
                        src={imageSrc}
                        alt={publication.title}
                        onError={() => setImageError(true)}
                        loading="lazy"
                        style={{
                            opacity: loading ? 0 : 1,
                        }}
                    />
                ) : (
                    <div className="publication-cover-placeholder">
                        {loading ? (
                            <div className="loading-spinner" style={{ width: '30px', height: '30px' }}></div>
                        ) : (
                            '📰'
                        )}
                    </div>
                )}

                <div className="publication-overlay">
                    <div className="publication-play-btn">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="white">
                            <path d="M8 5v14l11-7z" />
                        </svg>
                    </div>
                </div>

                {publication.is_favorite && (
                    <div className="publication-favorite-badge" title="Favorite">
                        ⭐
                    </div>
                )}

                {onRemove && (
                    <button
                        className="publication-remove-btn"
                        onClick={handleRemoveClick}
                        title="Remove from history"
                    >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2M10 11v6M14 11v6" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                    </button>
                )}
            </div>

            <div className="publication-info">
                <h3 className="publication-title" title={publication.title}>
                    {publication.title}
                </h3>
                <div className="publication-meta">
                    {publication.publication_date && (
                        <span>
                            {new Date(publication.publication_date).toLocaleDateString(undefined, {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric'
                            })}
                        </span>
                    )}
                    <span className="desktop-only">
                        {publication.page_count > 0 && (
                            <>
                                {publication.publication_date && <span>•</span>}
                                <span>{publication.page_count} pages</span>
                            </>
                        )}
                    </span>
                </div>

                {showProgress && progress > 0 && (
                    <div className="publication-progress">
                        <div
                            className="publication-progress-bar"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                )}
            </div>
        </div>
    );
};


export default PublicationCard;
