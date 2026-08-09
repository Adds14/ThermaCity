import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Map } from 'lucide-react';
import './WardRankings.css';

export default function WardRankings() {
  const [wards, setWards] = useState([]);
  const [loading, setLoading] = useState(true);

  // Mock data until PostGIS API is accessible
  useEffect(() => {
    setTimeout(() => {
      setWards([
        { id: 1, name: 'Bhavani Peth', avg_hvi: 84.5, pop_density: 35000, emergency_cells: 45 },
        { id: 2, name: 'Kasba-Vishrambaug Wada', avg_hvi: 81.2, pop_density: 42000, emergency_cells: 38 },
        { id: 3, name: 'Shivajinagar-Ghole Road', avg_hvi: 76.8, pop_density: 28000, emergency_cells: 21 },
        { id: 4, name: 'Dhole Patil Road', avg_hvi: 71.3, pop_density: 22000, emergency_cells: 18 },
        { id: 5, name: 'Yerawada-Kalas-Dhanori', avg_hvi: 68.9, pop_density: 29000, emergency_cells: 15 },
        { id: 6, name: 'Hadapsar-Mundhwa', avg_hvi: 65.4, pop_density: 31000, emergency_cells: 12 },
        { id: 7, name: 'Nagar Road-Vadgaon Sheri', avg_hvi: 64.1, pop_density: 26000, emergency_cells: 10 },
        { id: 8, name: 'Kothrud-Bavdhan', avg_hvi: 62.4, pop_density: 25000, emergency_cells: 5 },
        { id: 9, name: 'Warje-Karvenagar', avg_hvi: 59.7, pop_density: 23000, emergency_cells: 3 },
        { id: 10, name: 'Dhankawadi-Sahakarnagar', avg_hvi: 58.2, pop_density: 30000, emergency_cells: 2 },
        { id: 11, name: 'Wanawadi-Ramtekdi', avg_hvi: 57.5, pop_density: 21000, emergency_cells: 1 },
        { id: 12, name: 'Kondhwa-Yewalewadi', avg_hvi: 56.1, pop_density: 19000, emergency_cells: 1 },
        { id: 13, name: 'Sinhagad Road', avg_hvi: 55.8, pop_density: 24000, emergency_cells: 0 },
        { id: 14, name: 'Aundh-Baner', avg_hvi: 55.1, pop_density: 18000, emergency_cells: 0 },
        { id: 15, name: 'Bibwewadi', avg_hvi: 53.4, pop_density: 27000, emergency_cells: 0 },
      ]);
      setLoading(false);
    }, 800);
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
                  <Link to="/" className="btn btn-primary btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
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
