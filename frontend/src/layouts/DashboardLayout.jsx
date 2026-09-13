import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { Map, Activity, AlertTriangle, Layers, MapPin } from 'lucide-react';
import './DashboardLayout.css';
import api from '../services/api';

export default function DashboardLayout() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <div className="layout-container">
      {/* Sidebar Navigation */}
      <nav className="sidebar">
        <div className="sidebar-header" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          <h1 className="text-gradient">
            <Layers className="logo-icon" size={20} /> THERMACITY
          </h1>
        </div>

        <div className="sidebar-section">
          <h3 className="section-label">EXPLORE</h3>
          <ul className="nav-links">
            <li>
              <Link to="/explore/map" className={location.pathname === '/explore/map' ? 'active' : ''}>
                <Map size={20} />
                <span>City Heat Map</span>
              </Link>
            </li>
            <li>
              <Link to="/explore/rankings" className={location.pathname.startsWith('/explore/rankings') ? 'active' : ''}>
                <Activity size={20} />
                <span>Ward Rankings</span>
              </Link>
            </li>
            <li>
              <Link to="/explore/reports" className={location.pathname === '/explore/reports' ? 'active' : ''}>
                <AlertTriangle size={20} />
                <span>Community Reports</span>
              </Link>
            </li>
          </ul>
        </div>

        <div className="sidebar-section">
          <h3 className="section-label">YOUR LOCATION</h3>
          <div className="your-location-card">
            <p>Discover your local heat risk.</p>
            <button className="btn-primary btn-sm" onClick={() => navigate('/know-your-heat')}>
              <MapPin size={16} /> Know Your Heat
            </button>
          </div>
        </div>

        <div className="sidebar-spacer"></div>

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
                // Fetch the latest year PDF
                await api.downloadReport(2026);
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
