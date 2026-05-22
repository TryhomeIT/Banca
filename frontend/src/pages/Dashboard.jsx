import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import api from '../services/api';
import Header from '../components/Header';
import PublicationCard from '../components/PublicationCard';

const Dashboard = () => {
    useAuth(); // Ensure auth context is available
    const { t } = useTranslation();
    const navigate = useNavigate();

    const [searchQuery, setSearchQuery] = useState('');
    const [activeCategory, setActiveCategory] = useState('newspaper'); // Default to newspaper
    const [recentlyRead, setRecentlyRead] = useState([]);
    const [publications, setPublications] = useState([]);
    const [loading, setLoading] = useState(true);

    // Fetch local publications
    const fetchPublications = async () => {
        try {
            setLoading(true);
            const params = { limit: 500 }; // Request up to 500 items
            if (searchQuery) {
                params.search = searchQuery;
            } else {
                params.category = activeCategory;
            }
            const response = await api.get('/publications/', { params });
            setPublications(response.data);
        } catch (error) {
            console.error('Failed to fetch publications:', error);
        } finally {
            setLoading(false);
        }
    };

    // Effect for fetching
    useEffect(() => {
        fetchPublications();
        // Optional: Poll for updates every 30s
        const interval = setInterval(fetchPublications, 30000);
        return () => clearInterval(interval);
    }, [activeCategory, searchQuery]);

    const fetchRecent = async () => {
        try {
            const recentResponse = await api.get('/publications/recent', { params: { limit: 6 } });
            setRecentlyRead(recentResponse.data);
        } catch (error) {
            console.error('Failed to fetch recent publications:', error);
        }
    };

    useEffect(() => {
        fetchRecent();
    }, []);

    const handleOpenReader = (publicationId) => {
        navigate(`/read/${publicationId}`);
    };

    const handleRemoveProgress = async (publicationId) => {
        try {
            await api.delete(`/publications/${publicationId}/progress`);
            setRecentlyRead(prev => prev.filter(pub => pub.id !== publicationId));
        } catch (error) {
            console.error('Failed to remove reading progress:', error);
        }
    };

    const categories = [
        { id: 'newspaper', label: t('dashboard.newspapers') || 'Newspapers' },
        { id: 'magazine', label: t('dashboard.magazines') || 'Magazines' },
        { id: 'book', label: t('dashboard.books') || 'Books' },
    ];

    if (loading && publications.length === 0) {
        return (
            <>
                <Header searchQuery={searchQuery} onSearchChange={setSearchQuery} />
                <div className="container">
                    <div className="loading-container">
                        <div className="loading-spinner"></div>
                        <p>{t('dashboard.loading')}</p>
                    </div>
                </div>
            </>
        );
    }

    return (
        <>
            <Header
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
            />

            <main className="dashboard">
                <div className="container">
                    {!searchQuery ? (
                        <>
                            {recentlyRead.length > 0 && (
                                <section className="section">
                                    <p className="scroll-section-label">📖 {t('dashboard.continueReading')}</p>
                                    <div className="horizontal-scroll-wrapper">
                                        <div className="horizontal-scroll-list">
                                            {recentlyRead.map(pub => (
                                                <div key={pub.id} className="horizontal-scroll-item">
                                                    <PublicationCard
                                                        publication={pub}
                                                        onClick={() => handleOpenReader(pub.id)}
                                                        showProgress
                                                        onRemove={handleRemoveProgress}
                                                    />
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </section>
                            )}

                            <section className="section">
                                <div className="category-tabs">
                                    {categories.map(cat => (
                                        <button
                                            key={cat.id}
                                            className={`category-tab ${activeCategory === cat.id ? 'active' : ''}`}
                                            onClick={() => setActiveCategory(cat.id)}
                                        >
                                            {cat.label}
                                        </button>
                                    ))}
                                </div>

                                {activeCategory === 'book' ? (
                                    <div className="books-container">
                                        {(() => {
                                            const collections = {};
                                            const ungrouped = [];
                                            publications.forEach(pub => {
                                                if (pub.collection_name) {
                                                    if (!collections[pub.collection_name]) collections[pub.collection_name] = [];
                                                    collections[pub.collection_name].push(pub);
                                                } else {
                                                    ungrouped.push(pub);
                                                }
                                            });

                                            return (
                                                <>
                                                    {Object.keys(collections).map(collectionName => (
                                                        <div key={collectionName} className="book-collection" style={{ marginBottom: '2rem' }}>
                                                            <h3 className="section-title" style={{ fontSize: '1.25rem', marginBottom: '1rem', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem' }}>{collectionName}</h3>
                                                            <div className="publication-grid">
                                                                {collections[collectionName].map(pub => (
                                                                    <PublicationCard key={pub.id} publication={pub} onClick={() => handleOpenReader(pub.id)} />
                                                                ))}
                                                            </div>
                                                        </div>
                                                    ))}
                                                    {ungrouped.length > 0 && (
                                                        <div className="book-collection">
                                                            {Object.keys(collections).length > 0 && (
                                                                <h3 className="section-title" style={{ fontSize: '1.25rem', marginBottom: '1rem', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem' }}>
                                                                    {t('dashboard.otherBooks') || 'Other Books'}
                                                                </h3>
                                                            )}
                                                            <div className="publication-grid">
                                                                {ungrouped.map(pub => (
                                                                    <PublicationCard key={pub.id} publication={pub} onClick={() => handleOpenReader(pub.id)} />
                                                                ))}
                                                            </div>
                                                        </div>
                                                    )}
                                                </>
                                            );
                                        })()}
                                    </div>
                                ) : (
                                    <div className="publication-grid">
                                        {publications.map(pub => (
                                            <PublicationCard
                                                key={pub.id}
                                                publication={pub}
                                                onClick={() => handleOpenReader(pub.id)}
                                            />
                                        ))}
                                    </div>
                                )}
                            </section>
                        </>
                    ) : (
                        <section className="section">
                            <div className="section-header">
                                <h2 className="section-title">🔍 {t('dashboard.search')}</h2>
                                <button
                                    className="btn btn-secondary"
                                    onClick={() => setSearchQuery('')}
                                    style={{ marginLeft: 'auto' }}
                                >
                                    {t('common.clear')}
                                </button>
                            </div>

                            {publications.length > 0 ? (
                                <div className="publication-grid">
                                    {publications.map(pub => (
                                        <PublicationCard
                                            key={pub.id}
                                            publication={pub}
                                            onClick={() => handleOpenReader(pub.id)}
                                        />
                                    ))}
                                </div>
                            ) : (
                                <div className="loading-container">
                                    <p>{t('dashboard.noPublications')}</p>
                                </div>
                            )}
                        </section>
                    )}
                </div>
            </main>
        </>
    );
};

export default Dashboard;
