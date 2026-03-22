import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import Header from '../components/Header';

const Settings = () => {
    useTranslation(); // i18n context available
    const { user, loading } = useAuth();
    const navigate = useNavigate();

    useEffect(() => {
        if (!loading && !user?.is_admin) {
            navigate('/');
        }
    }, [user, loading, navigate]);

    if (loading) return <div className="loading-spinner"></div>;
    if (!user?.is_admin) return null; // Avoid rendering content during redirect

    return (
        <div className="settings-page">
            <Header />

            <div className="settings-container">
                {/* Main Content Area - Scrollable List */}
                <main className="settings-content-scroll">
                    <section id="status" className="settings-section">
                        <SystemControl />
                    </section>
                </main>
            </div>
        </div>
    );
};

// ================== System Control (Status & Entry Point) ==================
const SystemControl = () => {
    const [status, setStatus] = useState(null);
    const [aiSettings, setAiSettings] = useState({});
    const [generalSettings, setGeneralSettings] = useState({});
    const [loading, setLoading] = useState(true);

    // Modal States
    const [showTelegramModal, setShowTelegramModal] = useState(false);
    const [showAIModal, setShowAIModal] = useState(false);
    const [showConvexModal, setShowConvexModal] = useState(false);
    const [showUserModal, setShowUserModal] = useState(false);
    const [showContentModal, setShowContentModal] = useState(false);

    const fetchData = async () => {
        try {
            const [s, a, g] = await Promise.all([
                api.get('/admin/status'),
                api.get('/admin/settings?category=ai'),
                api.get('/admin/settings?category=general')
            ]);
            setStatus(s.data);
            setAiSettings(a.data || {});
            setGeneralSettings(g.data || {});
        } catch (err) {
            console.error('Failed to fetch system status:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
    }, []);

    const toggleBot = async () => {
        await api.post(status.telegram_bot.is_running ? '/admin/telegram/stop' : '/admin/telegram/start');
        fetchData();
    };

    if (loading) return <div className="loading-spinner"></div>;

    const isGeminiActive = !!aiSettings.GEMINI_API_KEY;
    const isConvexEnabled = generalSettings.USE_CONVEX === 'true';
    const userCount = status?.database?.total_users || 0;
    const fileCount = status?.database?.total_publications || 0;

    return (
        <div className="section">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>

                {/* 1. Telegram Bot Status Card */}
                <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <div style={{
                                width: '40px', height: '40px', borderRadius: '10px',
                                background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa',
                                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem'
                            }}>
                                🤖
                            </div>
                            <div>
                                <h4 style={{ fontSize: '1rem', marginBottom: '0.1rem' }}>Telegram Bot</h4>
                                <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
                                    {status?.telegram_bot?.is_running ? 'Monitoring channel' : 'Service stopped'}
                                </span>
                            </div>
                        </div>
                        <div style={{
                            padding: '0.25rem 0.6rem', borderRadius: '20px', fontSize: '0.75rem', fontWeight: '600',
                            background: status?.telegram_bot?.is_running ? 'rgba(74, 222, 128, 0.15)' : 'rgba(248, 113, 113, 0.15)',
                            color: status?.telegram_bot?.is_running ? '#4ade80' : '#f87171',
                            display: 'flex', alignItems: 'center'
                        }}>
                            <div style={{
                                width: '6px', height: '6px', borderRadius: '50%',
                                background: status?.telegram_bot?.is_running ? '#4ade80' : '#f87171',
                                marginRight: '6px', boxShadow: status?.telegram_bot?.is_running ? '0 0 8px #4ade80' : 'none'
                            }}></div>
                            {status?.telegram_bot?.is_running ? 'Connected' : 'Disconnected'}
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: '0.75rem', marginTop: 'auto' }}>
                        <button
                            className={`btn ${status?.telegram_bot?.is_running ? 'btn-secondary' : 'btn-primary'}`}
                            onClick={toggleBot}
                            style={{ flex: 1 }}
                        >
                            {status?.telegram_bot?.is_running ? 'Stop' : 'Start'}
                        </button>
                        <button className="btn btn-secondary" onClick={() => setShowTelegramModal(true)}>
                            Configure
                        </button>
                    </div>
                </div>

                {/* 2. Gemini AI Status Card */}
                <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <div style={{
                                width: '40px', height: '40px', borderRadius: '10px',
                                background: 'rgba(139, 92, 246, 0.15)', color: '#a78bfa',
                                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem'
                            }}>
                                🧠
                            </div>
                            <div>
                                <h4 style={{ fontSize: '1rem', marginBottom: '0.1rem' }}>Gemini AI</h4>
                                <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
                                    {isGeminiActive ? 'Ready for tasks' : 'API Key missing'}
                                </span>
                            </div>
                        </div>
                        <div style={{
                            padding: '0.25rem 0.6rem', borderRadius: '20px', fontSize: '0.75rem', fontWeight: '600',
                            background: isGeminiActive ? 'rgba(74, 222, 128, 0.15)' : 'rgba(148, 163, 184, 0.15)',
                            color: isGeminiActive ? '#4ade80' : '#94a3b8'
                        }}>
                            {isGeminiActive ? 'Active' : 'Not Configured'}
                        </div>
                    </div>

                    <button
                        className="btn btn-secondary"
                        onClick={() => setShowAIModal(true)}
                        style={{ marginTop: 'auto', width: '100%' }}
                    >
                        Configure AI
                    </button>
                </div>

                {/* 3. Convex Cloud Status Card */}
                <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <div style={{
                                width: '40px', height: '40px', borderRadius: '10px',
                                background: 'rgba(249, 115, 22, 0.15)', color: '#fb923c',
                                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem'
                            }}>
                                ☁️
                            </div>
                            <div>
                                <h4 style={{ fontSize: '1rem', marginBottom: '0.1rem' }}>Convex Cloud</h4>
                                <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
                                    {isConvexEnabled ? 'Syncing to cloud' : 'Local only mode'}
                                </span>
                            </div>
                        </div>
                        <div style={{
                            padding: '0.25rem 0.6rem', borderRadius: '20px', fontSize: '0.75rem', fontWeight: '600',
                            background: isConvexEnabled ? 'rgba(74, 222, 128, 0.15)' : 'rgba(148, 163, 184, 0.15)',
                            color: isConvexEnabled ? '#4ade80' : '#94a3b8'
                        }}>
                            {isConvexEnabled ? 'Enabled' : 'Disabled'}
                        </div>
                    </div>

                    <button
                        className="btn btn-secondary"
                        onClick={() => setShowConvexModal(true)}
                        style={{ marginTop: 'auto', width: '100%' }}
                    >
                        Configure Cloud
                    </button>
                </div>

                {/* 4. Files Status Card */}
                <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <div style={{
                                width: '40px', height: '40px', borderRadius: '10px',
                                background: 'rgba(34, 197, 94, 0.15)', color: '#4ade80',
                                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem'
                            }}>
                                📂
                            </div>
                            <div>
                                <h4 style={{ fontSize: '1rem', marginBottom: '0.1rem' }}>Files</h4>
                                <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
                                    {fileCount} total publication{fileCount !== 1 ? 's' : ''}
                                </span>
                            </div>
                        </div>
                        <div style={{
                            padding: '0.25rem 0.6rem', borderRadius: '20px', fontSize: '0.75rem', fontWeight: '600',
                            background: 'rgba(255, 255, 255, 0.1)', color: '#cbd5e1'
                        }}>
                            {fileCount}
                        </div>
                    </div>

                    <button
                        className="btn btn-secondary"
                        onClick={() => setShowContentModal(true)}
                        style={{ marginTop: 'auto', width: '100%' }}
                    >
                        Manage Files & Retention
                    </button>
                </div>

                {/* 5. User Management Status Card */}
                <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <div style={{
                                width: '40px', height: '40px', borderRadius: '10px',
                                background: 'rgba(236, 72, 153, 0.15)', color: '#f472b6',
                                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem'
                            }}>
                                👥
                            </div>
                            <div>
                                <h4 style={{ fontSize: '1rem', marginBottom: '0.1rem' }}>Users</h4>
                                <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
                                    {userCount} registered user{userCount !== 1 ? 's' : ''}
                                </span>
                            </div>
                        </div>
                        <div style={{
                            padding: '0.25rem 0.6rem', borderRadius: '20px', fontSize: '0.75rem', fontWeight: '600',
                            background: 'rgba(255, 255, 255, 0.1)', color: '#cbd5e1'
                        }}>
                            {userCount}
                        </div>
                    </div>

                    <button
                        className="btn btn-secondary"
                        onClick={() => setShowUserModal(true)}
                        style={{ marginTop: 'auto', width: '100%' }}
                    >
                        Manage Users
                    </button>
                </div>
            </div>

            {/* Modals */}
            {showTelegramModal && <TelegramConfigModal onClose={() => setShowTelegramModal(false)} />}
            {showAIModal && <AIConfigModal onClose={() => { setShowAIModal(false); fetchData(); }} />}
            {showConvexModal && <ConvexConfigModal onClose={() => { setShowConvexModal(false); fetchData(); }} />}
            {showUserModal && <UserManagementModal onClose={() => { setShowUserModal(false); fetchData(); }} />}
            {showContentModal && <ContentConfigModal onClose={() => { setShowContentModal(false); fetchData(); }} />}
        </div>
    );
};

// ================== Modals ==================

const ContentConfigModal = ({ onClose }) => {
    const [config, setConfig] = useState(null);
    const [generalSettings, setGeneralSettings] = useState({});
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('actions'); // actions, retention, rules, pending

    // Search states for rules and pending tabs
    const [rulesSearch, setRulesSearch] = useState('');
    const [pendingSearch, setPendingSearch] = useState('');

    // Sync Status & Logs
    const [isSyncing, setIsSyncing] = useState(false);
    const [syncLogs, setSyncLogs] = useState([]);
    const logsEndRef = useRef(null);

    const fetchData = async () => {
        try {
            const [c, g] = await Promise.all([
                api.get('/admin/publications/config'),
                api.get('/admin/settings?category=general')
            ]);
            setConfig(c.data);
            setGeneralSettings(g.data || {});
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    // Polling logs during sync
    useEffect(() => {
        let interval;
        if (isSyncing) {
            interval = setInterval(async () => {
                try {
                    const response = await api.get('/admin/logs?type=telegram_bot&lines=50');
                    if (response.data.logs) {
                        const lines = response.data.logs.split('\n');
                        // Filter for relevant logs or just show the tail
                        setSyncLogs(lines.filter(l => l.trim() !== ''));

                        // Check for completion signal in logs
                        if (response.data.logs.includes('Scan complete')) {
                            setIsSyncing(false);
                        }
                    }
                } catch (error) {
                    console.error("Failed to fetch sync logs", error);
                }
            }, 2000);
        }
        return () => clearInterval(interval);
    }, [isSyncing]);

    // Auto-scroll to bottom of logs
    useEffect(() => {
        if (logsEndRef.current) {
            logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [syncLogs]);

    // Manual Actions
    const handleSync = async (days) => {
        if (!confirm(`Scan history for last ${days} days? This may take a while.`)) return;
        setSyncLogs([`Starting sync for last ${days} days...`]);
        setIsSyncing(true);
        try { await api.post(`/admin/telegram/scan/days?days=${days}`); }
        catch {
            setSyncLogs(prev => [...prev, 'Failed to start sync command.']);
            setIsSyncing(false);
        }
    };

    const handleScanOthers = async () => {
        setSyncLogs(['Scanning "Others" folder...']);
        setIsSyncing(true);
        try { await api.post('/admin/telegram/scan/outros'); }
        catch { setIsSyncing(false); }
    };

    const handleSyncConvex = async () => {
        if (!confirm('Force sync all files to Convex?')) return;
        try { await api.post('/admin/telegram/sync-convex'); alert('Sync started'); } catch { alert('Failed'); }
    };

    const handleReorganize = async () => {
        if (!confirm('Reorganize all files based on current rules?')) return;
        try { await api.post('/admin/publications/reorganize'); alert('Reorganization started'); } catch { alert('Failed'); }
    };

    const handleCleanup = async () => {
        if (!confirm('⚠️ WARNING: This will DELETE ALL records and files, then re-download the last 7 days. Continue?')) return;
        setSyncLogs(['🧹 Starting full cleanup...']);
        setIsSyncing(true);
        try {
            const response = await api.post('/admin/telegram/cleanup');
            setSyncLogs(prev => [...prev, '✅ ' + response.data.message]);
        } catch (err) {
            setSyncLogs(prev => [...prev, '❌ Cleanup failed: ' + (err.response?.data?.detail || err.message)]);
            setIsSyncing(false);
        }
    };

    const handleDownloadLogs = async () => {
        try {
            const response = await api.get('/admin/logs/download?type=telegram_bot', { responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `telegram_bot_${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.log`);
            document.body.appendChild(link);
            link.click();
            link.parentNode.removeChild(link);
        } catch (err) {
            console.error(err);
            alert('Failed to download logs');
        }
    };

    // Retention Settings
    const handleSaveRetention = async () => {
        try {
            await api.post('/admin/settings', { settings: generalSettings });
            alert('Retention settings saved');
        } catch {
            alert('Failed to save settings');
        }
    };

    // Classification Rules
    const handleAddItem = async (e, category, value) => {
        e.preventDefault();
        if (!value || !value.trim()) return;
        try {
            await api.post('/admin/publications/add', { category, item: value });
            fetchData();
            e.target.elements[0].value = '';
        } catch {
            alert('Failed');
        }
    };

    const handleMoveItem = async (fromCategory, toCategory, item) => {
        try {
            await api.post('/admin/publications/move', { item, from_category: fromCategory, to_category: toCategory });
            fetchData();
        } catch {
            alert('Failed to move item');
        }
    };

    const handleRemoveItem = async (category, item) => {
        try { await api.post('/admin/publications/remove', { category, item }); fetchData(); } catch {
            alert('Failed');
        }
    };

    // Pending Actions
    const handleRecategorize = async (filename, targetCategory) => {
        try { await api.post('/admin/publications/recategorize', { filename, target_category: targetCategory }); fetchData(); } catch {
            alert('Failed');
        }
    };

    const handleDeleteOthers = async (filename) => {
        if (!confirm('Permanently delete file?')) return;
        try { await api.post('/admin/publications/others/delete', { filename }); fetchData(); } catch {
            alert('Failed');
        }
    };

    const handleRestoreItem = async (item, targetCategory) => {
        try { await api.post('/admin/publications/restore', { item, target_category: targetCategory }); fetchData(); } catch {
            alert('Failed');
        }
    };

    const renderList = (categoryKey, title, moveTargetKey = null) => {
        // Filter items based on search
        const items = config[categoryKey] || [];
        const filteredItems = rulesSearch
            ? items.filter(item => item.toLowerCase().includes(rulesSearch.toLowerCase()))
            : items;

        return (
            <div style={{ marginBottom: '1.5rem' }}>
                <h5 style={{ marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--color-text-secondary)' }}>
                    {title} ({filteredItems.length}/{items.length})
                </h5>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.5rem', maxHeight: '200px', overflowY: 'auto' }}>
                    {filteredItems.map(item => (
                        <span key={item} style={{
                            padding: '0.2rem 0.6rem', background: 'rgba(255,255,255,0.05)', borderRadius: '15px', fontSize: '0.8rem',
                            display: 'flex', alignItems: 'center', gap: '0.5rem', border: '1px solid var(--glass-border)'
                        }}>
                            {item}
                            {moveTargetKey && (
                                <button
                                    onClick={() => handleMoveItem(categoryKey, moveTargetKey, item)}
                                    title={`Move to ${moveTargetKey === 'jornais' ? 'Newspapers' : 'Magazines'}`}
                                    style={{ background: 'none', border: 'none', color: 'var(--color-accent-primary)', cursor: 'pointer', padding: 0, display: 'flex' }}
                                >
                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                                    </svg>
                                </button>
                            )}
                            <button onClick={() => handleRemoveItem(categoryKey, item)} style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer' }}>✕</button>
                        </span>
                    ))}
                </div>
                <form onSubmit={(e) => handleAddItem(e, categoryKey, e.target.elements[0].value)} style={{ display: 'flex', gap: '0.5rem' }}>
                    <input className="input" placeholder="Add keyword..." style={{ padding: '0.4rem' }} />
                    <button type="submit" className="btn btn-secondary" style={{ padding: '0.4rem 0.8rem' }}>Add</button>
                </form>
            </div>
        );
    };

    return (
        <div className="modal-overlay">
            <div className="modal" style={{ maxWidth: '800px', height: '80vh', display: 'flex', flexDirection: 'column' }}>
                <div className="modal-header">
                    <h4 className="modal-title">File Management</h4>
                    <button className="modal-close" onClick={onClose}>✕</button>
                </div>

                <div style={{ display: 'flex', borderBottom: '1px solid var(--glass-border)', padding: '0 0.5rem', overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
                    {['actions', 'retention', 'rules', 'pending'].map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            style={{
                                padding: '0.75rem 1rem', background: 'transparent', border: 'none',
                                color: activeTab === tab ? 'var(--color-accent-primary)' : 'var(--color-text-secondary)',
                                borderBottom: activeTab === tab ? '2px solid var(--color-accent-primary)' : 'none',
                                cursor: 'pointer', fontWeight: '500', textTransform: 'capitalize',
                                whiteSpace: 'nowrap', flexShrink: 0
                            }}
                        >
                            {tab}
                        </button>
                    ))}
                </div>

                <div className="modal-body" style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
                    {loading ? <div className="loading-spinner"></div> : (
                        <>
                            {activeTab === 'actions' && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.75rem' }}>
                                        <button className="btn btn-secondary" onClick={() => handleSync(7)} disabled={isSyncing}>
                                            {isSyncing ? '⏳ Syncing...' : '🔄 Sync Last 7 Days'}
                                        </button>
                                        <button className="btn btn-secondary" onClick={() => handleSync(30)} disabled={isSyncing}>
                                            {isSyncing ? '⏳ Syncing...' : '🔄 Sync Last 30 Days'}
                                        </button>
                                        <button className="btn btn-secondary" onClick={handleScanOthers} disabled={isSyncing}>🧠 Process "Others" Folder</button>
                                        <button className="btn btn-secondary" onClick={handleSyncConvex}>☁️ Force Convex Sync</button>
                                        <button className="btn btn-secondary" onClick={handleReorganize}>📂 Reorganize Files</button>
                                        <button className="btn btn-secondary" style={{ color: 'var(--color-error)' }} onClick={handleCleanup} disabled={isSyncing}>
                                            {isSyncing ? '⏳ Cleaning...' : '🧹 Cleanup Files'}
                                        </button>
                                    </div>

                                    {/* Log Viewer for Sync Tasks */}
                                    <div style={{
                                        background: 'rgba(0, 0, 0, 0.3)',
                                        borderRadius: '8px',
                                        padding: '1rem',
                                        marginTop: '0.5rem',
                                        border: '1px solid var(--glass-border)'
                                    }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', alignItems: 'center' }}>
                                            <span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', fontWeight: '600' }}>
                                                {isSyncing ? '🟢 TASK RUNNING...' : 'TASK LOGS'}
                                            </span>
                                            {isSyncing && <span className="loading-spinner" style={{ width: '14px', height: '14px' }}></span>}
                                        </div>
                                        <div style={{
                                            height: '200px',
                                            overflowY: 'auto',
                                            fontFamily: 'monospace',
                                            fontSize: '0.8rem',
                                            color: '#cbd5e1',
                                            whiteSpace: 'pre-wrap'
                                        }}>
                                            {syncLogs.length > 0 ? (
                                                syncLogs.map((log, i) => (
                                                    <div key={i} style={{ marginBottom: '4px', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                                                        {log}
                                                    </div>
                                                ))
                                            ) : (
                                                <span style={{ color: 'var(--color-text-muted)', fontStyle: 'italic' }}>No active task logs...</span>
                                            )}
                                            <div ref={logsEndRef} />
                                        </div>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                                        <button className="btn btn-secondary" onClick={handleDownloadLogs} style={{ fontSize: '0.8rem', padding: '0.3rem 0.8rem' }}>
                                            📥 Download Full Log
                                        </button>
                                    </div>
                                </div>
                            )}

                            {activeTab === 'retention' && (
                                <div>
                                    <div className="input-group">
                                        <label>Newspapers Retention (Days)</label>
                                        <input className="input" type="number"
                                            value={generalSettings.DOWNLOADS_RETENTION_DAYS_JORNAIS || '7'}
                                            onChange={e => setGeneralSettings({ ...generalSettings, DOWNLOADS_RETENTION_DAYS_JORNAIS: e.target.value })}
                                        />
                                    </div>
                                    <div className="input-group">
                                        <label>Magazines Retention (Days)</label>
                                        <input className="input" type="number"
                                            value={generalSettings.DOWNLOADS_RETENTION_DAYS_REVISTAS || '90'}
                                            onChange={e => setGeneralSettings({ ...generalSettings, DOWNLOADS_RETENTION_DAYS_REVISTAS: e.target.value })}
                                        />
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
                                        <button className="btn btn-primary" onClick={handleSaveRetention}>Save Settings</button>
                                    </div>
                                </div>
                            )}

                            {activeTab === 'rules' && (
                                <div>
                                    <div style={{ marginBottom: '1rem' }}>
                                        <input
                                            className="input"
                                            placeholder="🔍 Search keywords..."
                                            value={rulesSearch}
                                            onChange={(e) => setRulesSearch(e.target.value)}
                                            style={{ width: '100%', padding: '0.6rem' }}
                                        />
                                    </div>
                                    {renderList('jornais', 'Newspaper Keywords', 'revistas')}
                                    {renderList('revistas', 'Magazine Keywords', 'jornais')}
                                    {renderList('keywords', 'General Keywords')}
                                </div>
                            )}

                            {activeTab === 'pending' && (
                                <div>
                                    <div style={{ marginBottom: '1rem' }}>
                                        <input
                                            className="input"
                                            placeholder="🔍 Search pending files..."
                                            value={pendingSearch}
                                            onChange={(e) => setPendingSearch(e.target.value)}
                                            style={{ width: '100%', padding: '0.6rem' }}
                                        />
                                    </div>

                                    {(() => {
                                        const filteredOthers = pendingSearch
                                            ? (config.others || []).filter(f =>
                                                f.filename.toLowerCase().includes(pendingSearch.toLowerCase()) ||
                                                (f.extracted_name || '').toLowerCase().includes(pendingSearch.toLowerCase())
                                            )
                                            : (config.others || []);

                                        return filteredOthers.length > 0 ? (
                                            <>
                                                <h5 style={{ marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--color-text-secondary)' }}>
                                                    Pending Files ({filteredOthers.length}/{config.others?.length || 0})
                                                </h5>
                                                {filteredOthers.map((file) => (
                                                    <div key={file.filename} style={{
                                                        display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.8rem 0',
                                                        borderBottom: '1px solid var(--glass-border)'
                                                    }}>
                                                        <div style={{ flex: 1, minWidth: '200px', overflow: 'hidden', marginRight: '1rem' }}>
                                                            <div style={{ fontWeight: '600', color: '#f8fafc', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                                                                {file.extracted_name || file.filename}
                                                            </div>
                                                            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                                                                {file.filename}
                                                            </div>
                                                        </div>
                                                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                                                            <button className="btn btn-secondary" style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem' }} onClick={() => handleRecategorize(file.filename, 'jornais')}>News</button>
                                                            <button className="btn btn-secondary" style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem' }} onClick={() => handleRecategorize(file.filename, 'revistas')}>Mag</button>
                                                            <button className="btn btn-secondary" style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem', color: 'var(--color-error)' }} onClick={() => handleDeleteOthers(file.filename)}>✕</button>
                                                        </div>
                                                    </div>
                                                ))}
                                            </>
                                        ) : (
                                            <p style={{ color: 'var(--color-text-muted)', textAlign: 'center', padding: '2rem' }}>
                                                {pendingSearch ? 'No matching files found.' : 'No pending files in "Others".'}
                                            </p>
                                        );
                                    })()}

                                    {(() => {
                                        const filteredIgnored = pendingSearch
                                            ? (config.ignored || []).filter(item => item.toLowerCase().includes(pendingSearch.toLowerCase()))
                                            : (config.ignored || []);

                                        return filteredIgnored.length > 0 && (
                                            <div style={{ marginTop: '2rem' }}>
                                                <h5 style={{ color: 'var(--color-error)', marginBottom: '0.5rem' }}>
                                                    Ignored Items ({filteredIgnored.length}/{config.ignored?.length || 0})
                                                </h5>
                                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                                                    {filteredIgnored.map(item => (
                                                        <span key={item} style={{
                                                            padding: '0.2rem 0.6rem', background: 'rgba(239, 68, 68, 0.1)', color: '#f87171', borderRadius: '15px', fontSize: '0.8rem',
                                                            display: 'flex', alignItems: 'center', gap: '0.5rem', border: '1px solid rgba(239, 68, 68, 0.2)'
                                                        }}>
                                                            {item}
                                                            <button onClick={() => handleRestoreItem(item, 'jornais')} style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer' }}>↩️</button>
                                                            <button onClick={() => handleRemoveItem('ignored', item)} style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer' }}>✕</button>
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        );
                                    })()}
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

const UserManagementModal = ({ onClose }) => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showAddForm, setShowAddForm] = useState(false);
    const [newUser, setNewUser] = useState({ username: '', email: '', password: '', is_admin: false });

    const fetchUsers = async () => {
        try {
            const response = await api.get('/admin/users');
            setUsers(response.data);
        } catch (err) {
            console.error('Failed to load users:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchUsers();
    }, []);

    const handleDelete = async (userId) => {
        if (!window.confirm('Are you sure you want to delete this user?')) return;
        try {
            await api.delete(`/admin/users/${userId}`);
            fetchUsers();
        } catch {
            alert('Failed to delete user');
        }
    };

    const handleResetPassword = async (userId) => {
        const newPassword = window.prompt('Enter new password for this user:');
        if (!newPassword) return;
        try {
            await api.put(`/admin/users/${userId}`, { password: newPassword });
            alert('Password reset successfully');
        } catch {
            alert('Failed to reset password');
        }
    };

    const handleAddUser = async (e) => {
        e.preventDefault();
        try {
            await api.post('/admin/users', newUser);
            setShowAddForm(false);
            setNewUser({ username: '', email: '', password: '', is_admin: false });
            fetchUsers();
        } catch (err) {
            alert(err.response?.data?.detail || 'Failed to create user');
        }
    };

    return (
        <div className="modal-overlay">
            <div className="modal" style={{ maxWidth: '700px' }}>
                <div className="modal-header">
                    <h4 className="modal-title">User Management</h4>
                    <button className="modal-close" onClick={onClose}>✕</button>
                </div>
                <div className="modal-body" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
                    {loading ? (
                        <div className="loading-spinner"></div>
                    ) : (
                        <>
                            {!showAddForm ? (
                                <>
                                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1rem' }}>
                                        <button className="btn btn-primary" onClick={() => setShowAddForm(true)}>+ Add User</button>
                                    </div>
                                    <div style={{ overflowX: 'auto' }}>
                                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                                            <thead>
                                                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--glass-border)', background: 'var(--color-bg-tertiary)' }}>
                                                    <th style={{ padding: '0.75rem' }}>Username</th>
                                                    <th style={{ padding: '0.75rem' }}>Role</th>
                                                    <th style={{ padding: '0.75rem', textAlign: 'right' }}>Actions</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {users.map(user => (
                                                    <tr key={user.id} style={{ borderBottom: '1px solid var(--glass-border)' }}>
                                                        <td style={{ padding: '0.75rem' }}>
                                                            <div>{user.username}</div>
                                                            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>{user.email}</div>
                                                        </td>
                                                        <td style={{ padding: '0.75rem' }}>
                                                            <span className="badge" style={{
                                                                backgroundColor: user.is_admin ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.1)',
                                                                color: user.is_admin ? '#818cf8' : '#cbd5e1',
                                                                padding: '0.2rem 0.6rem',
                                                                borderRadius: '4px',
                                                                fontSize: '0.75rem',
                                                                fontWeight: '600'
                                                            }}>
                                                                {user.is_admin ? 'Admin' : 'User'}
                                                            </span>
                                                        </td>
                                                        <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                                                            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                                                                <button
                                                                    className="btn btn-secondary"
                                                                    style={{ padding: '0.4rem 0.6rem', color: 'var(--color-accent-primary)' }}
                                                                    onClick={() => handleResetPassword(user.id)}
                                                                    title="Reset Password"
                                                                >
                                                                    🔑
                                                                </button>
                                                                <button
                                                                    className="btn btn-secondary"
                                                                    style={{ padding: '0.4rem 0.6rem', color: 'var(--color-error)' }}
                                                                    onClick={() => handleDelete(user.id)}
                                                                    title="Delete User"
                                                                >
                                                                    ✕
                                                                </button>
                                                            </div>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </>
                            ) : (
                                <form onSubmit={handleAddUser}>
                                    <div className="input-group">
                                        <label>Username</label>
                                        <input className="input" required value={newUser.username} onChange={e => setNewUser({ ...newUser, username: e.target.value })} />
                                    </div>
                                    <div className="input-group">
                                        <label>Email</label>
                                        <input className="input" type="email" required value={newUser.email} onChange={e => setNewUser({ ...newUser, email: e.target.value })} />
                                    </div>
                                    <div className="input-group">
                                        <label>Password</label>
                                        <input className="input" type="password" required value={newUser.password} onChange={e => setNewUser({ ...newUser, password: e.target.value })} />
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '1rem' }}>
                                        <input type="checkbox" checked={newUser.is_admin} onChange={e => setNewUser({ ...newUser, is_admin: e.target.checked })} style={{ width: 'auto' }} />
                                        <label style={{ marginBottom: 0 }}>Administrator Access</label>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1.5rem' }}>
                                        <button type="button" className="btn btn-secondary" onClick={() => setShowAddForm(false)}>Cancel</button>
                                        <button type="submit" className="btn btn-primary">Create User</button>
                                    </div>
                                </form>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

const TelegramConfigModal = ({ onClose }) => {
    const [settings, setSettings] = useState({});
    const [saving, setSaving] = useState(false);
    const [loginStep, setLoginStep] = useState('config');
    const [loginData, setLoginData] = useState({ code: '', password: '' });

    useEffect(() => {
        api.get('/admin/settings?category=telegram').then(res => setSettings(res.data)).catch(console.error);
    }, []);

    const handleSave = async () => {
        setSaving(true);
        try { await api.post('/admin/settings', { settings }); alert('Saved'); }
        catch { alert('Failed'); }
        finally { setSaving(false); }
    };

    const handleRequestCode = async () => {
        try {
            await api.post('/admin/telegram/login/request', {
                phone: settings.TELEGRAM_PHONE,
                api_id: settings.TELEGRAM_API_ID,
                api_hash: settings.TELEGRAM_API_HASH
            });
            setLoginStep('code');
            alert('Code sent!');
        } catch { alert('Request failed'); }
    };

    const handleVerifyCode = async (e) => {
        e.preventDefault();
        try {
            await api.post('/admin/telegram/login/verify', {
                phone: settings.TELEGRAM_PHONE,
                code: loginData.code,
                password: loginData.password
            });
            setLoginStep('success');
            alert('Logged in!');
        } catch { alert('Verification failed'); }
    };

    return (
        <div className="modal-overlay">
            <div className="modal">
                <div className="modal-header">
                    <h4 className="modal-title">Telegram Configuration</h4>
                    <button className="modal-close" onClick={onClose}>✕</button>
                </div>
                <div className="modal-body">
                    {loginStep === 'config' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <div className="input-group">
                                <label>API ID</label>
                                <input className="input" value={settings.TELEGRAM_API_ID || ''} onChange={e => setSettings({ ...settings, TELEGRAM_API_ID: e.target.value })} />
                            </div>
                            <div className="input-group">
                                <label>API Hash</label>
                                <input className="input" value={settings.TELEGRAM_API_HASH || ''} onChange={e => setSettings({ ...settings, TELEGRAM_API_HASH: e.target.value })} />
                            </div>
                            <div className="input-group">
                                <label>Phone Number</label>
                                <input className="input" value={settings.TELEGRAM_PHONE || ''} onChange={e => setSettings({ ...settings, TELEGRAM_PHONE: e.target.value })} placeholder="+351..." />
                            </div>
                            <div className="input-group">
                                <label>Channel ID / Username</label>
                                <input className="input" value={settings.TELEGRAM_CHANNEL_ID || ''} onChange={e => setSettings({ ...settings, TELEGRAM_CHANNEL_ID: e.target.value })} />
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
                                <button className="btn btn-secondary" onClick={handleRequestCode} disabled={!settings.TELEGRAM_PHONE}>Request Login Code</button>
                                <button className="btn btn-primary" onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save Settings'}</button>
                            </div>
                        </div>
                    )}
                    {loginStep === 'code' && (
                        <form onSubmit={handleVerifyCode} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <div className="input-group">
                                <label>Enter Code</label>
                                <input className="input" required value={loginData.code} onChange={e => setLoginData({ ...loginData, code: e.target.value })} />
                            </div>
                            <div className="input-group">
                                <label>2FA Password (Optional)</label>
                                <input className="input" type="password" value={loginData.password} onChange={e => setLoginData({ ...loginData, password: e.target.value })} />
                            </div>
                            <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>Verify</button>
                        </form>
                    )}
                    {loginStep === 'success' && (
                        <div style={{ textAlign: 'center', color: '#4ade80' }}>
                            <h4>✅ Authenticated Successfully</h4>
                            <button className="btn btn-secondary" style={{ marginTop: '1rem' }} onClick={() => setLoginStep('config')}>Back to Settings</button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

const AIConfigModal = ({ onClose }) => {
    const [settings, setSettings] = useState({});
    const [saving, setSaving] = useState(false);
    const [showKey, setShowKey] = useState(false);

    useEffect(() => {
        api.get('/admin/settings?category=ai').then(res => setSettings(res.data || {})).catch(console.error);
    }, []);

    const handleSave = async () => {
        setSaving(true);
        try { await api.post('/admin/settings', { settings }); alert('Saved'); onClose(); }
        catch { alert('Failed'); }
        finally { setSaving(false); }
    };

    return (
        <div className="modal-overlay">
            <div className="modal">
                <div className="modal-header">
                    <h4 className="modal-title">AI Configuration</h4>
                    <button className="modal-close" onClick={onClose}>✕</button>
                </div>
                <div className="modal-body">
                    <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
                        Configure Google Gemini API key to enable AI features.
                    </p>
                    <div className="input-group" style={{ position: 'relative' }}>
                        <label>API Key</label>
                        <div style={{ position: 'relative' }}>
                            <input
                                className="input"
                                type={showKey ? "text" : "password"}
                                value={settings.GEMINI_API_KEY || ''}
                                onChange={e => setSettings({ ...settings, GEMINI_API_KEY: e.target.value })}
                                placeholder="Paste your API key here..."
                                style={{ paddingRight: '45px', fontFamily: 'monospace' }}
                            />
                            <button
                                type="button"
                                onClick={() => setShowKey(!showKey)}
                                style={{
                                    position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)',
                                    background: 'transparent', border: 'none', color: 'var(--color-text-muted)',
                                    cursor: 'pointer', padding: '8px'
                                }}
                            >
                                {showKey ? '👁️' : '👁️‍🗨️'}
                            </button>
                        </div>
                        <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: '0.5rem' }}>
                            <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--color-accent-primary)' }}>Get API Key</a>
                        </p>
                    </div>
                </div>
                <div className="modal-footer">
                    <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
                    <button className="btn btn-primary" onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save Changes'}</button>
                </div>
            </div>
        </div>
    );
};

const ConvexConfigModal = ({ onClose }) => {
    const [settings, setSettings] = useState({});
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        api.get('/admin/settings?category=general').then(res => setSettings(res.data || {})).catch(console.error);
    }, []);

    const handleSave = async () => {
        setSaving(true);
        try { await api.post('/admin/settings', { settings }); alert('Saved'); onClose(); }
        catch { alert('Failed'); }
        finally { setSaving(false); }
    };

    return (
        <div className="modal-overlay">
            <div className="modal">
                <div className="modal-header">
                    <h4 className="modal-title">Convex Cloud Configuration</h4>
                    <button className="modal-close" onClick={onClose}>✕</button>
                </div>
                <div className="modal-body">
                    <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
                        Enable cloud synchronization to backup your library and access it remotely.
                    </p>
                    <div className="input-group">
                        <label>Cloud Sync Status</label>
                        <select
                            className="input"
                            value={settings.USE_CONVEX || 'false'}
                            onChange={e => setSettings({ ...settings, USE_CONVEX: e.target.value })}
                        >
                            <option value="true">Enabled (Cloud & Local)</option>
                            <option value="false">Disabled (Local Only)</option>
                        </select>
                        <p style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginTop: '0.5rem' }}>
                            When disabled, the application runs entirely on your local machine.
                        </p>
                    </div>
                </div>
                <div className="modal-footer">
                    <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
                    <button className="btn btn-primary" onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save Changes'}</button>
                </div>
            </div>
        </div>
    );
};

export default Settings;
