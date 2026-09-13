import { useState } from 'react';
import { Search, Thermometer, Droplets, TreePine, Building2, MapPin, Activity } from 'lucide-react';
import api from '../services/api';
import GlobalNav from '../components/GlobalNav';
import './CompareAreas.css';

export default function CompareAreas() {
  const [q1, setQ1] = useState('Aundh');
  const [q2, setQ2] = useState('Wadgaon Sheri');
  
  const [loc1, setLoc1] = useState(null);
  const [loc2, setLoc2] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, loading, success, error
  const [errorMsg, setErrorMsg] = useState('');

  const fetchArea = async (searchStr) => {
    const geoUrl = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchStr + ', Pune, Maharashtra, India')}&limit=1`;
    const geoRes = await fetch(geoUrl);
    const geoData = await geoRes.json();
    
    if (!geoData || geoData.length === 0) {
      throw new Error(`Location not found in Pune: ${searchStr}`);
    }
    
    const { lat, lon, display_name } = geoData[0];
    const tcRes = await api.get('/grid/locate', {
      params: { lat: parseFloat(lat), lng: parseFloat(lon), year: 2026 }
    });
    
    return {
      name: display_name.split(',').slice(0, 2).join(', '),
      data: tcRes.data
    };
  };

  const handleCompare = async (e) => {
    e.preventDefault();
    if (!q1.trim() || !q2.trim()) return;

    setStatus('loading');
    setErrorMsg('');
    setLoc1(null);
    setLoc2(null);

    try {
      const [res1, res2] = await Promise.all([
        fetchArea(q1),
        fetchArea(q2)
      ]);
      setLoc1(res1);
      setLoc2(res2);
      setStatus('success');
    } catch (err) {
      setStatus('error');
      setErrorMsg(err.message || 'Failed to compare areas.');
    }
  };

  const MetricComparison = ({ label, icon: Icon, val1, val2, suffix, max, invertColor }) => {
    const pct1 = Math.min(100, Math.max(0, (val1 / max) * 100));
    const pct2 = Math.min(100, Math.max(0, (val2 / max) * 100));
    
    const win1 = invertColor ? val1 < val2 : val1 > val2;
    const win2 = invertColor ? val2 < val1 : val2 > val1;

    return (
      <div className="comp-row">
        <div className="comp-label"><Icon size={16} /> {label}</div>
        <div className="comp-bars">
          <div className="comp-bar-group">
            <div className="cb-val">{val1.toFixed(1)}{suffix}</div>
            <div className="cb-track">
              <div className={`cb-fill ${win1 ? 'winner' : ''}`} style={{ width: `${pct1}%` }}></div>
            </div>
          </div>
          <div className="comp-bar-group right">
            <div className="cb-track">
              <div className={`cb-fill ${win2 ? 'winner' : ''}`} style={{ width: `${pct2}%` }}></div>
            </div>
            <div className="cb-val">{val2.toFixed(1)}{suffix}</div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="compare-container">
      <GlobalNav />
      
      <div className="compare-content">
        <div className="section-header">
          <h2>Compare Neighbourhoods</h2>
          <p className="section-desc">See how different areas of Pune experience urban heat.</p>
        </div>

        <form className="compare-form" onSubmit={handleCompare}>
          <div className="compare-inputs">
            <div className="search-input-wrapper">
              <MapPin size={18} className="search-icon" />
              <input 
                type="text" 
                placeholder="Area 1 (e.g. Aundh)" 
                value={q1}
                onChange={(e) => setQ1(e.target.value)}
              />
            </div>
            <div className="vs-badge">VS</div>
            <div className="search-input-wrapper">
              <MapPin size={18} className="search-icon" />
              <input 
                type="text" 
                placeholder="Area 2 (e.g. Hadapsar)" 
                value={q2}
                onChange={(e) => setQ2(e.target.value)}
              />
            </div>
          </div>
          <button type="submit" className="btn btn-primary">Compare Data</button>
        </form>

        {status === 'loading' && (
          <div className="kyh-state">
            <div className="spinner"></div>
            <p>Fetching environmental data for comparison...</p>
          </div>
        )}

        {status === 'error' && (
          <div className="kyh-state">
            <p className="text-emergency">{errorMsg}</p>
          </div>
        )}

        {status === 'success' && loc1 && loc2 && (
          <div className="compare-results">
            <div className="comp-header-row">
              <div className="comp-h-left">
                <h3>{loc1.name}</h3>
                <span className="badge badge-safe">Ward {loc1.data.ward.id}</span>
              </div>
              <div className="comp-h-right">
                <h3>{loc2.name}</h3>
                <span className="badge badge-safe">Ward {loc2.data.ward.id}</span>
              </div>
            </div>

            <div className="comp-metrics-container">
              <MetricComparison 
                label="Urban Heat Index" 
                icon={Activity} 
                val1={loc1.data.features.hvi_score} 
                val2={loc2.data.features.hvi_score} 
                suffix="" max={100} invertColor={true} 
              />
              
              <MetricComparison 
                label="Air/Surface Temp" 
                icon={Thermometer} 
                val1={loc1.data.features.lst_observed} 
                val2={loc2.data.features.lst_observed} 
                suffix="°C" max={50} invertColor={true} 
              />
              
              <MetricComparison 
                label="Vegetation Cover" 
                icon={TreePine} 
                val1={loc1.data.features.ndvi * 100} 
                val2={loc2.data.features.ndvi * 100} 
                suffix="%" max={100} invertColor={false} 
              />

              <MetricComparison 
                label="Built-up Area" 
                icon={Building2} 
                val1={loc1.data.features.ndbi * 100} 
                val2={loc2.data.features.ndbi * 100} 
                suffix="%" max={100} invertColor={true} 
              />

              <MetricComparison 
                label="Water Influence" 
                icon={Droplets} 
                val1={loc1.data.features.ndwi * 100} 
                val2={loc2.data.features.ndwi * 100} 
                suffix="%" max={100} invertColor={false} 
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
