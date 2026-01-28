import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '../services/api';
import Header from '../components/Header';

const Favorites = () => {
    useTranslation(); // i18n context available for future use
    const navigate = useNavigate();

    const [publications, setPublications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [activeCategory, setActiveCategory] = useState(null); // null = all

    const fetchPublications = async () => {
        try {
            setLoading(true);
            const params = activeCategory ? { category: activeCategory } : {};
            const response = await api.get('/publications/favorites/titles', { params });
            setPublications(response.data);
        } catch (error) {
            console.error('Failed to fetch publications:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPublications();
    }, [activeCategory]);

    const toggleFavorite = async (title, isFavorite) => {
        try {
            if (isFavorite) {
                await api.delete(`/publications/favorites/${encodeURIComponent(title)}`);
            } else {
                await api.post(`/publications/favorites/${encodeURIComponent(title)}`);
            }
            // Optimistic update
            setPublications(prev => prev.map(pub =>
                pub.title === title ? { ...pub, is_favorite: !isFavorite } : pub
            ));
        } catch (error) {
            console.error('Failed to toggle favorite:', error);
        }
    };

    const filteredPublications = searchQuery
        ? publications.filter(pub => pub.title.toLowerCase().includes(searchQuery.toLowerCase()))
        : publications;

    const categories = [
        { id: null, label: 'All' },
        { id: 'newspaper', label: 'Newspapers' },
        { id: 'magazine', label: 'Magazines' },
    ];

    return (
        <>
            <Header searchQuery={searchQuery} onSearchChange={setSearchQuery} />

            <main className="dashboard">
                <div className="container">
                    <section className="section">
                        <div className="section-header" style={{ marginBottom: '1.5rem' }}>
                            <h2 className="section-title">⭐ Manage Favorites</h2>
                            <button className="btn btn-secondary" onClick={() => navigate('/')}>
                                ← Back to Dashboard
                            </button>
                        </div>

                        <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1.5rem' }}>
                            Select your favorite publications. Favorites from today will appear first on your dashboard.
                        </p>

                        <div className="category-tabs">
                            {categories.map(cat => (
                                <button
                                    key={cat.id || 'all'}
                                    className={`category-tab ${activeCategory === cat.id ? 'active' : ''}`}
                                    onClick={() => setActiveCategory(cat.id)}
                                >
                                    {cat.label}
                                </button>
                            ))}
                        </div>

                        {loading ? (
                            <div className="loading-container">
                                <div className="loading-spinner"></div>
                                <p>Loading publications...</p>
                            </div>
                        ) : (
                            <div className="publication-grid">
                                {filteredPublications.map(pub => (
                                    <FavoriteCard
                                        key={pub.title}
                                        publication={pub}
                                        onToggle={() => toggleFavorite(pub.title, pub.is_favorite)}
                                    />
                                ))}
                            </div>
                        )}

                        {!loading && filteredPublications.length === 0 && (
                            <div className="loading-container">
                                <p>{searchQuery ? 'No matching publications found.' : 'No publications available.'}</p>
                            </div>
                        )}
                    </section>
                </div>
            </main>
        </>
    );
};

const FavoriteCard = ({ publication, onToggle }) => {
    const [imageSrc, setImageSrc] = useState(null);
    const [imageError, setImageError] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let isMounted = true;

        const fetchThumbnail = async () => {
            try {
                await new Promise(resolve => setTimeout(resolve, Math.random() * 300));
                if (!isMounted) return;

                const response = await api.get(`/publications/${publication.thumbnail_id}/thumbnail`, {
                    responseType: 'blob',
                    timeout: 10000
                });

                if (isMounted && response.data.size > 0) {
                    const url = URL.createObjectURL(response.data);
                    setImageSrc(url);
                } else {
                    setImageError(true);
                }
                setLoading(false);
            } catch {
                if (isMounted) {
                    setImageError(true);
                    setLoading(false);
                }
            }
        };

        if (publication.thumbnail_id) {
            fetchThumbnail();
        }

        return () => {
            isMounted = false;
            if (imageSrc) URL.revokeObjectURL(imageSrc);
        };
    }, [publication.thumbnail_id]);

    return (
        <div className="publication-card" onClick={onToggle} style={{ cursor: 'pointer' }}>
            <div className="publication-cover">
                {!imageError && imageSrc ? (
                    <img src={imageSrc} alt={publication.title} loading="lazy" style={{ opacity: loading ? 0 : 1 }} />
                ) : (
                    <div className="publication-cover-placeholder">
                        {loading ? <div className="loading-spinner" style={{ width: '30px', height: '30px' }}></div> : '📰'}
                    </div>
                )}

                {/* Star Overlay */}
                <div style={{
                    position: 'absolute', inset: 0,
                    background: publication.is_favorite ? 'rgba(251, 191, 36, 0.3)' : 'rgba(0, 0, 0, 0.4)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    transition: 'all 0.2s ease'
                }}>
                    <span style={{
                        fontSize: '2.5rem',
                        filter: publication.is_favorite ? 'drop-shadow(0 0 10px gold)' : 'none',
                        transition: 'all 0.2s ease'
                    }}>
                        {publication.is_favorite ? '⭐' : '☆'}
                    </span>
                </div>
            </div>

            <div className="publication-info">
                <h3 className="publication-title" title={publication.title}>
                    {publication.title}
                </h3>
            </div>
        </div>
    );
};

export default Favorites;
