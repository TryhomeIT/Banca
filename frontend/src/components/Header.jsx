import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import api from '../services/api';
import siteLogo from '../assets/site_logo.png';

const Header = ({ searchQuery, onSearchChange }) => {
    const { user, logout } = useAuth();
    const { t, i18n } = useTranslation();
    const navigate = useNavigate();
    const [othersCount, setOthersCount] = useState(0);
    const [showLangMenu, setShowLangMenu] = useState(false);
    const [isMobileSearchOpen, setIsMobileSearchOpen] = useState(false);
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    const languages = [
        { code: 'en', name: 'English', flag: '🇬🇧' },
        { code: 'pt', name: 'Português', flag: '🇵🇹' },
        { code: 'es', name: 'Español', flag: '🇪🇸' },
        { code: 'nl', name: 'Nederlands', flag: '🇳🇱' }
    ];

    const currentLanguage = languages.find(lang => lang.code === i18n.language) || languages[1];

    useEffect(() => {
        if (user?.is_admin) {
            const fetchOthersCount = async () => {
                try {
                    const response = await api.get('/admin/status');
                    setOthersCount(response.data.folders.others.count || 0);
                } catch (error) {
                    console.error('Failed to fetch others count:', error);
                }
            };

            fetchOthersCount();
            // Optional: poll every minute
            const interval = setInterval(fetchOthersCount, 60000);
            return () => clearInterval(interval);
        }
    }, [user]);

    const changeLanguage = (langCode) => {
        i18n.changeLanguage(langCode);
        setShowLangMenu(false);
    };

    return (
        <>
            <header className="header">
                <div className="container header-content">
                    <div
                        className="header-logo"
                        onClick={() => navigate('/')}
                        style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                    >
                        <img src={siteLogo} alt="Banca" style={{ height: '32px', width: 'auto' }} />
                    </div>

                    <nav className="header-nav">
                        {/* Mobile Search Toggle */}
                        <button
                            className="btn btn-secondary btn-icon mobile-only"
                            onClick={() => setIsMobileSearchOpen(!isMobileSearchOpen)}
                        >
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <circle cx="11" cy="11" r="8" />
                                <path d="M21 21l-4.35-4.35" />
                            </svg>
                        </button>

                        {/* Search - Desktop */}
                        <div className="header-search desktop-only">
                            <svg className="header-search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <circle cx="11" cy="11" r="8" />
                                <path d="M21 21l-4.35-4.35" />
                            </svg>
                            <input
                                type="text"
                                className="input"
                                placeholder={t('dashboard.search')}
                                value={searchQuery}
                                onChange={(e) => onSearchChange(e.target.value)}
                            />
                        </div>

                        <div className="desktop-only header-actions">
                            {/* Language Selector */}
                            <div style={{ position: 'relative' }}>
                                <button
                                    className="btn btn-secondary btn-icon"
                                    onClick={() => setShowLangMenu(!showLangMenu)}
                                    title={t('settings.selectLanguage')}
                                >
                                    {currentLanguage.flag}
                                </button>
                                {showLangMenu && (
                                    <div className="lang-dropdown">
                                        {languages.map(lang => (
                                            <button
                                                key={lang.code}
                                                onClick={() => changeLanguage(lang.code)}
                                                className={`lang-btn ${i18n.language === lang.code ? 'active' : ''}`}
                                            >
                                                <span>{lang.flag}</span>
                                                <span>{lang.name}</span>
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* Settings Button */}
                            {user?.is_admin && (
                                <button
                                    className="btn btn-secondary btn-icon"
                                    onClick={() => navigate('/settings')}
                                    title={`${othersCount} files pending in Others`}
                                    style={{ position: 'relative' }}
                                >
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
                                        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1Z" />
                                    </svg>
                                    {othersCount > 0 && (
                                        <span className="notification-badge">
                                            {othersCount > 99 ? '99+' : othersCount}
                                        </span>
                                    )}
                                </button>
                            )}

                            {/* User Menu */}
                            <div className="header-user" onClick={logout} title="Click to logout">
                                <div className="header-avatar">
                                    {user?.username?.charAt(0).toUpperCase() || 'U'}
                                </div>
                            </div>
                        </div>

                        {/* Burger Button - Mobile Only */}
                        <button
                            className={`hamburger-btn mobile-only ${isMenuOpen ? 'open' : ''}`}
                            onClick={() => setIsMenuOpen(!isMenuOpen)}
                            aria-label="Menu"
                        >
                            <span></span>
                            <span></span>
                            <span></span>
                        </button>
                    </nav>
                </div>
            </header>

            {/* Mobile Menu - Slide from Right */}
            {isMenuOpen && <div className="mobile-drawer-backdrop" onClick={() => setIsMenuOpen(false)} />}
            <div className={`mobile-drawer ${isMenuOpen ? 'open' : ''}`}>
                <div className="mobile-drawer-header">
                    <span className="mobile-drawer-title">Menu</span>
                    <button className="mobile-drawer-close" onClick={() => setIsMenuOpen(false)}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M18 6L6 18M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="mobile-drawer-content">
                    {user?.is_admin && (
                        <button className="mobile-drawer-item" onClick={() => { navigate('/settings'); setIsMenuOpen(false); }}>
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
                                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1Z" />
                            </svg>
                            {t('settings.title')}
                            {othersCount > 0 && <span className="notification-badge" style={{ position: 'static', marginLeft: 'auto' }}>{othersCount}</span>}
                        </button>
                    )}

                    <div className="mobile-drawer-divider" />

                    <div className="mobile-drawer-section">
                        <div className="mobile-drawer-label">{t('settings.selectLanguage')}</div>
                        <div className="mobile-lang-grid">
                            {languages.map(lang => (
                                <button
                                    key={lang.code}
                                    className={`mobile-lang-btn ${i18n.language === lang.code ? 'active' : ''}`}
                                    onClick={() => changeLanguage(lang.code)}
                                >
                                    <span>{lang.flag}</span>
                                    <span>{lang.name}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="mobile-drawer-footer">
                    <div className="mobile-drawer-user">
                        <div className="header-avatar">
                            {user?.username?.charAt(0).toUpperCase()}
                        </div>
                        <div className="mobile-drawer-user-info">
                            <div className="mobile-drawer-user-name">{user?.username}</div>
                            <div className="mobile-drawer-user-role">{user?.is_admin ? 'Administrator' : 'User'}</div>
                        </div>
                    </div>
                    <button className="mobile-drawer-logout" onClick={logout}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
                        </svg>
                        {t('common.logout')}
                    </button>
                </div>
            </div>

            {/* Mobile Search Overlay */}
            {isMobileSearchOpen && (
                <div className="mobile-search-bar mobile-only">
                    <div className="container mobile-search-container">
                        <div className="header-search" style={{ flex: 1, display: 'block' }}>
                            <svg className="header-search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <circle cx="11" cy="11" r="8" />
                                <path d="M21 21l-4.35-4.35" />
                            </svg>
                            <input
                                autoFocus
                                type="text"
                                className="input"
                                placeholder={t('dashboard.search')}
                                value={searchQuery}
                                onChange={(e) => onSearchChange(e.target.value)}
                            />
                        </div>
                        <button
                            className="btn btn-secondary btn-icon"
                            onClick={() => setIsMobileSearchOpen(false)}
                        >
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M18 6L6 18M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>
            )}
        </>
    );
};

export default Header;
