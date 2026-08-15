import { useState, useEffect } from 'react';
import { CheckCircle, ShieldAlert, MapPin, Clock, RefreshCw } from 'lucide-react';
import { fetchUnverifiedReports, verifyReport } from './api';

function App() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    loadReports();
    // Auto-poll every 10 seconds
    const interval = setInterval(() => {
      refreshReports();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadReports = async () => {
    setLoading(true);
    try {
      const data = await fetchUnverifiedReports();
      setReports(data.features || []);
      setError(null);
    } catch (err) {
      console.error(err);
      setError("Failed to load reports. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const refreshReports = async () => {
    setIsRefreshing(true);
    try {
      const data = await fetchUnverifiedReports();
      setReports(data.features || []);
      setError(null);
    } catch (err) {
      console.error(err);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleVerify = async (id) => {
    try {
      await verifyReport(id);
      // Remove from list
      setReports(reports.filter(r => r.properties.id !== id));
    } catch (err) {
      console.error("Verification failed", err);
      alert("Failed to verify report");
    }
  };

  const getSeverityBadge = (severity) => {
    if (severity >= 4) return <span className="badge badge-emergency">Emergency</span>;
    if (severity === 3) return <span className="badge badge-stressed">Stressed</span>;
    return <span className="badge" style={{background: 'rgba(251,191,36,0.15)', color: '#fbbf24', border: '1px solid rgba(251,191,36,0.3)'}}>Caution</span>;
  };

  return (
    <div className="admin-container">
      <header className="admin-header">
        <div>
          <h1>ThermaCity Admin Dashboard</h1>
          <p className="subtitle">Verify crowdsourced heat impact reports before they appear on the public map.</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8' }}>
          <ShieldAlert size={20} />
          <span>Admin Session</span>
        </div>
      </header>

      <main className="dashboard-layout">
        <div className="glass-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
            <h2 style={{ margin: 0, fontSize: '1.2rem' }}>Pending Verifications ({reports.length})</h2>
            <button 
              onClick={refreshReports} 
              disabled={isRefreshing}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                background: 'rgba(255,255,255,0.1)', border: 'none', 
                color: '#fff', padding: '6px 12px', borderRadius: '6px',
                cursor: 'pointer', transition: 'background 0.2s'
              }}
            >
              <RefreshCw size={16} className={isRefreshing ? 'spin' : ''} />
              Refresh
            </button>
          </div>

          {loading ? (
            <div className="empty-state">Loading reports...</div>
          ) : error ? (
            <div className="empty-state" style={{color: '#ef4444'}}>{error}</div>
          ) : reports.length === 0 ? (
            <div className="empty-state">
              <CheckCircle size={48} style={{margin: '0 auto 16px', color: '#10b981', opacity: 0.5}} />
              <h3>All Caught Up!</h3>
              <p>There are no pending reports to verify.</p>
            </div>
          ) : (
            <div className="report-grid">
              {reports.map((report) => {
                const p = report.properties;
                return (
                  <div key={p.id} className="report-card">
                    <div className="report-header">
                      <h3 className="report-category">{p.category.replace(/_/g, ' ')}</h3>
                      {getSeverityBadge(p.severity)}
                    </div>
                    
                    <div className="report-meta">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <MapPin size={14} />
                        <span>{p.ward_name || 'Unknown Ward'} (Cell: {p.cell_code || 'N/A'})</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Clock size={14} />
                        <span>{new Date(p.created_at).toLocaleString()}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>Reporter: {p.reporter_name || 'Anonymous'}</span>
                      </div>
                    </div>

                    <div className="metrics-grid">
                      <div className="metric">
                        <span className="metric-label">Heat</span>
                        <span className="metric-val">{p.heat_impact_rating}/5</span>
                      </div>
                      <div className="metric">
                        <span className="metric-label">Shade</span>
                        <span className="metric-val">{p.shade_rating}/5</span>
                      </div>
                      <div className="metric">
                        <span className="metric-label">Water</span>
                        <span className="metric-val">{p.water_rating}/5</span>
                      </div>
                    </div>

                    {p.description && (
                      <div className="report-desc">
                        "{p.description}"
                      </div>
                    )}

                    <button 
                      className="btn btn-verify" 
                      onClick={() => handleVerify(p.id)}
                    >
                      <CheckCircle size={18} />
                      Verify & Publish
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
