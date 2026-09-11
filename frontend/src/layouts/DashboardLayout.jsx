import { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { Map, Activity, AlertTriangle, Layers } from 'lucide-react';
import './DashboardLayout.css';

export default function DashboardLayout() {
  const [year, setYear] = useState(2026);
  const location = useLocation();

  return (
    <div className="layout-container">
      {/* Sidebar Navigation */}
      <nav className="sidebar glass-panel">
        <div className="sidebar-header">
          <h1 className="text-gradient">ThermaCity</h1>
          <p className="subtitle">Pune Heat Crisis Dashboard</p>
        </div>

        <ul className="nav-links">
          <li>
            <Link to="/" className={location.pathname === '/' ? 'active' : ''}>
              <Map size={20} />
              <span>City Heat Map</span>
            </Link>
          </li>
          <li>
            <Link to="/ward/top" className={location.pathname.startsWith('/ward') ? 'active' : ''}>
              <Activity size={20} />
              <span>Ward Rankings</span>
            </Link>
          </li>
          <li>
            <Link to="/report" className={location.pathname === '/report' ? 'active' : ''}>
              <AlertTriangle size={20} />
              <span>Community Reports</span>
            </Link>
          </li>
        </ul>

        <div className="sidebar-actions">
          <button 
            className="btn btn-outline"
            style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
            onClick={async (e) => {
              const btn = e.currentTarget;
              const originalText = btn.innerHTML;
              btn.innerHTML = 'Generating...';
              btn.disabled = true;
              try {
                const { downloadReport } = await import('../services/api');
                await downloadReport(2024); // could be dynamic based on global state
              } catch (err) {
                console.error("Failed to download report", err);
                alert("Failed to generate report");
              } finally {
                btn.innerHTML = originalText;
                btn.disabled = false;
              }
            }}
          >
            <Layers size={18} />
            Export PDF Report
          </button>
        </div>

        <div className="sidebar-footer">
          <div className="legend">
            <h4>Vulnerability Tiers</h4>
            <div className="legend-item"><span className="dot safe"></span> Heat-Safe</div>
            <div className="legend-item"><span className="dot caution"></span> Caution</div>
            <div className="legend-item"><span className="dot stressed"></span> Stressed</div>
            <div className="legend-item"><span className="dot emergency"></span> Emergency</div>
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
