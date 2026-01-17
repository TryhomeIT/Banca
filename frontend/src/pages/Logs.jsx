import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const Logs = () => {
    const navigate = useNavigate();
    const [logType, setLogType] = useState('app');
    const [logs, setLogs] = useState('');
    const [loading, setLoading] = useState(true);
    const [autoRefresh, setAutoRefresh] = useState(false);
    const logEndRef = useRef(null);

    const fetchLogs = async () => {
        try {
            const response = await api.get(`/admin/logs?type=${logType}&lines=500`);
            setLogs(response.data.logs);
        } catch (error) {
            console.error('Failed to fetch logs:', error);
            setLogs('Error loading logs. Make sure you are an admin and the backend is running.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLogs();
    }, [logType]);

    useEffect(() => {
        let interval;
        if (autoRefresh) {
            interval = setInterval(fetchLogs, 3000);
        }
        return () => clearInterval(interval);
    }, [autoRefresh, logType]);

    useEffect(() => {
        if (logEndRef.current) {
            logEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [logs]);

    return (
        <div className="container" style={{ padding: '2rem 1.5rem', height: '100vh', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <div className="header-content" style={{ marginBottom: '1.5rem', flexShrink: 0 }}>
                <div className="header-left" style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                    <button className="btn btn-secondary" onClick={() => navigate('/settings')}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M19 12H5M12 19l-7-7 7-7" />
                        </svg>
                        Back
                    </button>
                    <h1>System Logs</h1>
                    <div className="category-tabs" style={{ marginBottom: 0, paddingBottom: 0 }}>
                        <button
                            className={`category-tab ${logType === 'app' ? 'active' : ''}`}
                            onClick={() => setLogType('app')}
                        >
                            🚀 App Server
                        </button>
                        <button
                            className={`category-tab ${logType === 'telegram_bot' ? 'active' : ''}`}
                            onClick={() => setLogType('telegram_bot')}
                        >
                            🤖 Telegram Bot
                        </button>
                    </div>
                    <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.9rem' }}>
                            <input
                                type="checkbox"
                                checked={autoRefresh}
                                onChange={(e) => setAutoRefresh(e.target.checked)}
                                style={{ width: 'auto' }}
                            />
                            Auto-refresh
                        </label>
                        <button className="btn btn-secondary" onClick={fetchLogs} disabled={loading}>
                            Refresh Now
                        </button>
                    </div>
                </div>
            </div>

            {/* Logs Console */}
            <div className="card" style={{
                flex: 1,
                backgroundColor: '#0d1117',
                color: '#e6edf3',
                padding: '1.5rem',
                fontFamily: 'monospace',
                fontSize: '0.85rem',
                lineHeight: '1.5',
                overflowY: 'auto',
                position: 'relative',
                border: '1px solid #30363d',
                borderRadius: '8px'
            }}>
                {loading && !logs ? (
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                        <div className="loading-spinner"></div>
                    </div>
                ) : (
                    <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', margin: 0 }}>
                        {logs || 'No log entries found.'}
                        <div ref={logEndRef} />
                    </pre>
                )}
            </div>
        </div>
    );
};

export default Logs;
