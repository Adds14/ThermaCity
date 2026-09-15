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

  
  const getQualitative = (val, type) => {
    if (type === 'ndvi') {
      if (val < 0.2) return 'Low';
      if (val < 0.4) return 'Moderate';
      return 'High';
    }
    if (type === 'ndbi') {
      if (val < -0.1) return 'Low';
      if (val < 0.1) return 'Moderate';
      return 'High';
    }
    if (type === 'ndwi') {
      if (val < -0.3) return 'Low';
      if (val < 0) return 'Moderate';
      return 'High';
    }
    return '';
  };

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
      setErrorMsg("Area out of Pune, please try other area.");
    }
  };

  
  const MetricComparison = ({ label, icon: Icon, val1, val2, suffix, min = 0, max, invertColor, isIndex, type }) => {
    // For indices, we might range from -1 to +1, so we normalize for the bar width
    const range = max - min;
    const pct1 = Math.min(100, Math.max(0, ((val1 - min) / range) * 100));
    const pct2 = Math.min(100, Math.max(0, ((val2 - min) / range) * 100));
    
    const win1 = invertColor ? val1 < val2 : val1 > val2;
    const win2 = invertColor ? val2 < val1 : val2 > val1;

    const display1 = isIndex ? `(${val1.toFixed(2)}) ${getQualitative(val1, type)}` : `${val1.toFixed(1)}${suffix}`;
    const display2 = isIndex ? `(${val2.toFixed(2)}) ${getQualitative(val2, type)}` : `${val2.toFixed(1)}${suffix}`;

    return (
      <div className="comp-row">
        <div className="comp-label"><Icon size={16} /> {label}</div>
        <div className="comp-bars">
          <div className="comp-bar-group">
            <div className="cb-val">{display1}</div>
            <div className="cb-track">
              <div className={`cb-fill ${win1 ? 'winner' : ''}`} style={{ width: `${pct1}%` }}></div>
            </div>
          </div>
          <div className="comp-bar-group right">
            <div className="cb-track">
              <div className={`cb-fill ${win2 ? 'winner' : ''}`} style={{ width: `${pct2}%` }}></div>
            </div>
            <div className="cb-val">{display2}</div>
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
                label="Heat Vulnerability Index" 
                icon={Activity} 
                val1={loc1.data.features.hvi_score} 
                val2={loc2.data.features.hvi_score} 
                suffix="" min={0} max={100} invertColor={true} 
              />
              
              <MetricComparison 
                label="Land Surface Temp" 
                icon={Thermometer} 
                val1={loc1.data.features.lst_observed} 
                val2={loc2.data.features.lst_observed} 
                suffix="°C" min={30} max={50} invertColor={true} 
              />
              
              <MetricComparison 
                label="Vegetation Condition" 
                icon={TreePine} 
                val1={loc1.data.features.ndvi} 
                val2={loc2.data.features.ndvi} 
                min={-0.2} max={0.8} invertColor={false} isIndex={true} type="ndvi"
              />

              <MetricComparison 
                label="Built-up Intensity" 
                icon={Building2} 
                val1={loc1.data.features.ndbi} 
                val2={loc2.data.features.ndbi} 
                min={-0.4} max={0.6} invertColor={true} isIndex={true} type="ndbi"
              />

              <MetricComparison 
                label="Water Signal" 
                icon={Droplets} 
                val1={loc1.data.features.ndwi} 
                val2={loc2.data.features.ndwi} 
                min={-0.8} max={0.2} invertColor={false} isIndex={true} type="ndwi"
              />
            </div>
            
            <div className="comp-summary" style={{ marginTop: '2rem', padding: '1.5rem', background: 'var(--panel-bg)', borderRadius: '6px', border: '1px solid var(--panel-border)' }}>
              <h4 style={{ marginBottom: '1rem', color: 'var(--text-muted)' }}>WHAT STANDS OUT?</h4>
              <p style={{ lineHeight: 1.6 }}>
                {loc1.name} has a {loc1.data.features.hvi_score > loc2.data.features.hvi_score ? 'higher' : 'lower'} Heat Vulnerability Index than {loc2.name}. 
                The land surface temperature in {loc1.name} is {Math.abs(loc1.data.features.lst_observed - loc2.data.features.lst_observed).toFixed(1)}°C {loc1.data.features.lst_observed > loc2.data.features.lst_observed ? 'hotter' : 'cooler'}. 
                {loc1.data.features.ndvi > loc2.data.features.ndvi ? ` ${loc1.name} shows a stronger vegetation signal` : ` ${loc2.name} shows a stronger vegetation signal`}, while 
                {loc1.data.features.ndbi > loc2.data.features.ndbi ? ` ${loc1.name} has higher built-up intensity.` : ` ${loc2.name} has higher built-up intensity.`}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

