import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Map, Filter } from 'lucide-react';
import './WardRankings.css';

export default function WardRankings() {
  const [wards, setWards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterTier, setFilterTier] = useState('All');
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;
    const loadWards = async () => {
      try {
        const { fetchWardSummary } = await import('../../services/api');
        const data = await fetchWardSummary(2026);
        if (active) {
          const sorted = data.sort((a, b) => b.avg_hvi - a.avg_hvi).map((w) => ({
            id: w.ward_id,
            name: w.ward_name,
            avg_hvi: w.avg_hvi,
            pop_density: w.avg_pop_density,
            tier: w.avg_hvi >= 75 ? 'Emergency' : w.avg_hvi >= 50 ? 'Stressed' : w.avg_hvi >= 25 ? 'Caution' : 'Heat-Safe',
            emergency_cells: w.hvi_tier === 'Emergency' || w.hvi_tier === 'Stressed' ? Math.floor(w.cell_count * 0.1) : 0
          }));
          setWards(sorted);
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

  const getTierClass = (tier) => {
    switch (tier) {
      case 'Emergency': return 'badge-emergency';
      case 'Stressed': return 'badge-stressed';
      case 'Caution': return 'badge-caution';
      default: return 'badge-safe';
    }
  };

  const distribution = useMemo(() => {
    const dist = { 'Heat-Safe': 0, 'Caution': 0, 'Stressed': 0, 'Emergency': 0 };
    wards.forEach(w => {
      dist[w.tier] = (dist[w.tier] || 0) + 1;
    });
    return dist;
  }, [wards]);

  const filteredWards = useMemo(() => {
    if (filterTier === 'All') return wards;
    return wards.filter(w => w.tier === filterTier);
  }, [wards, filterTier]);

  const highestRisk = wards.length > 0 ? wards[0] : null;
  const totalEmergency = wards.reduce((acc, curr) => acc + curr.emergency_cells, 0);

  if (loading) {
    return <div className="loading-state">Loading ward analytics...</div>;
  }

  return (
    <div className="ward-rankings panel">
      <div className="wr-header">
        <h2>Ward Heat Vulnerability</h2>
        <div className="wr-stats">
          <span>{wards.length} wards analyzed</span>
          <span>• Ranked by average Heat Vulnerability Index across each ward</span>
        </div>
        <p style={{ marginTop: '0.5rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
          A ward's score is an aggregate of the underlying 100×100m analysis cells within that ward.
        </p>
      </div>
      <div className="summary-cards">
        {highestRisk && (
          <div className="summary-card danger">
            <span className="sc-label">HIGHEST RISK</span>
            <span className="sc-value">{highestRisk.name}</span>
            <span className="sc-sub">HVI {highestRisk.avg_hvi.toFixed(1)}</span>
          </div>
        )}
        <div className="summary-card warning">
          <span className="sc-label">EMERGENCY CELLS</span>
          <span className="sc-value">{totalEmergency.toLocaleString()}</span>
          <span className="sc-sub">City-wide</span>
        </div>
      </div>

      <div className="distribution-section panel">
        <h3>HVI Distribution</h3>
        <div className="dist-bars">
          {Object.entries(distribution).map(([tier, count]) => {
            const pct = (count / Math.max(1, wards.length)) * 100;
            return (
              <div key={tier} className="dist-row">
                <span className="dist-label">{tier}</span>
                <div className="dist-bar-wrapper">
                  <div className={`dist-bar ${getTierClass(tier).replace('badge-', 'bg-')}`} style={{ width: `${pct}%` }}></div>
                </div>
                <span className="dist-count">{count}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="table-controls">
        <div className="filters">
          <Filter size={16} />
          {['All', 'Heat-Safe', 'Caution', 'Stressed', 'Emergency'].map(t => (
            <button 
              key={t}
              className={`filter-btn ${filterTier === t ? 'active' : ''}`}
              onClick={() => setFilterTier(t)}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="rankings-table-wrapper panel">
        <table className="rankings-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Ward Name</th>
              <th>Avg HVI (0-100)</th>
              <th>Status</th>
              <th>Emergency Cells</th>
              <th>Pop. Density (/km²)</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredWards.map((ward, index) => (
              <tr key={ward.id}>
                <td className="rank-col">#{wards.findIndex(w => w.id === ward.id) + 1}</td>
                <td className="name-col">{ward.name}</td>
                <td className="score-col">
                  <div className="score-bar-bg">
                    <div 
                      className={`score-bar-fill ${getTierClass(ward.tier).replace('badge-', 'bg-')}`}
                      style={{ width: `${ward.avg_hvi}%` }}
                    />
                  </div>
                  <span>{ward.avg_hvi.toFixed(1)}</span>
                </td>
                <td>
                  <span className={`badge ${getTierClass(ward.tier)}`}>
                    {ward.tier}
                  </span>
                </td>
                <td className={ward.emergency_cells > 20 ? 'text-emergency font-bold' : ''}>
                  {ward.emergency_cells}
                </td>
                <td>{(ward.pop_density ?? 0).toLocaleString()}</td>
                <td>
                  <button onClick={() => navigate(`/explore/map?ward=${ward.id}`)} className="btn btn-outline btn-sm">
                    <Map size={14} /> View Map
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {filteredWards.length === 0 && (
          <div className="empty-state">No wards found for this status tier.</div>
        )}
      </div>
    </div>
  );
}
