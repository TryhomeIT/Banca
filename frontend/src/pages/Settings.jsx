import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '../services/api';
import Header from '../components/Header';

const Settings = () => {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState('system');

    const tabs = [
        { id: 'system', label: 'System', icon: '⚙️' },
        { id: 'users', label: 'Users', icon: '👥' },
        { id: 'content', label: 'Content', icon: '📂' },
        { id: 'telegram', label: 'Telegram', icon: '🤖' },
        { id: 'ai', label: 'AI', icon: '🧠' },
    ];

    return (
        <div className="settings-page">
            <Header />

            <div className="settings-container">
                {/* Tab Navigation - Sidebar on desktop, bottom bar on mobile */}
                <nav className="settings-tabs">
                    {tabs.map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`settings-tab ${activeTab === tab.id ? 'active' : ''}`}
                        >
                            <span className="settings-tab-icon">{tab.icon}</span>
                            <span className="settings-tab-label">{tab.label}</span>
                        </button>
                    ))}
                </nav>

                {/* Content */}
                <div className="settings-content">
                    {activeTab === 'users' && <UserManagement />}
                    {activeTab === 'content' && <ContentConfig />}
                    {activeTab === 'telegram' && <TelegramSettings />}
                    {activeTab === 'ai' && <AISettings />}
                    {activeTab === 'system' && <SystemControl />}
                </div>
            </div>
        </div>
    );
};

// ================== User Management Component ==================
const UserManagement = () => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showAddModal, setShowAddModal] = useState(false);
    const [newUser, setNewUser] = useState({ username: '', email: '', password: '', is_admin: false });

    const fetchUsers = async () => {
        try {
            const response = await api.get('/admin/users');
            setUsers(response.data);
        } catch (err) {
            setError('Failed to load users');
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
        } catch (err) {
            alert('Failed to delete user');
        }
    };

    const handleAddUser = async (e) => {
        e.preventDefault();
        try {
            await api.post('/admin/users', newUser);
            setShowAddModal(false);
            setNewUser({ username: '', email: '', password: '', is_admin: false });
            fetchUsers();
        } catch (err) {
            alert(err.response?.data?.detail || 'Failed to create user');
        }
    };

    if (loading) return <div className="loading-spinner"></div>;

    return (
        <div className="section">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h3 className="section-title">User Management</h3>
                <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>+ Add User</button>
            </div>

            <div className="card" style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                    <thead>
                        <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }}>
                            <th style={{ padding: '0.75rem' }}>Username</th>
                            <th style={{ padding: '0.75rem' }}>Email</th>
                            <th style={{ padding: '0.75rem' }}>Role</th>
                            <th style={{ padding: '0.75rem', textAlign: 'right' }}>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users.map(user => (
                            <tr key={user.id} style={{ borderBottom: '1px solid var(--glass-border)' }}>
                                <td style={{ padding: '0.6rem 0.75rem' }}>{user.username}</td>
                                <td style={{ padding: '0.6rem 0.75rem' }}>{user.email}</td>
                                <td style={{ padding: '0.6rem 0.75rem' }}>
                                    <span className="badge" style={{
                                        backgroundColor: user.is_admin ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.1)',
                                        padding: '0.2rem 0.5rem',
                                        borderRadius: '4px',
                                        fontSize: '0.75rem'
                                    }}>
                                        {user.is_admin ? 'Admin' : 'User'}
                                    </span>
                                </td>
                                <td style={{ padding: '0.6rem 0.75rem', textAlign: 'right' }}>
                                    <button
                                        className="btn btn-secondary"
                                        style={{ padding: '0.25rem 0.5rem', color: 'var(--color-error)', fontSize: '0.8rem' }}
                                        onClick={() => handleDelete(user.id)}
                                        title="Delete User"
                                    >
                                        ✕
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {showAddModal && (
                <div className="modal-overlay">
                    <div className="modal">
                        <div className="modal-header">
                            <h4 className="modal-title">Create New User</h4>
                            <button className="modal-close" onClick={() => setShowAddModal(false)}>✕</button>
                        </div>
                        <form onSubmit={handleAddUser}>
                            <div className="modal-body">
                                <div className="input-group">
                                    <label>Username</label>
                                    <input
                                        className="input"
                                        required
                                        value={newUser.username}
                                        onChange={e => setNewUser({ ...newUser, username: e.target.value })}
                                    />
                                </div>
                                <div className="input-group">
                                    <label>Email</label>
                                    <input
                                        className="input"
                                        type="email"
                                        required
                                        value={newUser.email}
                                        onChange={e => setNewUser({ ...newUser, email: e.target.value })}
                                    />
                                </div>
                                <div className="input-group">
                                    <label>Password</label>
                                    <input
                                        className="input"
                                        type="password"
                                        required
                                        value={newUser.password}
                                        onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                                    />
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '1rem' }}>
                                    <input
                                        type="checkbox"
                                        checked={newUser.is_admin}
                                        onChange={e => setNewUser({ ...newUser, is_admin: e.target.checked })}
                                        style={{ width: 'auto' }}
                                    />
                                    <label style={{ marginBottom: 0 }}>Is Admin?</label>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn btn-secondary" onClick={() => setShowAddModal(false)}>Cancel</button>
                                <button type="submit" className="btn btn-primary">Create User</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

// ================== Content Config Component ==================
const ContentConfig = () => {
    const [config, setConfig] = useState(null);
    const [loading, setLoading] = useState(true);
    const [runningTasks, setRunningTasks] = useState({});

    const fetchRunningTasks = async () => {
        try {
            const response = await api.get('/admin/tasks/status');
            setRunningTasks(response.data.running_tasks || {});
        } catch (err) {
            console.error('Failed to fetch running tasks:', err);
        }
    };

    const isTaskRunning = (taskName) => taskName in runningTasks;

    const fetchConfig = async () => {
        try {
            const response = await api.get('/admin/publications/config');
            setConfig(response.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchConfig();
        fetchRunningTasks();
        const taskInterval = setInterval(fetchRunningTasks, 3000);
        return () => clearInterval(taskInterval);
    }, []);

    const handleAddItem = async (e, category, value) => {
        e.preventDefault();
        if (!value || !value.trim()) return;
        try {
            await api.post('/admin/publications/add', { category, item: value });
            fetchConfig();
            return true;
        } catch (err) {
            alert('Failed to add item');
            return false;
        }
    };

    const handleMoveItem = async (fromCategory, toCategory, item) => {
        try {
            await api.post('/admin/publications/move', {
                item,
                from_category: fromCategory,
                to_category: toCategory
            });
            fetchConfig();
        } catch (err) {
            console.error('Failed to move item:', err);
        }
    };

    const handleRemoveItem = async (category, item, permanent = false) => {
        // Only confirm for permanent deletions
        if (permanent && !window.confirm(`Permanently delete "${item}"? This cannot be undone.`)) return;
        try {
            await api.post('/admin/publications/remove', { category, item, permanent });
            fetchConfig();
        } catch (err) {
            alert('Failed to remove item');
        }
    };

    const handleRestoreItem = async (item, targetCategory) => {
        try {
            await api.post('/admin/publications/restore', { item, target_category: targetCategory });
            fetchConfig();
        } catch (err) {
            alert('Failed to restore item: ' + (err.response?.data?.detail || err.message));
        }
    };

    const handleRecategorize = async (filename, targetCategory) => {
        try {
            await api.post('/admin/publications/recategorize', { filename, target_category: targetCategory });
            fetchConfig();
        } catch (err) {
            alert('Failed to recategorize file');
        }
    };

    const handleDeleteOthers = async (filename) => {
        if (!window.confirm(`Are you sure you want to permanently delete "${filename}"?`)) return;
        try {
            await api.post('/admin/publications/others/delete', { filename });
            fetchConfig();
        } catch (err) {
            alert('Failed to delete file');
        }
    };

    if (loading) return <div className="loading-spinner"></div>;

    const renderList = (title, categoryKey, description, moveTargetKey = null) => (
        <div className="card" style={{ padding: '1rem', marginBottom: '1rem' }}>
            <h4 style={{ fontSize: '1rem' }}>{title}</h4>
            <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.8125rem', marginBottom: '0.75rem' }}>
                {description}
            </p>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '0.75rem' }}>
                {config[categoryKey]?.map(item => (
                    <span key={item} title={item} style={{
                        padding: '0.2rem 0.6rem',
                        background: 'rgba(255, 255, 255, 0.1)',
                        borderRadius: '20px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.4rem',
                        fontSize: '0.8125rem',
                        maxWidth: '100%',
                        overflow: 'hidden'
                    }}>
                        <span style={{
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            flex: '1',
                            minWidth: 0
                        }}>
                            {item}
                        </span>
                        {moveTargetKey && (
                            <button
                                onClick={() => handleMoveItem(categoryKey, moveTargetKey, item)}
                                title={`Move to ${moveTargetKey === 'jornais' ? 'Newspapers' : 'Magazines'}`}
                                style={{ background: 'none', border: 'none', color: 'var(--color-accent-primary)', cursor: 'pointer', padding: 0, display: 'flex', flexShrink: 0, marginLeft: '0.25rem' }}
                            >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                                </svg>
                            </button>
                        )}
                        <button
                            onClick={() => handleRemoveItem(categoryKey, item)}
                            style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', padding: 0, flexShrink: 0 }}
                        >✕</button>
                    </span>
                ))}
                {(!config[categoryKey] || config[categoryKey].length === 0) && (
                    <span style={{ color: 'var(--color-text-muted)', fontStyle: 'italic' }}>No items defined</span>
                )}
            </div>

            <form onSubmit={async (e) => {
                const input = e.target.elements[0];
                const success = await handleAddItem(e, categoryKey, input.value);
                if (success) input.value = '';
            }} style={{ display: 'flex', gap: '0.5rem' }}>
                <input
                    className="input"
                    placeholder="Add new item..."
                    style={{ padding: '0.5rem 1rem' }}
                />
                <button type="submit" className="btn btn-secondary">Add</button>
            </form>
        </div>
    );

    return (
        <div className="section">
            <h3 className="section-title">Content Classification Rules</h3>
            <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1.5rem' }}>
                Define how files are categorized. The bot checks these keywords in filenames.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 450px), 1fr))', gap: '1rem' }}>
                {renderList('Newspapers (Jornais)', 'jornais', 'Keywords to identify newspapers', 'revistas')}
                {renderList('Magazines (Revistas)', 'revistas', 'Keywords to identify magazines', 'jornais')}
                {renderList('Scan Keywords', 'keywords', 'Keywords to download regardless of -PT')}
            </div>

            {config.ignored && config.ignored.length > 0 && (
                <div className="card" style={{ padding: '1rem', marginTop: '1.5rem', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                    <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#f87171' }}>
                        🚫 Ignored Publications / Keywords
                        <span className="badge" style={{ background: 'rgba(239,68,68,0.1)', color: '#f87171' }}>{config.ignored.length}</span>
                    </h4>
                    <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.8125rem', marginBottom: '1rem' }}>
                        These items will NEVER be automatically categorized. Files matching these names will stay in the Others folder.
                    </p>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                        {config.ignored.map(item => (
                            <span key={item} title={item} style={{
                                padding: '0.3rem 0.75rem',
                                background: 'rgba(239, 68, 68, 0.05)',
                                border: '1px solid rgba(239, 68, 68, 0.1)',
                                borderRadius: '20px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                fontSize: '0.8125rem',
                                maxWidth: '300px'
                            }}>
                                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item}</span>
                                <div style={{ display: 'flex', gap: '0.2rem', borderLeft: '1px solid rgba(239,68,68,0.2)', paddingLeft: '0.4rem', marginLeft: '0.2rem' }}>
                                    <button
                                        onClick={() => handleRestoreItem(item, 'jornais')}
                                        title="Restore to Newspapers"
                                        style={{ background: 'none', border: 'none', color: 'var(--color-accent-primary)', cursor: 'pointer', padding: '0 2px', fontSize: '0.9rem' }}
                                    >📰</button>
                                    <button
                                        onClick={() => handleRestoreItem(item, 'revistas')}
                                        title="Restore to Magazines"
                                        style={{ background: 'none', border: 'none', color: 'var(--color-accent-secondary)', cursor: 'pointer', padding: '0 2px', fontSize: '0.9rem' }}
                                    >📑</button>
                                    <button
                                        onClick={() => handleRemoveItem('ignored', item, true)}
                                        title="Delete Permanently"
                                        style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer', padding: '0 2px' }}
                                    >✕</button>
                                </div>
                            </span>
                        ))}
                    </div>
                </div>
            )}

            <div style={{ marginTop: '1.5rem', marginBottom: '1rem' }}>
                <button
                    className="btn btn-secondary"
                    disabled={isTaskRunning('reorganize')}
                    onClick={async () => {
                        if (!confirm('This will scan all PDF files and move any that are in the wrong folder. Continue?')) return;
                        try {
                            fetchRunningTasks(); // Update immediately to show loading
                            const res = await api.post('/admin/publications/reorganize');
                            alert(`Reorganization complete!\n\n📰 Moved to Jornais: ${res.data.files_moved_to_jornais}\n📖 Moved to Revistas: ${res.data.files_moved_to_revistas}\n🤖 AI Categorized: ${res.data.ai_categorized || 0}\n💾 Database records updated: ${res.data.database_records_updated}`);
                            fetchConfig();
                            fetchRunningTasks();
                        } catch (err) {
                            alert('Failed: ' + (err.response?.data?.detail || err.message));
                            fetchRunningTasks();
                        }
                    }}
                >
                    {isTaskRunning('reorganize') ? '⏳ Reorganizing...' : '🔄 Reorganize Files'}
                </button>
                <span style={{ marginLeft: '0.75rem', fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
                    {isTaskRunning('reorganize')
                        ? 'Task in progress... (you can leave this page)'
                        : 'Scan all PDFs and move misplaced files to correct folders'}
                </span>
            </div>

            {config.others && config.others.length > 0 && (
                <div className="card" style={{ padding: '1rem', marginTop: '1.5rem' }}>
                    <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.1rem' }}>
                        📂 Unmatched Files (Others)
                        <span className="badge" style={{ fontSize: '0.7rem' }}>{config.others.length}</span>
                    </h4>
                    <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.8125rem', marginBottom: '1rem' }}>
                        Files that didn't match any rules. Click to add requested keyword to rules and move file.
                    </p>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 300px), 1fr))', gap: '0.75rem' }}>
                        {config.others.map(file => (
                            <div key={file.filename} className="card" style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                background: 'rgba(255,255,255,0.03)',
                                padding: '0.75rem',
                                border: '1px solid rgba(255,255,255,0.05)',
                                borderRadius: '8px'
                            }}>
                                <div style={{ overflow: 'hidden', marginRight: '1rem', flex: '1', minWidth: 0 }}>
                                    <div style={{
                                        fontSize: '0.85rem',
                                        fontWeight: '600',
                                        color: 'var(--color-text-primary)',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        whiteSpace: 'nowrap'
                                    }} title={file.clean_name}>
                                        {file.clean_name}
                                    </div>
                                    <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={file.filename}>
                                        {file.filename}
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '0.4rem', flexShrink: 0 }}>
                                    <button
                                        className="btn btn-secondary"
                                        style={{ padding: '0.2rem 0.4rem', fontSize: '0.7rem', minWidth: '70px' }}
                                        onClick={() => handleRecategorize(file.filename, 'jornais')}
                                        title="Assign to Newspapers"
                                    >+ Jornais</button>
                                    <button
                                        className="btn btn-secondary"
                                        style={{ padding: '0.2rem 0.4rem', fontSize: '0.7rem', minWidth: '70px' }}
                                        onClick={() => handleRecategorize(file.filename, 'revistas')}
                                        title="Assign to Magazines"
                                    >+ Revistas</button>
                                    <button
                                        className="btn btn-secondary"
                                        style={{ padding: '0.2rem 0.4rem', fontSize: '0.7rem', color: 'var(--color-error)' }}
                                        onClick={() => handleDeleteOthers(file.filename)}
                                        title="Delete file permanently"
                                    >✕</button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

// ================== Telegram Settings Component ==================
const TelegramSettings = () => {
    const [settings, setSettings] = useState({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [loginStep, setLoginStep] = useState('config'); // config, code, success
    const [loginData, setLoginData] = useState({ phone: '', code: '', password: '' });
    const [showHelp, setShowHelp] = useState(false);

    const hasSettings = settings.TELEGRAM_API_ID && settings.TELEGRAM_API_HASH && settings.TELEGRAM_PHONE;

    const fetchSettings = async () => {
        try {
            const response = await api.get('/admin/settings?category=telegram');
            setSettings(response.data);
            // Auto-show help if settings are empty
            if (!response.data.TELEGRAM_API_ID && !response.data.TELEGRAM_API_HASH) {
                setShowHelp(true);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSettings();
    }, []);

    const handleChange = (key, value) => {
        setSettings(prev => ({ ...prev, [key]: value }));
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            await api.post('/admin/settings', { settings });
            alert('Settings saved successfully');
        } catch (err) {
            alert('Failed to save settings');
        } finally {
            setSaving(false);
        }
    };

    const handleRequestCode = async (e) => {
        e.preventDefault();
        try {
            await api.post('/admin/telegram/login/request', {
                phone: settings.TELEGRAM_PHONE,
                api_id: settings.TELEGRAM_API_ID,
                api_hash: settings.TELEGRAM_API_HASH
            });
            setLoginStep('code');
            alert('Login code requested. Please check your Telegram app.');
        } catch (err) {
            alert(err.response?.data?.detail || 'Failed to request login code');
        }
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
            alert('Successfully logged in to Telegram!');
        } catch (err) {
            alert(err.response?.data?.detail || 'Verification failed');
        }
    };

    if (loading) return <div className="loading-spinner"></div>;

    return (
        <div className="section">
            {/* Help Toggle - Shows info icon when settings exist */}
            {hasSettings && (
                <div style={{ marginBottom: '1rem' }}>
                    <button
                        onClick={() => setShowHelp(!showHelp)}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#38bdf8',
                            cursor: 'pointer',
                            fontSize: '0.9rem',
                            padding: '0.5rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                        }}
                    >
                        ℹ️ {showHelp ? 'Hide setup guide' : 'Show setup guide'}
                    </button>
                </div>
            )}

            {showHelp && (
                <div className="card" style={{ padding: '1rem', marginBottom: '1.5rem', background: 'rgba(56, 189, 248, 0.05)', border: '1px solid rgba(56, 189, 248, 0.2)' }}>
                    <h4 style={{ color: '#38bdf8', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem' }}>
                        <span>📖</span> How to setup Telegram
                    </h4>
                    <ol style={{ paddingLeft: '1.25rem', color: 'var(--color-text-secondary)', fontSize: '0.85rem', lineHeight: '1.5' }}>
                        <li>Go to <a href="https://my.telegram.org" target="_blank" rel="noopener noreferrer" style={{ color: '#38bdf8' }}>my.telegram.org</a> and log in with your phone number.</li>
                        <li>Click on <strong>"API development tools"</strong>.</li>
                        <li>Create a new application (you can name it "Banca App"). You'll get an <strong>API ID</strong> and <strong>API Hash</strong>.</li>
                        <li>Copy these values into the fields below and click <strong>"Save Settings"</strong>.</li>
                        <li>Once saved, scroll down to <strong>"Telegram Authentication"</strong> and click <strong>"Request Login Code"</strong>.</li>
                        <li>Enter the code you receive in your Telegram app to finish the setup!</li>
                    </ol>
                </div>
            )}

            <h3 className="section-title">Telegram Bot Credentials</h3>
            <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
                Configure your Telegram API credentials and source channel.
            </p>

            <div className="card" style={{ padding: '1.25rem', marginBottom: '1.5rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
                    <div className="input-group" style={{ marginBottom: 0 }}>
                        <label>API ID</label>
                        <input className="input" style={{ padding: '0.6rem' }} value={settings.TELEGRAM_API_ID || ''} onChange={e => handleChange('TELEGRAM_API_ID', e.target.value)} />
                    </div>
                    <div className="input-group" style={{ marginBottom: 0 }}>
                        <label>API Hash</label>
                        <input className="input" style={{ padding: '0.6rem' }} value={settings.TELEGRAM_API_HASH || ''} onChange={e => handleChange('TELEGRAM_API_HASH', e.target.value)} />
                    </div>
                    <div className="input-group" style={{ marginBottom: 0 }}>
                        <label>Phone Number</label>
                        <input className="input" style={{ padding: '0.6rem' }} value={settings.TELEGRAM_PHONE || ''} onChange={e => handleChange('TELEGRAM_PHONE', e.target.value)} placeholder="+351..." />
                    </div>
                    <div className="input-group" style={{ marginBottom: 0 }}>
                        <label>Source Channel ID / @username</label>
                        <input className="input" style={{ padding: '0.6rem' }} value={settings.TELEGRAM_CHANNEL_ID || ''} onChange={e => handleChange('TELEGRAM_CHANNEL_ID', e.target.value)} />
                    </div>
                </div>
                <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                    {saving ? 'Saving...' : 'Save Settings'}
                </button>
            </div>

            <h3 className="section-title">Telegram Authentication</h3>
            <div className="card" style={{ padding: '1.5rem' }}>
                {loginStep === 'config' && (
                    <div>
                        <p style={{ marginBottom: '1rem' }}>The bot needs to authenticate with your Telegram account to access private channels and download files.</p>
                        <button className="btn btn-secondary" onClick={handleRequestCode} disabled={!settings.TELEGRAM_PHONE || !settings.TELEGRAM_API_ID}>
                            Request Login Code
                        </button>
                    </div>
                )}
                {loginStep === 'code' && (
                    <form onSubmit={handleVerifyCode}>
                        <div className="input-group">
                            <label>Login Code (from Telegram message)</label>
                            <input className="input" required value={loginData.code} onChange={e => setLoginData({ ...loginData, code: e.target.value })} />
                        </div>
                        <div className="input-group">
                            <label>2FA Password (only if enabled)</label>
                            <input className="input" type="password" value={loginData.password} onChange={e => setLoginData({ ...loginData, password: e.target.value })} />
                        </div>
                        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                            <button type="submit" className="btn btn-primary">Verify Code</button>
                            <button type="button" className="btn btn-secondary" onClick={() => setLoginStep('config')}>Back</button>
                        </div>
                    </form>
                )}
                {loginStep === 'success' && (
                    <div style={{ textAlign: 'center', color: 'var(--color-success)' }}>
                        <h4>✅ Authenticated Successfully</h4>
                        <p>Your Telegram session is now active and stored.</p>
                        <button className="btn btn-secondary" style={{ marginTop: '1rem' }} onClick={() => setLoginStep('config')}>New Login</button>
                    </div>
                )}
            </div>
        </div>
    );
};

// ================== AI Settings Component ==================
const AISettings = () => {
    const [settings, setSettings] = useState({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    const fetchSettings = async () => {
        try {
            const response = await api.get('/admin/settings?category=ai');
            setSettings(response.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSettings();
    }, []);

    const handleChange = (key, value) => {
        setSettings(prev => ({ ...prev, [key]: value }));
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            await api.post('/admin/settings', { settings });
            alert('AI Settings saved successfully');
        } catch (err) {
            alert('Failed to save AI settings');
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div className="loading-spinner"></div>;

    return (
        <div className="section">
            <h3 className="section-title">Gemini AI Configuration</h3>
            <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1.5rem' }}>
                Used for automated file classification and "Outros" folder re-processing.
            </p>

            <div className="card" style={{ padding: '1.5rem' }}>
                <div className="input-group">
                    <label>Gemini API Key</label>
                    <input
                        className="input"
                        type="password"
                        value={settings.GEMINI_API_KEY || ''}
                        onChange={e => handleChange('GEMINI_API_KEY', e.target.value)}
                        placeholder="Enter your Google AI Studio API Key"
                    />
                </div>
                <div style={{ marginTop: '1rem' }}>
                    <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                        {saving ? 'Saving...' : 'Save AI Settings'}
                    </button>
                </div>
            </div>
        </div>
    );
};

// ================== System Control Component ==================
const SystemControl = () => {
    const navigate = useNavigate();
    const { t } = useTranslation();
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(true);
    const [runningTasks, setRunningTasks] = useState({});
    const [logs, setLogs] = useState('');
    const [logType, setLogType] = useState('telegram_bot');
    const logContainerRef = useRef(null);

    useEffect(() => {
        if (logContainerRef.current) {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
        }
    }, [logs]);

    const fetchStatus = async () => {
        try {
            const response = await api.get('/admin/status');
            setStatus(response.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const fetchRunningTasks = async () => {
        try {
            const response = await api.get('/admin/tasks/status');
            setRunningTasks(response.data.running_tasks || {});
        } catch (err) {
            console.error('Failed to fetch running tasks:', err);
        }
    };

    const fetchLogs = async () => {
        try {
            const response = await api.get(`/admin/logs?type=${logType}&lines=100`);
            setLogs(response.data.logs || '');
        } catch (err) {
            console.error('Failed to fetch logs:', err);
        }
    };

    useEffect(() => {
        fetchStatus();
        fetchLogs();
        fetchRunningTasks();
        const statusInterval = setInterval(fetchStatus, 5000);
        const logInterval = setInterval(fetchLogs, 5000);
        const taskInterval = setInterval(fetchRunningTasks, 3000);
        return () => {
            clearInterval(statusInterval);
            clearInterval(logInterval);
            clearInterval(taskInterval);
        };
    }, [logType]);

    const isTaskRunning = (taskName) => taskName in runningTasks;

    const toggleBot = async () => {
        if (!status) return;
        try {
            const endpoint = status.telegram_bot.is_running ? '/admin/telegram/stop' : '/admin/telegram/start';
            await api.post(endpoint);
            fetchStatus();
        } catch (err) {
            alert('Failed to change bot status');
        }
    };

    const triggerScan = async (days = 0) => {
        try {
            const endpoint = days > 0 ? `/admin/telegram/scan/days?days=${days}` : '/admin/telegram/scan';
            await api.post(endpoint);
            alert(`Scan requested (${days > 0 ? days + ' days' : 'quick'}) `);
            fetchRunningTasks();
        } catch (err) {
            alert('Scan failed to start');
        }
    };

    if (loading) return <div className="loading-spinner"></div>;

    if (!status) {
        return (
            <div className="section">
                <h3 className="section-title">System Status & Control</h3>
                <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
                    <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1.5rem' }}>Failed to load system status.</p>
                    <button className="btn btn-primary" onClick={fetchStatus}>Retry</button>
                </div>
            </div>
        );
    }

    return (
        <div className="section">
            <h3 className="section-title">System Status & Control</h3>

            <div className="card" style={{ padding: '1.5rem', marginBottom: '2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                    <div>
                        <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            Telegram Bot
                            <span style={{
                                padding: '0.25rem 0.75rem',
                                borderRadius: '20px',
                                background: status?.telegram_bot?.is_running ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                                color: status?.telegram_bot?.is_running ? '#4ade80' : '#f87171',
                                fontSize: '0.9rem'
                            }}>
                                {status?.telegram_bot?.is_running ? 'Running' : 'Stopped'}
                            </span>
                        </h4>
                        <p style={{ color: 'var(--color-text-secondary)', marginTop: '0.5rem' }}>
                            {status?.telegram_bot?.files_downloaded || 0} files processed today
                        </p>
                    </div>
                    <div style={{ display: 'flex', gap: '1rem' }}>
                        <button
                            className={`btn ${status?.telegram_bot?.is_running ? 'btn-secondary' : 'btn-primary'}`}
                            onClick={toggleBot}
                            style={status?.telegram_bot?.is_running ? { color: 'var(--color-error)', borderColor: 'rgba(239, 68, 68, 0.3)' } : {}}
                        >
                            {status?.telegram_bot?.is_running ? 'Stop Bot' : 'Start Bot'}
                        </button>
                    </div>
                </div>

                <div style={{ borderTop: '1px solid var(--glass-border)', paddingTop: '1.5rem' }}>
                    <h5 style={{ marginBottom: '1rem' }}>Manual Tasks</h5>
                    <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                        <button
                            className="btn btn-secondary"
                            onClick={() => triggerScan()}
                            disabled={!status?.telegram_bot?.is_running || isTaskRunning('scan')}
                        >
                            {isTaskRunning('scan') ? '⏳ Scanning...' : 'Quick Scan'}
                        </button>
                        <button
                            className="btn btn-secondary"
                            onClick={() => triggerScan(7)}
                            disabled={!status?.telegram_bot?.is_running || isTaskRunning('scan')}
                        >
                            {isTaskRunning('scan') ? '⏳ Scanning...' : 'Scan 7 Days'}
                        </button>
                        <button
                            className="btn btn-secondary"
                            onClick={() => triggerScan(30)}
                            disabled={!status?.telegram_bot?.is_running || isTaskRunning('scan')}
                        >
                            {isTaskRunning('scan') ? '⏳ Scanning...' : 'Scan 30 Days'}
                        </button>
                        <button
                            className="btn btn-secondary"
                            onClick={async () => {
                                try {
                                    await api.post('/admin/telegram/ai-categorize');
                                    fetchRunningTasks();
                                    alert('AI categorization manually triggered');
                                } catch (err) { alert('Failed'); }
                            }}
                            disabled={!status?.telegram_bot?.is_running || isTaskRunning('ai_categorize')}
                        >
                            {isTaskRunning('ai_categorize') ? '⏳ Categorizing...' : 'Run AI Categorization'}
                        </button>
                        <button
                            className="btn btn-secondary"
                            onClick={async () => {
                                try {
                                    await api.post('/admin/telegram/scan/outros');
                                    fetchRunningTasks();
                                    alert('Recategorization scan started');
                                } catch (err) { alert('Failed'); }
                            }}
                            disabled={!status?.telegram_bot?.is_running || isTaskRunning('scan_outros')}
                        >
                            {isTaskRunning('scan_outros') ? '⏳ Processing...' : 'Process Outros'}
                        </button>
                        <button
                            className="btn btn-secondary"
                            onClick={async () => {
                                if (!confirm('This will remove duplicate files and delete Jornais older than 7 days and Revistas older than 90 days. Continue?')) return;
                                try {
                                    await api.post('/admin/telegram/cleanup');
                                    fetchRunningTasks();
                                    alert('Cleanup task requested');
                                } catch (err) { alert('Failed'); }
                            }}
                            disabled={!status?.telegram_bot?.is_running || isTaskRunning('cleanup')}
                        >
                            {isTaskRunning('cleanup') ? '⏳ Cleaning...' : 'Cleanup Telegram Files'}
                        </button>
                        <button
                            className="btn btn-secondary"
                            onClick={async () => {
                                if (!confirm('This will scan all PDFs and DELETE any that are corrupted or 0 bytes. This cannot be undone. Continue?')) return;
                                try {
                                    await api.post('/admin/scan/corrupt');
                                    alert('Scan started in background. Check App Logs for progress.');
                                    setLogType('app'); // Switch to app logs
                                    fetchRunningTasks();
                                } catch (err) { alert('Failed: ' + (err.response?.data?.detail || err.message)); fetchRunningTasks(); }
                            }}
                            disabled={isTaskRunning('scan_corrupt')}
                        >
                            {isTaskRunning('scan_corrupt') ? '⏳ Scanning...' : '🧹 Remove Corrupt PDFs'}
                        </button>
                        <button
                            className="btn btn-secondary"
                            onClick={async () => {
                                if (!confirm('This will wipe the Cloud database and re-upload all local files. Fixes thumbnail mismatches. Continue?')) return;
                                try {
                                    fetchRunningTasks();
                                    await api.post('/admin/telegram/sync-convex');
                                    alert('Cloud sync complete! Thumbnails and metadata are now aligned.');
                                    fetchRunningTasks();
                                } catch (err) { alert('Failed: ' + (err.response?.data?.detail || err.message)); fetchRunningTasks(); }
                            }}
                            disabled={isTaskRunning('sync_convex')}
                        >
                            {isTaskRunning('sync_convex') ? '⏳ Syncing...' : '☁️ Force Cloud Sync'}
                        </button>
                    </div>
                </div>

                <div style={{ borderTop: '1px solid var(--glass-border)', paddingTop: '1.5rem', marginTop: '1.5rem' }}>
                    <h5 style={{ marginBottom: '1rem', color: '#f87171', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        ⚠️ Danger Zone
                    </h5>
                    <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>
                        Use these actions only if the system is corrupted or you want to start fresh.
                    </p>
                    <button
                        className="btn btn-secondary"
                        style={{ color: '#f87171', borderColor: 'rgba(239, 68, 68, 0.3)' }}
                        onClick={async () => {
                            if (!confirm('☢️ NUCLEAR RESET ☢️\n\nThis will:\n1. Wipe the entire database (User history lost)\n2. Reset Bot download history\n3. Rescan all files (Fixes missing items)\n4. Scan Telegram for missing files (last 7 days)\n\nAre you ABSOLUTELY sure?')) return;
                            try {
                                await api.post('/admin/reset', { days: 7, delete_downloads: false });
                                alert('System reset initiated. The page may reload or require login.');
                                window.location.reload();
                            } catch (err) {
                                alert('Reset failed: ' + (err.response?.data?.detail || err.message));
                            }
                        }}
                    >
                        ☢️ Full System Reset & Rescan
                    </button>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                <div className="card" style={{ padding: '1rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--color-accent-primary)' }}>{status?.database?.total_publications || 0}</div>
                    <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>Publications</div>
                </div>
                <div className="card" style={{ padding: '1rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--color-accent-secondary)' }}>{status?.database?.by_category?.newspaper || 0}</div>
                    <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>Newspapers</div>
                </div>
                <div className="card" style={{ padding: '1rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#fafafa' }}>{status?.database?.by_category?.magazine || 0}</div>
                    <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>Magazines</div>
                </div>
                <div className="card" style={{ padding: '1rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--color-text-muted)' }}>{status?.database?.total_users || 0}</div>
                    <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>Users</div>
                </div>
            </div>

            <div className="card" style={{ padding: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <div style={{ display: 'flex', gap: '0.75rem' }}>
                        <button className={`btn ${logType === 'telegram_bot' ? 'btn-primary' : 'btn-secondary'}`} style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }} onClick={() => setLogType('telegram_bot')}>Bot Logs</button>
                        <button className={`btn ${logType === 'app' ? 'btn-primary' : 'btn-secondary'}`} style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }} onClick={() => setLogType('app')}>App Logs</button>
                    </div>
                    <button className="btn btn-secondary" style={{ padding: '0.4rem', borderRadius: '50%' }} onClick={fetchLogs}>🔄</button>
                </div>
                <pre
                    ref={logContainerRef}
                    style={{
                        background: 'rgba(0, 0, 0, 0.3)',
                        padding: '1rem',
                        borderRadius: '8px',
                        fontSize: '0.8rem',
                        fontFamily: 'monospace',
                        maxHeight: '300px',
                        overflow: 'auto',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-all',
                        color: 'var(--color-text-secondary)',
                        margin: 0
                    }}
                >
                    {logs || 'No logs available'}
                </pre>
            </div>
        </div>
    );
};

export default Settings;
