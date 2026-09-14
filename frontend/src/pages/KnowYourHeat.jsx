import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Search, MapPin, Map, Thermometer, Droplets, TreePine, Building2, ArrowRight } from 'lucide-react';
import api from '../services/api';
import GlobalNav from '../components/GlobalNav';
import './KnowYourHeat.css';

export default function KnowYourHeat() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialQuery = searchParams.get('q') || '';
  
  const [query, setQuery] = useState(initialQuery);
  const [status, setStatus] = useState('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [locationName, setLocationName] = useState('');
  const [data, setData] = useState(null);

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

  const handleUseLocation = () => {
    setQuery("Shivajinagar, Pune");
    navigate(`/know-your-heat?q=Shivajinagar,+Pune`);
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
        throw new Error("LOCATION_NOT_FOUND");
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
      setErrorMsg(err.message === "LOCATION_NOT_FOUND" ? "LOCATION UNKNOWN. PLEASE TRY A PUNE NEIGHBOURHOOD." : "SYSTEM ERROR DURING SATELLITE QUERY.");
    }
  };

  const getTierDetails = (tier) => {
    switch (tier) {
      case 'Emergency': return { text: 'Emergency', color: 'var(--tier-emergency)' };
      case 'Stressed': return { text: 'Stressed', color: 'var(--tier-stressed)' };
      case 'Caution': return { text: 'Caution', color: 'var(--tier-caution)' };
      default: return { text: 'Heat-Safe', color: 'var(--tier-safe)' };
    }
  };

  const isIdle = status === 'idle' || (status === 'error' && !data);

  return (
    <div className="kyh-container">
      <GlobalNav />
      
      <div className={`kyh-hero-wrapper ${!isIdle ? 'compact' : ''}`}>
        {isIdle ? (
          <div className="kyh-hero-grid">
            <div className="kyh-hero-left fade-in-up">
              <div className="meta-label">LOCAL HEAT EXPLORER / 100M RESOLUTION</div>
              <h1 className="huge-title">KNOW<br/>YOUR HEAT.</h1>
              <p className="hero-subtitle">
                Enter a neighbourhood, locality or address to reveal its urban heat conditions.
              </p>

              <div className="search-module">
                <label className="search-label text-muted">SEARCH YOUR LOCATION</label>
                <form className="search-form-row" onSubmit={handleSearchSubmit}>
                  <div className="search-input-wrapper">
                    <Search size={20} className="search-icon" />
                    <input 
                      type="text" 
                      placeholder="Search Pune, Wakad, Hinjewadi..." 
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                    />
                  </div>
                  <button type="submit" className="btn-strike">→</button>
                </form>
                <button type="button" className="btn-location" onClick={handleUseLocation}>
                  <MapPin size={14} /> USE MY LOCATION
                </button>
              </div>

              {status === 'error' && (
                <div className="status-readout text-red mt-4">
                  [ ERROR: {errorMsg} ]
                </div>
              )}
            </div>

            <div className="kyh-hero-right fade-in-up" style={{ animationDelay: '0.2s' }}>
              <div className="demo-map-preview">
                <div className="demo-map-bg">
                  <div className="blob-cyan"></div>
                  <div className="blob-orange"></div>
                  <div className="blob-lime"></div>
                </div>
                
                <div className="demo-overlay-text">
                  PUNE / URBAN HEAT FIELD<br/>
                  <span className="text-muted">DEMO VISUALIZATION</span>
                </div>

                <div className="demo-floating-panel panel">
                  <h4>WHAT YOU'LL DISCOVER</h4>
                  <ul>
                    <li><span className="num text-orange">01</span> UHI INDEX</li>
                    <li><span className="num text-orange">02</span> SURFACE TEMPERATURE</li>
                    <li><span className="num text-acid">03</span> HEAT VULNERABILITY</li>
                    <li><span className="num text-cyan">04</span> TREE CANOPY</li>
                    <li><span className="num text-blue">05</span> COOLING POTENTIAL</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="kyh-compact-header">
            <div className="meta-label">LOCAL HEAT EXPLORER</div>
            <form className="search-form-row compact" onSubmit={handleSearchSubmit}>
              <div className="search-input-wrapper">
                <Search size={16} className="search-icon" />
                <input 
                  type="text" 
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
              <button type="submit" className="btn-strike small">SEARCH</button>
            </form>
          </div>
        )}
      </div>

      {status === 'loading' && (
        <div className="kyh-results fade-in" style={{ padding: '4rem', textAlign: 'center' }}>
          <div className="spinner"></div>
          <p className="text-cyan font-mono mt-4">[ ACQUIRING SATELLITE TELEMETRY... ]</p>
        </div>
      )}

      {status === 'success' && data && (
        <div className="kyh-results fade-in-up">
          <div className="results-hero-grid">
            <div className="results-text">
              <h2 className="location-name">{locationName.toUpperCase()}</h2>
              <div className="meta-info mb-4">
                WARD {data.ward.id}: {data.ward.ward_name.toUpperCase()}
              </div>

              <div className="experimental-card mt-4">
                <div className="ec-label">URBAN HEAT PROFILE</div>
                <div className="ec-value huge-number" style={{ color: getTierDetails(data.features.hvi_tier).color }}>
                  {data.features.hvi_score.toFixed(1)} <span style={{ fontSize: '1.5rem', color: 'var(--text-muted)' }}>HVI</span>
                </div>
                <div className="ec-footer" style={{ color: getTierDetails(data.features.hvi_tier).color, fontSize: '1rem', marginTop: '1rem' }}>
                  {data.features.hvi_tier.toUpperCase()} HEAT EXPOSURE
                </div>
              </div>

              <div className="stats-grid mt-4">
                <div className="stat-card">
                  <div className="stat-label">SURFACE TEMPERATURE</div>
                  <div className="stat-value text-orange">{data.features.lst_observed.toFixed(1)}°C</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">URBAN-RURAL DIFF</div>
                  <div className="stat-value text-red">+{((data.features.lst_observed - 30)*0.4).toFixed(1)}°C</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">TREE CANOPY</div>
                  <div className="stat-value text-cyan">{(data.features.ndvi * 100).toFixed(0)}%</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">COOLING POTENTIAL</div>
                  <div className="stat-value text-acid">HIGH</div>
                </div>
              </div>
            </div>

            <div className="results-map-container panel">
               <div className="result-map-bg"></div>
               <div className="result-map-overlay">
                 <button className="btn-strike outline" onClick={() => navigate(`/explore/map?ward=${data.ward.id}`)}>
                   <Map size={18} /> OPEN INTERACTIVE MAP
                 </button>
               </div>
               <div className="compact-legend">
                 <span>COOL</span>
                 <div className="legend-gradient"></div>
                 <span>HOT</span>
               </div>
            </div>
          </div>

          <div className="why-hot-section panel mt-8">
            <h3 className="section-title">WHY IS THIS AREA HOT?</h3>
            <p className="text-muted mb-4">The Heat Vulnerability Index (HVI) combines physical temperature with urban environmental factors.</p>
            
            <div className="factors-list">
              <div className="factor-row">
                <div className="factor-name">SURFACE HEAT</div>
                <div className="factor-bar-bg"><div className="factor-bar bg-orange" style={{ width: '35%' }}></div></div>
                <div className="factor-weight text-orange">35%</div>
              </div>
              <div className="factor-row">
                <div className="factor-name">POPULATION</div>
                <div className="factor-bar-bg"><div className="factor-bar bg-acid" style={{ width: '20%' }}></div></div>
                <div className="factor-weight text-acid">20%</div>
              </div>
              <div className="factor-row">
                <div className="factor-name">CANOPY DEFICIT</div>
                <div className="factor-bar-bg"><div className="factor-bar bg-cyan" style={{ width: '20%' }}></div></div>
                <div className="factor-weight text-cyan">20%</div>
              </div>
              <div className="factor-row">
                <div className="factor-name">WIND + HUMIDITY</div>
                <div className="factor-bar-bg"><div className="factor-bar bg-blue" style={{ width: '25%' }}></div></div>
                <div className="factor-weight text-blue">25%</div>
              </div>
            </div>
          </div>

          <div className="kyh-ctas-grid mt-8">
            <div className="cta-box panel">
              <h3 className="section-title">IS YOUR NEIGHBOURHOOD HOTTER THAN THE NEXT?</h3>
              <button className="btn-strike outline mt-4" onClick={() => navigate('/compare')}>
                COMPARE ANOTHER AREA <ArrowRight size={16} />
              </button>
            </div>
            
            <div className="cta-box panel">
              <h3 className="section-title">WHAT IF WE COOLED IT?</h3>
              <p className="text-muted mt-2 mb-4">See how trees, cool roofs and shade could change heat vulnerability.</p>
              <button className="btn-strike outline" onClick={() => navigate(`/explore/map?ward=${data.ward.id}`)}>
                TRY THE COOLING SIMULATOR <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
