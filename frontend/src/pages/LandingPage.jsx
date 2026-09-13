import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Map, Thermometer, Droplets, TreePine, Building2, TrendingUp, Sun, Activity, Users, Home } from 'lucide-react';
import GlobalNav from '../components/GlobalNav';
import './LandingPage.css';

export default function LandingPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/know-your-heat?q=${encodeURIComponent(searchQuery)}`);
    }
  };

  return (
    <div className="landing-container">
      <GlobalNav />

      {/* ── 1. HERO SECTION ── */}
      <section className="hero-section">
        <div className="hero-content">
          <div className="hero-tag">ThermaCity</div>
          <h1 className="hero-title">Understanding Urban Heat in Pune</h1>
          <p className="hero-subtitle">
            Urban heat is not distributed evenly across a city. ThermaCity helps you explore how built-up surfaces, vegetation, water, temperature and local conditions influence heat at the neighbourhood level.
          </p>
          
          <div className="hero-search-box">
            <h3>KNOW THE UHI AT YOUR PLACE</h3>
            <form className="hero-search-form" onSubmit={handleSearch}>
              <div className="search-input-wrapper">
                <Search size={18} className="search-icon" />
                <input 
                  type="text" 
                  placeholder="Search your area, locality or address..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <button type="submit" className="btn btn-primary">Explore Heat</button>
            </form>
            <div className="popular-areas">
              <span>Popular areas:</span>
              <button onClick={() => navigate('/know-your-heat?q=Wakad')}>Wakad</button>
              <button onClick={() => navigate('/know-your-heat?q=Baner')}>Baner</button>
              <button onClick={() => navigate('/know-your-heat?q=Kothrud')}>Kothrud</button>
              <button onClick={() => navigate('/know-your-heat?q=Aundh')}>Aundh</button>
              <button onClick={() => navigate('/know-your-heat?q=Hadapsar')}>Hadapsar</button>
            </div>
          </div>
        </div>
        
        {/* Abstract Data Visualization Background */}
        <div className="hero-visual">
          <div className="data-grid">
            {Array.from({ length: 64 }).map((_, i) => (
              <div 
                key={i} 
                className="grid-cell"
                style={{
                  opacity: Math.random() * 0.5 + 0.1,
                  backgroundColor: Math.random() > 0.7 ? 'var(--tier-stressed)' : (Math.random() > 0.4 ? 'var(--tier-caution)' : 'var(--tier-safe)')
                }}
              />
            ))}
          </div>
        </div>
      </section>

      {/* ── 2. WHAT IS UHI? ── */}
      <section className="editorial-section border-top">
        <div className="section-header">
          <h2>What is the Urban Heat Island effect?</h2>
          <p className="section-desc">
            Urban areas can become warmer than their surrounding areas because roads, buildings, concrete and other built surfaces absorb and retain heat. Vegetation and water can reduce this effect through shade, evapotranspiration and cooling.
          </p>
        </div>
        
        <div className="uhi-diagram">
          <div className="uhi-side cool-side">
            <h4>COOLER ENVIRONMENT</h4>
            <div className="uhi-visual"><TreePine size={48} strokeWidth={1.5} /></div>
            <p><strong>Vegetation / Open Space</strong></p>
            <ul>
              <li>More shade</li>
              <li>Evapotranspiration</li>
              <li>Lower heat retention</li>
            </ul>
          </div>
          
          <div className="uhi-arrow">
            <TrendingUp size={32} />
          </div>

          <div className="uhi-side hot-side">
            <h4>URBAN SURFACES</h4>
            <div className="uhi-visual"><Building2 size={48} strokeWidth={1.5} /></div>
            <p><strong>Buildings / Roads / Concrete</strong></p>
            <ul>
              <li>Absorb solar radiation</li>
              <li>Store heat</li>
              <li>Release heat after sunset</li>
            </ul>
          </div>
        </div>
      </section>

      {/* ── 3. WHY IT MATTERS ── */}
      <section className="editorial-section border-top bg-alt">
        <div className="section-header">
          <h2>Why does urban heat matter?</h2>
        </div>
        <div className="impact-grid">
          <div className="impact-block">
            <Users size={24} className="impact-icon text-caution" />
            <h4>1. Human comfort</h4>
            <p>Higher surface and air temperatures make outdoor environments less comfortable and reduce livability.</p>
          </div>
          <div className="impact-block">
            <Activity size={24} className="impact-icon text-emergency" />
            <h4>2. Public health</h4>
            <p>Extreme heat can increase heat-related health risks, particularly for vulnerable populations and outdoor workers.</p>
          </div>
          <div className="impact-block">
            <Sun size={24} className="impact-icon text-stressed" />
            <h4>3. Energy demand</h4>
            <p>Hotter neighbourhoods can increase cooling requirements and electricity demand during summer months.</p>
          </div>
          <div className="impact-block">
            <Map size={24} className="impact-icon text-safe" />
            <h4>4. Urban environment</h4>
            <p>Areas with less vegetation and more impervious surfaces can retain heat for longer, compounding the effect.</p>
          </div>
        </div>
      </section>

      {/* ── 4. WHAT SHAPES HEAT? ── */}
      <section className="editorial-section border-top">
        <div className="section-header">
          <h2>What shapes heat in a neighbourhood?</h2>
          <p className="section-desc">ThermaCity measures these major environmental factors to estimate vulnerability.</p>
        </div>
        
        <div className="factors-list">
          <div className="factor-row">
            <div className="f-icon"><Thermometer size={28} /></div>
            <div className="f-content">
              <h4>TEMPERATURE</h4>
              <p>How warm is the area? We look at Land Surface Temperature (LST) derived from satellite thermal sensors.</p>
            </div>
          </div>
          <div className="factor-row">
            <div className="f-icon text-safe"><TreePine size={28} /></div>
            <div className="f-content">
              <h4>VEGETATION</h4>
              <p>How much cooling vegetation is present? Measured using the Normalized Difference Vegetation Index (NDVI).</p>
            </div>
          </div>
          <div className="factor-row">
            <div className="f-icon text-muted"><Building2 size={28} /></div>
            <div className="f-content">
              <h4>BUILT-UP AREA</h4>
              <p>How much of the landscape is covered by buildings and hard surfaces? Measured using NDBI.</p>
            </div>
          </div>
          <div className="factor-row">
            <div className="f-icon text-accent"><Droplets size={28} /></div>
            <div className="f-content">
              <h4>WATER</h4>
              <p>Where are cooling water bodies located? Measured using the Normalized Difference Water Index (NDWI).</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── 5. METHODOLOGY ── */}
      <section className="editorial-section border-top bg-alt">
        <div className="section-header">
          <h2>How is the Urban Heat Index calculated?</h2>
          <p className="section-desc">
            The index combines multiple environmental indicators to estimate relative urban heat conditions across neighbourhoods. It is a normalized score (0-100) representing relative vulnerability, not an absolute temperature.
          </p>
        </div>
        
        <div className="methodology-diagram">
          <div className="math-box">Temperature</div>
          <div className="math-op">+</div>
          <div className="math-box">Built-up intensity</div>
          <div className="math-op">+</div>
          <div className="math-box">Vegetation deficit</div>
          <div className="math-op">+</div>
          <div className="math-box">Water / cooling influence</div>
          <div className="math-arrow">↓</div>
          <div className="math-result bg-stressed text-main">Urban Heat Index</div>
        </div>
      </section>

      {/* ── 6. DATA TO ACTION ── */}
      <section className="editorial-section border-top">
        <div className="section-header">
          <h2>From Data to Action</h2>
        </div>
        
        <div className="personas-grid">
          <div className="persona-block">
            <Home className="p-icon" />
            <h4>FOR RESIDENTS</h4>
            <p>Understand how hot your neighbourhood is compared to the city average.</p>
          </div>
          <div className="persona-block">
            <Users className="p-icon" />
            <h4>FOR STUDENTS</h4>
            <p>Explore and learn about urban climate patterns using real environmental data.</p>
          </div>
          <div className="persona-block">
            <Activity className="p-icon" />
            <h4>FOR RESEARCHERS</h4>
            <p>Use neighbourhood-level environmental indicators for urban studies.</p>
          </div>
          <div className="persona-block">
            <Map className="p-icon" />
            <h4>FOR PLANNERS</h4>
            <p>Identify areas that may benefit from cooling interventions and urban forestry.</p>
          </div>
        </div>
      </section>

      <footer className="editorial-footer">
        <div className="footer-content">
          <h2>Ready to explore Pune's climate data?</h2>
          <div className="footer-actions">
            <button className="btn btn-primary" onClick={() => navigate('/explore/map')}>Explore Heat Map</button>
            <button className="btn btn-outline" onClick={() => navigate('/compare')}>Compare Areas</button>
          </div>
        </div>
      </footer>
    </div>
  );
}
