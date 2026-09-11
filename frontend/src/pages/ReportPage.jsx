import { useState, useEffect, useRef } from 'react';
import { MapPin, AlertCircle } from 'lucide-react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { submitReport } from '../services/api';
import './ReportForm.css';

// Fix for default Leaflet marker icon in React
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const PUNE_CENTER = [18.5204, 73.8567];

export default function ReportForm() {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: 'extreme_heat',
    severity: 3,
    heat_impact_rating: 3,
    shade_rating: 3,
    water_rating: 3,
  });
  
  const [position, setPosition] = useState(null); // {lat, lng}
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const markerInstance = useRef(null);

  useEffect(() => {
    if (!mapInstance.current && mapRef.current) {
      mapInstance.current = L.map(mapRef.current).setView(PUNE_CENTER, 12);
      L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
        attribution: '&copy; CARTO'
      }).addTo(mapInstance.current);

      mapInstance.current.on('click', (e) => {
        setPosition(e.latlng);
      });
    }

    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (mapInstance.current && position) {
      if (markerInstance.current) {
        markerInstance.current.setLatLng(position);
      } else {
        markerInstance.current = L.marker(position).addTo(mapInstance.current);
      }
    } else if (markerInstance.current) {
      markerInstance.current.remove();
      markerInstance.current = null;
    }
  }, [position]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!position) {
      setError("Please drop a pin on the map to select the location.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await submitReport({
        latitude: position.lat,
        longitude: position.lng,
        category: formData.category,
        description: formData.description,
        severity: parseInt(formData.severity),
        heat_impact_rating: parseInt(formData.heat_impact_rating),
        shade_rating: parseInt(formData.shade_rating),
        water_rating: parseInt(formData.water_rating),
        reporter_name: formData.name,
      });
      setSubmitted(true);
      setTimeout(() => {
        setSubmitted(false);
        setFormData({
          name: '', description: '', category: 'extreme_heat', severity: 3, heat_impact_rating: 3, shade_rating: 3, water_rating: 3
        });
        setPosition(null);
      }, 4000);
    } catch (err) {
      console.error(err);
      setError("Failed to submit report. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const renderSurveyQuestion = (label, field, desc0, desc5) => (
    <div className="form-group survey-group">
      <label>{label}</label>
      <div className="survey-options">
        {[0, 1, 2, 3, 4, 5].map((val) => (
          <label key={val} className={`survey-radio ${formData[field] === val ? 'active' : ''}`}>
            <input 
              type="radio" 
              name={field}
              value={val}
              checked={formData[field] === val}
              onChange={(e) => setFormData({...formData, [field]: parseInt(e.target.value)})}
            />
            {val}
          </label>
        ))}
      </div>
      <div className="survey-legend">
        <span>0 = {desc0}</span>
        <span>5 = {desc5}</span>
      </div>
    </div>
  );

  return (
    <div className="report-container animate-slide-in">
      <header className="page-header">
        <h2>Report Community Heat Impact</h2>
        <p className="subtitle">Crowdsource real-time vulnerability data. Help us map extreme heat risks.</p>
      </header>

      <div className="report-layout">
        <div className="form-panel glass-panel">
          {submitted ? (
            <div className="success-message">
              <div className="success-icon">✓</div>
              <h3>Report Submitted</h3>
              <p>Thank you. Your report has been submitted and is awaiting verification by the disaster management cell.</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="impact-form">
              {error && <div className="error-message">{error}</div>}

              <div className="form-group">
                <label>1. Location (Tap on the map to drop a pin)</label>
                <div className="map-picker-container">
                  <div ref={mapRef} className="location-picker-map"></div>
                </div>
                {!position && <p className="map-hint">Click the map to select a location.</p>}
                {position && <p className="map-hint success-hint">Location selected: {position.lat.toFixed(4)}, {position.lng.toFixed(4)}</p>}
              </div>

              <div className="form-group">
                <label>2. Category</label>
                <select 
                  value={formData.category} 
                  onChange={(e) => setFormData({...formData, category: e.target.value})}
                  className="form-select"
                >
                  <option value="extreme_heat">Extreme Heat</option>
                  <option value="lack_of_shade">Lack of Shade</option>
                  <option value="hot_pavement">Hot Pavement</option>
                  <option value="bus_stop_no_shade">Bus Stop (No Shade)</option>
                  <option value="water_fountain_unavailable">No Water Available</option>
                  <option value="cooling_shelter_closed">Cooling Shelter Closed</option>
                </select>
              </div>

              <div className="form-group row">
                <div className="half">
                  <label>Reporter Name (Optional)</label>
                  <input type="text" value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} />
                </div>
                <div className="half">
                  <label>General Severity (1-5)</label>
                  <input type="number" min="1" max="5" value={formData.severity} onChange={(e) => setFormData({...formData, severity: e.target.value})} required />
                </div>
              </div>

              <div className="survey-section">
                <h3 className="section-title">Environmental Survey</h3>
                {renderSurveyQuestion("Heat Impact Assessment", "heat_impact_rating", "Normal", "Emergency")}
                {renderSurveyQuestion("Shade Availability", "shade_rating", "Lots of shade", "No shade at all")}
                {renderSurveyQuestion("Water Availability", "water_rating", "Easily available", "None available")}
              </div>

              <div className="form-group">
                <label>Additional Notes (Optional)</label>
                <textarea 
                  rows="3" 
                  placeholder="Describe the situation..."
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                ></textarea>
              </div>

              <button type="submit" className="btn btn-primary submit-btn" disabled={loading}>
                <AlertCircle size={18} /> {loading ? "Submitting..." : "Submit Impact Report"}
              </button>
            </form>
          )}
        </div>

        <div className="info-panel">
          <div className="glass-panel feed-panel">
            <h3>How It Works</h3>
            <div className="feed-list">
              <div className="feed-item">
                <span className="badge badge-caution">1. Locate</span>
                <p className="feed-desc">Pinpoint the exact location on the map.</p>
              </div>
              <div className="feed-item">
                <span className="badge badge-stressed">2. Survey</span>
                <p className="feed-desc">Fill out the rapid survey using the 0-5 scale to quantify environmental factors.</p>
              </div>
              <div className="feed-item">
                <span className="badge badge-emergency">3. Verification</span>
                <p className="feed-desc">Once verified by admins, your report acts as a live pin on the Heat Vulnerability Map.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
