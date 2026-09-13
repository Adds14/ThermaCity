import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Search, MapPin, Map, Thermometer, Droplets, TreePine, Building2 } from 'lucide-react';
import api from '../services/api';
import GlobalNav from '../components/GlobalNav';
import './KnowYourHeat.css';

export default function KnowYourHeat() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialQuery = searchParams.get('q') || '';
  
  const [query, setQuery] = useState(initialQuery);
  const [status, setStatus] = useState('idle'); // idle, loading, error, success
  const [errorMsg, setErrorMsg] = useState('');
  const [locationName, setLocationName] = useState('');
  const [data, setData] = useState(null);
  const [cityAvg] = useState(33.5); // Mocked city avg for now

  useEffect(() => {
    if (initialQuery) {
      performSearch(initialQuery);
    }
  }, [initialQuery]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      navigate(`/know-your-heat?q=${encodeURIComponent(query)}`);
    }
  };

  const performSearch = async (searchStr) => {
    setStatus('loading');
    setErrorMsg('');
    setData(null);
    
    try {
      const geoUrl = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchStr + ', Pune, Maharashtra, India')}&limit=1`;
      
      const geoRes = await fetch(geoUrl);
      const geoData = await geoRes.json();
      
      if (!geoData || geoData.length === 0) {
        throw new Error("We couldn't find this location in Pune. Please try a different area or address.");
      }
      
      const { lat, lon, display_name } = geoData[0];
      const shortName = display_name.split(',').slice(0, 2).join(', ');
      setLocationName(shortName);

      const tcRes = await api.get('/grid/locate', {
        params: { lat: parseFloat(lat), lng: parseFloat(lon), year: 2026 }
      });
      
      setData(tcRes.data);
      setStatus('success');
    } catch (err) {
      console.error(err);
      setStatus('error');
      setErrorMsg(err.response?.data?.detail || err.message || "An error occurred.");
    }
  };

  const getTierDetails = (tier) => {
    switch (tier) {
      case 'Emergency': return { text: 'Emergency', cls: 'badge-emergency' };
      case 'Stressed': return { text: 'Stressed', cls: 'badge-stressed' };
      case 'Caution': return { text: 'Caution', cls: 'badge-caution' };
      default: return { text: 'Heat-Safe', cls: 'badge-safe' };
    }
  };

  return (
    <div className="kyh-container">
      <GlobalNav />

      <div className="kyh-content">
        <div className="kyh-header-compact">
          <div className="khy-titles">
            <h1>Know the UHI at your place</h1>
            <p>Enter a neighbourhood, locality or address to explore its urban heat conditions.</p>
          </div>
          <form className="hero-search-form" onSubmit={handleSearchSubmit}>
            <div className="search-input-wrapper">
              <Search size={18} className="search-icon" />
              <input 
                type="text" 
                placeholder="Search Pune locality or address..." 
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <button type="submit" className="btn btn-primary">Search</button>
          </form>
        </div>

        {status === 'loading' && (
          <div className="kyh-state">
            <div className="spinner"></div>
            <p>Analyzing environmental data...</p>
          </div>
        )}

        {status === 'error' && (
          <div className="kyh-state">
            <p className="text-emergency">{errorMsg}</p>
          </div>
        )}

        {status === 'success' && data && (
          <div className="kyh-dashboard">
            <div className="dashboard-header">
              <div className="dh-left">
                <span className="section-label">YOUR AREA</span>
                <h2>{locationName}</h2>
                <div className="dh-meta">
                  <MapPin size={14} /> Ward {data.ward.id}: {data.ward.ward_name} (100×100m grid cell)
                </div>
              </div>
              <div className="dh-right">
                <button onClick={() => navigate('/explore/map')} className="btn btn-outline btn-sm">
                  <Map size={14} /> View on Map
                </button>
              </div>
            </div>

            <div className="dashboard-grid">
              
              {/* Primary Metric */}
              <div className="primary-metric-box">
                <span className="section-label">Urban Heat Index</span>
                <div className="hvi-big-value">
                  {data.features.hvi_score.toFixed(1)} <span className="max-val">/ 100</span>
                </div>
                <div className="hvi-tier-badge">
                  <span className={`badge ${getTierDetails(data.features.hvi_tier).cls}`}>
                    {data.features.hvi_tier.toUpperCase()}
                  </span>
                </div>
                
                <div className="comparison-stat">
                  <span className="text-muted">Compared with Pune average:</span>
                  <strong className={data.features.hvi_score > cityAvg ? 'text-emergency' : 'text-safe'}>
                    {data.features.hvi_score > cityAvg ? '+' : ''}
                    {(data.features.hvi_score - cityAvg).toFixed(1)} points
                  </strong>
                </div>
              </div>

              {/* Data Breakdown */}
              <div className="data-breakdown">
                <span className="section-label">Environmental Factors</span>
                
                <div className="factor-bar-row">
                  <div className="fb-label">
                    <Thermometer size={16} /> Air/Surface Temp
                  </div>
                  <div className="fb-bar-container">
                    <div className="fb-bar bg-stressed" style={{ width: `${(data.features.lst_observed / 50) * 100}%` }}></div>
                  </div>
                  <div className="fb-value">{data.features.lst_observed.toFixed(1)}°C</div>
                </div>

                <div className="factor-bar-row">
                  <div className="fb-label">
                    <Building2 size={16} /> Built-up Coverage
                  </div>
                  <div className="fb-bar-container">
                    <div className="fb-bar" style={{ background: 'var(--color-built)', width: `${Math.max(0, data.features.ndbi) * 100}%` }}></div>
                  </div>
                  <div className="fb-value">{(Math.max(0, data.features.ndbi) * 100).toFixed(0)}%</div>
                </div>

                <div className="factor-bar-row">
                  <div className="fb-label">
                    <TreePine size={16} /> Vegetation Coverage
                  </div>
                  <div className="fb-bar-container">
                    <div className="fb-bar" style={{ background: 'var(--color-veg)', width: `${Math.max(0, data.features.ndvi) * 100}%` }}></div>
                  </div>
                  <div className="fb-value">{(Math.max(0, data.features.ndvi) * 100).toFixed(0)}%</div>
                </div>

                <div className="factor-bar-row">
                  <div className="fb-label">
                    <Droplets size={16} /> Water Presence
                  </div>
                  <div className="fb-bar-container">
                    <div className="fb-bar" style={{ background: 'var(--color-water)', width: `${Math.max(0, data.features.ndwi) * 100}%` }}></div>
                  </div>
                  <div className="fb-value">{(Math.max(0, data.features.ndwi) * 100).toFixed(0)}%</div>
                </div>

              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
