import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Document, Page, pdfjs } from 'react-pdf';
import api from '../services/api';

// Configure PDF.js worker to use a version-matched CDN
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const Reader = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const { t } = useTranslation();
    const containerRef = useRef(null);

    const [publication, setPublication] = useState(null);
    const [pdfUrl, setPdfUrl] = useState(null);
    const [numPages, setNumPages] = useState(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [error, setError] = useState(null);
    const [scale, setScale] = useState(1);
    const [pageWidth, setPageWidth] = useState(null);
    const [loading, setLoading] = useState(true);
    const [turning, setTurning] = useState(null); // 'left' or 'right'
    const [originalPageDims, setOriginalPageDims] = useState(null); // { width, height }
    const [showControls, setShowControls] = useState(true);
    const controlsTimeoutRef = useRef(null);

    // Auto-hide controls
    const resetControlsTimeout = useCallback(() => {
        setShowControls(true);
        if (controlsTimeoutRef.current) clearTimeout(controlsTimeoutRef.current);
        controlsTimeoutRef.current = setTimeout(() => {
            setShowControls(false);
        }, 3000);
    }, []);

    useEffect(() => {
        resetControlsTimeout();
        return () => {
            if (controlsTimeoutRef.current) clearTimeout(controlsTimeoutRef.current);
        };
    }, [resetControlsTimeout]);

    const handleInteraction = () => {
        resetControlsTimeout();
    };

    // Fetch publication details
    useEffect(() => {
        const fetchPublication = async () => {
            try {
                const response = await api.get(`/publications/${id}`);
                setPublication(response.data);
                setCurrentPage(response.data.current_page || 1);

                // Set PDF URL (auth token is added in file memo)
                setPdfUrl(`${api.defaults.baseURL}/publications/${id}/pdf`);
            } catch (error) {
                console.error('Failed to fetch publication:', error);
                navigate('/');
            }
        };

        fetchPublication();
    }, [id, navigate]);

    // Container dimensions state
    const [containerSize, setContainerSize] = useState({ width: window.innerWidth, height: window.innerHeight });

    // Update container dimensions on resize
    useEffect(() => {
        const updateDimensions = () => {
            if (containerRef.current) {
                setContainerSize({
                    width: containerRef.current.clientWidth,
                    height: containerRef.current.clientHeight
                });
            }
        };

        updateDimensions();
        window.addEventListener('resize', updateDimensions);
        return () => window.removeEventListener('resize', updateDimensions);
    }, []);

    // Handle page load to fit to screen
    const onPageLoadSuccess = ({ originalWidth, originalHeight }) => {
        setOriginalPageDims({ width: originalWidth, height: originalHeight });
        setLoading(false);
    };

    // Recalculate page width when container or page dims change
    useEffect(() => {
        if (containerSize.width && containerSize.height && originalPageDims) {
            const { width: containerWidth, height: containerHeight } = containerSize;
            const { width: originalWidth, height: originalHeight } = originalPageDims;

            // Calculate scale to fit container (contain)
            const scaleWidth = containerWidth / originalWidth;
            const scaleHeight = containerHeight / originalHeight;

            // Use the smaller scale to ensure it fits entirely
            const scaleToFit = Math.min(scaleWidth, scaleHeight);

            // Update page width
            setPageWidth((originalWidth * scaleToFit) - 4);
        }
    }, [containerSize, originalPageDims]);

    // Save reading progress
    const saveProgress = useCallback(async (page) => {
        try {
            await api.put(`/publications/${id}/progress`, { current_page: page });
        } catch (error) {
            console.error('Failed to save progress:', error);
        }
    }, [id]);

    // Page navigation
    const goToPage = useCallback((page, direction = null) => {
        if (page >= 1 && page <= numPages) {
            if (direction) {
                setTurning(direction);
                setTimeout(() => setTurning(null), 500);
            }
            setCurrentPage(page);
            saveProgress(page);
        }
    }, [numPages, saveProgress]);

    const goToPrevPage = useCallback(() => {
        goToPage(currentPage - 1, 'right');
    }, [currentPage, goToPage]);

    const goToNextPage = useCallback(() => {
        goToPage(currentPage + 1, 'left');
    }, [currentPage, goToPage]);

    // Keyboard navigation
    useEffect(() => {
        const handleKeyDown = (e) => {
            switch (e.key) {
                case 'ArrowLeft':
                    goToPrevPage();
                    break;
                case 'ArrowRight':
                case ' ':
                    e.preventDefault();
                    goToNextPage();
                    break;
                case 'Escape':
                    navigate('/');
                    break;
                default:
                    break;
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [goToPrevPage, goToNextPage, navigate]);

    // Zoom controls
    const zoomIn = () => setScale(prev => Math.min(prev + 0.25, 3));
    const zoomOut = () => setScale(prev => Math.max(prev - 0.25, 0.5));
    const resetZoom = () => setScale(1);

    const toggleFavorite = async () => {
        if (!publication) return;
        const isFavorite = publication.is_favorite;
        try {
            if (isFavorite) {
                await api.delete(`/publications/favorites/${encodeURIComponent(publication.title)}`);
            } else {
                await api.post(`/publications/favorites/${encodeURIComponent(publication.title)}`);
            }
            // Update local state
            setPublication(prev => ({ ...prev, is_favorite: !isFavorite }));
        } catch (error) {
            console.error('Failed to toggle favorite:', error);
        }
    };

    const onDocumentLoadSuccess = ({ numPages }) => {
        setNumPages(numPages);
        setLoading(false);
        setError(null);
    };

    const onDocumentLoadError = (err) => {
        console.error('PDF Load Error:', err);
        setError(err.message || 'Failed to load PDF');
        setLoading(false);
    };

    const handlePageInputChange = (e) => {
        const value = parseInt(e.target.value, 10);
        if (!isNaN(value)) {
            goToPage(value);
        }
    };

    const file = useMemo(() => ({
        url: pdfUrl,
        httpHeaders: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
        }
    }), [pdfUrl]);

    if (!publication || !pdfUrl) {
        return (
            <div className="reader">
                <div className="loading-container" style={{ flex: 1 }}>
                    <div className="loading-spinner"></div>
                    <p>Loading publication...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="reader" onMouseMove={handleInteraction} onClick={handleInteraction} onTouchStart={handleInteraction}>
            {/* Header */}
            <header className={`reader-header ${!showControls ? 'hidden' : ''}`}>
                <div className="reader-header-left">
                    <button className="reader-back-btn desktop-only" onClick={() => navigate('/')}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M19 12H5M12 19l-7-7 7-7" />
                        </svg>
                        <span>{t('common.back')}</span>
                    </button>
                    <h1 className="reader-title">{publication.title}</h1>
                </div>

                <div className="reader-header-right">
                    <button
                        className={`reader-favorite-btn ${publication?.is_favorite ? 'is-favorite' : ''}`}
                        onClick={toggleFavorite}
                        title={publication?.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
                    >
                        {publication?.is_favorite ? '⭐' : '☆'}
                    </button>
                </div>

            </header>
            {/* Main Reading Area */}
            <main className="reader-main" ref={containerRef}>
                {/* Click Zones */}
                <div
                    className="reader-click-zone left"
                    onClick={goToPrevPage}
                    style={{ cursor: currentPage > 1 ? 'pointer' : 'default' }}
                />
                <div
                    className="reader-click-zone right"
                    onClick={goToNextPage}
                    style={{ cursor: currentPage < numPages ? 'pointer' : 'default' }}
                />

                {/* Navigation Buttons */}
                <button
                    className="reader-nav-btn prev"
                    onClick={goToPrevPage}
                    disabled={currentPage <= 1}
                >
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M15 18l-6-6 6-6" />
                    </svg>
                </button>
                <button
                    className="reader-nav-btn next"
                    onClick={goToNextPage}
                    disabled={currentPage >= numPages}
                >
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M9 18l6-6-6-6" />
                    </svg>
                </button>

                {/* PDF Page */}
                <div className="reader-page-container">
                    <div className="reader-page-wrapper">
                        <div className={`reader-page-inner ${turning ? `turning-${turning}` : ''}`}>
                            {loading && (
                                <div className="loading-container" style={{ position: 'absolute', inset: 0 }}>
                                    <div className="loading-spinner"></div>
                                </div>
                            )}
                            <Document
                                file={file}
                                onLoadSuccess={onDocumentLoadSuccess}
                                onLoadError={onDocumentLoadError}
                                loading=""
                            >
                                {error ? (
                                    <div className="error-message" style={{ padding: '2rem', textAlign: 'center' }}>
                                        <p style={{ color: 'var(--color-error)', marginBottom: '1rem' }}>{error}</p>
                                        <button className="btn btn-secondary" onClick={() => window.location.reload()}>Retry</button>
                                    </div>
                                ) : (
                                    <Page
                                        pageNumber={currentPage}
                                        width={pageWidth ? pageWidth * scale : undefined}
                                        className="reader-page"
                                        renderTextLayer={false}
                                        renderAnnotationLayer={false}
                                        onLoadSuccess={onPageLoadSuccess}
                                    />
                                )}
                            </Document>
                        </div>
                    </div>
                </div>
            </main>

            {/* Mobile Navigation bar */}
            <div className={`mobile-only reader-mobile-nav ${!showControls ? 'hidden' : ''}`}>
                <button className="btn btn-secondary" onClick={goToPrevPage} disabled={currentPage <= 1}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M15 18l-6-6 6-6" />
                    </svg>
                </button>
                <div className="reader-page-info">
                    <span>{currentPage} / {numPages}</span>
                </div>
                <button className="btn btn-secondary" onClick={goToNextPage} disabled={currentPage >= numPages}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M9 18l6-6-6-6" />
                    </svg>
                </button>
            </div>
        </div>
    );
};

export default Reader;
