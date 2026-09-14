import { Link } from 'react-router-dom';
import { ArrowRight, Activity, ThermometerSun, Map as MapIcon } from 'lucide-react';
import './LandingPage.css';

export default function LandingPage() {
  return (
    <div className="landing-container">
      {/* Background Heat Field (CSS animated) */}
      <div className="bg-heat-field">
        <div className="heat-blob blob-1"></div>
        <div className="heat-blob blob-2"></div>
        <div className="heat-blob blob-3"></div>
      </div>

      <div className="hero-section">
        <div className="hero-content">
          <div className="hero-brand">THERMACITY</div>
          <h1 className="huge-title">
            YOUR CITY<br />
            IS HEATING<br />
            <span className="text-orange">UP.</span>
          </h1>
          <p className="hero-subtitle">
            Understand the heat vulnerability where you live through high-resolution satellite imagery and deterministic modeling.
          </p>
          <Link to="/know-your-heat" className="btn-explore">
            EXPLORE YOUR AREA <ArrowRight size={20} />
          </Link>
        </div>
        
        <div className="hero-visual">
          <div className="experimental-card">
            <div className="ec-label">AVG HEAT VULNERABILITY</div>
            <div className="ec-value huge-number">38.4</div>
            <div className="ec-scale">
              <div className="ec-bar" style={{ width: '38.4%' }}></div>
            </div>
            <div className="ec-footer text-acid">ELEVATED EXPOSURE DETECTED</div>
          </div>
        </div>
      </div>

      <div className="data-journalism-section">
        <div className="dj-header">
          <h2>THE SCIENCE OF URBAN HEAT</h2>
        </div>
        
        <div className="dj-grid">
          <div className="dj-card panel">
            <div className="dj-icon"><ThermometerSun size={24} className="text-orange"/></div>
            <h3>Land Surface Temp (LST)</h3>
            <p>Our ML model predicts surface temperatures across a 100×100m grid using Landsat & Sentinel-2 satellite data, capturing micro-heat islands.</p>
          </div>
          
          <div className="dj-card panel">
            <div className="dj-icon"><Activity size={24} className="text-acid"/></div>
            <h3>Human Vulnerability</h3>
            <p>Temperature alone doesn't equal risk. We combine LST with population density, tree canopy deficit, and humidity to calculate true exposure.</p>
          </div>

          <div className="dj-card panel">
            <div className="dj-icon"><MapIcon size={24} className="text-cyan"/></div>
            <h3>Actionable Simulation</h3>
            <p>Model cooling interventions like tree planting and cool roofs in real-time to see their predicted impact on local heat vulnerability.</p>
          </div>
        </div>
      </div>

      <div className="methodology-section panel">
        <div className="meth-header">
          <h4 className="text-muted">METHODOLOGY</h4>
          <h2>How HVI is Calculated</h2>
        </div>
        
        <div className="formula-display">
          <div className="formula-part text-orange">
            <span className="fp-val">35%</span>
            <span className="fp-lbl">SURFACE HEAT</span>
          </div>
          <div className="formula-op">+</div>
          <div className="formula-part text-acid">
            <span className="fp-val">20%</span>
            <span className="fp-lbl">POPULATION</span>
          </div>
          <div className="formula-op">+</div>
          <div className="formula-part text-cyan">
            <span className="fp-val">20%</span>
            <span className="fp-lbl">CANOPY DEFICIT</span>
          </div>
          <div className="formula-op">+</div>
          <div className="formula-part text-blue">
            <span className="fp-val">25%</span>
            <span className="fp-lbl">WIND & HUMIDITY</span>
          </div>
          <div className="formula-arrow">→</div>
          <div className="formula-result">
            <span className="fp-val text-main">HVI</span>
            <span className="fp-lbl">0–100 SCORE</span>
          </div>
        </div>
      </div>
      
      <div className="data-sources">
        <span className="text-muted">DATA SOURCES:</span> Landsat 8/9 • Sentinel-2 • ESA WorldCover • ERA5-Land • WorldPop
      </div>
    </div>
  );
}
