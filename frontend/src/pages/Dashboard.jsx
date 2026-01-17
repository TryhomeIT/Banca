import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { useQuery } from "convex/react";
import { api as convexApi } from "../../convex/_generated/api";
import api from '../services/api';
import Header from '../components/Header';
import PublicationCard from '../components/PublicationCard';

const Dashboard = () => {
    const { user } = useAuth();
    const { t } = useTranslation();
    const navigate = useNavigate();
    
    const [searchQuery, setSearchQuery] = useState('');
    const [activeCategory, setActiveCategory] = useState('newspaper'); // Default to newspaper
    const [recentlyRead, setRecentlyRead] = useState([]);
    
    // Real-time publications from Convex
    // Since 'all' is gone, we always filter by category
    const convexPublications = useQuery(convexApi.publications.list, {
        category: activeCategory
    });

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

    // Filter by search query (client-side for now, or could be moved to Convex)
    const filteredPublications = convexPublications ? convexPublications.filter(pub => 
        pub.title.toLowerCase().includes(searchQuery.toLowerCase())
    ) : [];

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
        { id: 'newspaper', label: t('dashboard.newspapers') },
        { id: 'magazine', label: t('dashboard.magazines') },
        { id: 'others', label: t('dashboard.others') },
    ];

    if (convexPublications === undefined) {
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
                                    <div className="section-header">
                                        <h2 className="section-title">📖 {t('dashboard.continueReading')}</h2>
                                    </div>
                                    <div className="publication-grid">
                                        {recentlyRead.map(pub => (
                                            <PublicationCard
                                                key={pub.id}
                                                publication={pub}
                                                onClick={() => handleOpenReader(pub.id)}
                                                showProgress
                                                onRemove={handleRemoveProgress}
                                            />
                                        ))}
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

                                <div className="publication-grid">
                                    {filteredPublications.map(pub => (
                                        <PublicationCard
                                            key={pub._id}
                                            publication={pub}
                                            onClick={() => handleOpenReader(pub.external_id || pub.id)}
                                        />
                                    ))}
                                </div>
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

                            {filteredPublications.length > 0 ? (
                                <div className="publication-grid">
                                    {filteredPublications.map(pub => (
                                        <PublicationCard
                                            key={pub._id}
                                            publication={pub}
                                            onClick={() => handleOpenReader(pub.external_id || pub.id)}
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
