import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Map } from 'lucide-react';
import './WardRankings.css';

export default function WardRankings() {
  const [wards, setWards] = useState([]);
  const [loading, setLoading] = useState(true);

  // Mock data until PostGIS API is accessible
  useEffect(() => {
    let active = true;
    const loadWards = async () => {
      try {
        const { fetchWardSummary } = await import('../../services/api');
        const data = await fetchWardSummary(2026);
        if (active) {
          // data format from api: ward_id, ward_name, avg_hvi, hvi_tier, cell_count, avg_lst
          setWards(data.map((w, index) => ({
            id: w.ward_id,
            name: w.ward_name,
            avg_hvi: w.avg_hvi,
            pop_density: 25000, // DB doesn't pass pop_density right now in the mapper
            emergency_cells: w.hvi_tier === 'Emergency' || w.hvi_tier === 'Stressed' ? Math.floor(w.cell_count * 0.1) : 0
          })));
          setLoading(false);
        }
      } catch (err) {
        console.error("Failed to fetch ward rankings:", err);
        if (active) setLoading(false);
      }
    };
    loadWards();
    return () => { active = false; };
  }, []);

  const getTierClass = (score) => {
    if (score >= 75) return 'badge-emergency';
    if (score >= 50) return 'badge-stressed';
    if (score >= 25) return 'badge-caution';
    return 'badge-safe';
  };

  const getTierText = (score) => {
    if (score >= 75) return 'Emergency';
    if (score >= 50) return 'Stressed';
    if (score >= 25) return 'Caution';
    return 'Safe';
  };

  if (loading) {
    return <div className="loading-state">Loading ward analytics...</div>;
  }

  return (
    <div className="ward-rankings-container animate-slide-in">
      <header className="page-header">
        <h2>Ward Vulnerability Rankings</h2>
        <p className="subtitle">Prioritize resource allocation (tankers, cooling centers) based on aggregate Heat Vulnerability Index.</p>
      </header>

      <div className="rankings-table-wrapper glass-panel">
        <table className="rankings-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Ward Name</th>
              <th>Avg HVI (0-100)</th>
              <th>Status</th>
              <th>Emergency Cells</th>
              <th>Pop. Density (/sq km)</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {wards.map((ward, index) => (
              <tr key={ward.id} className={index < 2 ? 'critical-row' : ''}>
                <td className="rank-col">#{index + 1}</td>
                <td className="name-col">{ward.name}</td>
                <td className="score-col">
                  <div className="score-bar-bg">
                    <div 
                      className={`score-bar-fill ${getTierClass(ward.avg_hvi).replace('badge-', 'bg-')}`}
                      style={{ width: `${ward.avg_hvi}%` }}
                    />
                  </div>
                  <span>{ward.avg_hvi.toFixed(1)}</span>
                </td>
                <td>
                  <span className={`badge ${getTierClass(ward.avg_hvi)}`}>
                    {getTierText(ward.avg_hvi)}
                  </span>
                </td>
                <td className={ward.emergency_cells > 20 ? 'text-emergency font-bold' : ''}>
                  {ward.emergency_cells}
                </td>
                <td>{ward.pop_density.toLocaleString()}</td>
                <td>
                  <Link to={`/?ward=${ward.id}`} className="btn btn-primary btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                    <Map size={14} /> View Map
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
