import { useState, useEffect, useRef } from 'react';
import { MapPin, AlertCircle, ArrowRight, ArrowLeft, CheckCircle } from 'lucide-react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { submitReport } from '../services/api';
import './ReportForm.css';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const PUNE_CENTER = [18.5204, 73.8567];

export default function ReportForm() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: 'extreme_heat',
    severity: 3,
    heat_impact_rating: 3,
    shade_rating: 3,
    water_rating: 3,
  });
  
  const [position, setPosition] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const markerInstance = useRef(null);

  // Initialize Map only on Step 1
  useEffect(() => {
    if (step === 1 && !mapInstance.current && mapRef.current) {
      mapInstance.current = L.map(mapRef.current).setView(PUNE_CENTER, 12);
      L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
        attribution: '&copy; CARTO'
      }).addTo(mapInstance.current);

      mapInstance.current.on('click', (e) => {
        setPosition(e.latlng);
      });

      // Recover marker if returning to Step 1
      if (position) {
        markerInstance.current = L.marker(position).addTo(mapInstance.current);
      }
    }

    return () => {
      if (step !== 1 && mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
        markerInstance.current = null;
      }
    };
  }, [step]); // Re-run when step changes

  useEffect(() => {
    if (step === 1 && mapInstance.current && position) {
      if (markerInstance.current) {
        markerInstance.current.setLatLng(position);
      } else {
        markerInstance.current = L.marker(position).addTo(mapInstance.current);
      }
    }
  }, [position, step]);

  const handleSubmit = async () => {
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
        setStep(1);
        setFormData({
          name: '', description: '', category: 'extreme_heat', severity: 3, heat_impact_rating: 3, shade_rating: 3, water_rating: 3
        });
        setPosition(null);
      }, 5000);
    } catch (err) {
      console.error(err);
      setError("Failed to submit report. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleNext = () => {
    if (step === 1 && !position) {
      setError("Please drop a pin on the map to continue.");
      return;
    }
    setError(null);
    setStep(s => Math.min(s + 1, 4));
  };

  const handlePrev = () => setStep(s => Math.max(s - 1, 1));

  const renderSurveySlider = (label, field, desc0, desc5) => (
    <div className="survey-slider-group">
      <div className="ss-header">
        <label>{label}</label>
        <span className="ss-val badge badge-safe">{formData[field]}/5</span>
      </div>
      <input 
        type="range"
        min="0" max="5" step="1"
        value={formData[field]}
        onChange={(e) => setFormData({...formData, [field]: parseInt(e.target.value)})}
        className="styled-slider"
      />
      <div className="ss-labels">
        <span>0 - {desc0}</span>
        <span>5 - {desc5}</span>
      </div>
    </div>
  );

  const steps = [
    { num: 1, title: 'Location' },
    { num: 2, title: 'Details' },
    { num: 3, title: 'Survey' },
    { num: 4, title: 'Review' },
  ];

  return (
    <div className="report-container animate-slide-in">
      <header className="page-header">
        <h2>Report Community Heat Impact</h2>
        <p className="subtitle">Help us map extreme heat risks to prioritize cooling interventions.</p>
      </header>

      <div className="wizard-layout">
        <div className="wizard-sidebar panel">
          <ul className="wizard-steps">
            {steps.map(s => (
              <li key={s.num} className={`wizard-step ${step === s.num ? 'active' : ''} ${step > s.num ? 'completed' : ''}`}>
                <div className="step-circle">{step > s.num ? '✓' : s.num}</div>
                <span>{s.title}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="wizard-content panel">
          {submitted ? (
            <div className="success-state fade-in">
              <CheckCircle size={64} color="#10b981" />
              <h3>Report Submitted Successfully!</h3>
              <p>Thank you for contributing. Your report has been submitted for admin verification and will soon appear on the public heat map.</p>
            </div>
          ) : (
            <div className="step-container fade-in" key={step}>
              {error && <div className="error-banner"><AlertCircle size={16} /> {error}</div>}

              {/* STEP 1 */}
              {step === 1 && (
                <div className="step-content">
                  <h3>Step 1: Where is this happening?</h3>
                  <p className="step-desc">Tap on the map to drop a pin at the location.</p>
                  <div className="map-wrapper-wizard">
                    <div ref={mapRef} className="location-picker-map"></div>
                  </div>
                  {position && <p className="success-text mt-2">✓ Location captured ({position.lat.toFixed(4)}, {position.lng.toFixed(4)})</p>}
                </div>
              )}

              {/* STEP 2 */}
              {step === 2 && (
                <div className="step-content">
                  <h3>Step 2: Incident Details</h3>
                  <div className="form-grid">
                    <div className="form-group">
                      <label>Category</label>
                      <select 
                        value={formData.category} 
                        onChange={(e) => setFormData({...formData, category: e.target.value})}
                        className="form-input"
                      >
                        <option value="extreme_heat">Extreme Heat</option>
                        <option value="lack_of_shade">Lack of Shade</option>
                        <option value="hot_pavement">Hot Pavement</option>
                        <option value="bus_stop_no_shade">Bus Stop (No Shade)</option>
                        <option value="water_fountain_unavailable">No Water Available</option>
                        <option value="cooling_shelter_closed">Cooling Shelter Closed</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label>Severity (1 = Mild, 5 = Severe)</label>
                      <input 
                        type="range" min="1" max="5" 
                        value={formData.severity} 
                        onChange={(e) => setFormData({...formData, severity: e.target.value})} 
                        className="styled-slider mt-2" 
                      />
                      <div className="ss-labels mt-1"><span>1</span><span>5</span></div>
                    </div>

                    <div className="form-group full-width">
                      <label>Your Name (Optional)</label>
                      <input 
                        type="text" 
                        placeholder="Anonymous"
                        value={formData.name} 
                        onChange={(e) => setFormData({...formData, name: e.target.value})} 
                        className="form-input"
                      />
                    </div>

                    <div className="form-group full-width">
                      <label>Additional Notes (Optional)</label>
                      <textarea 
                        rows="3" 
                        placeholder="Describe the situation..."
                        value={formData.description}
                        onChange={(e) => setFormData({...formData, description: e.target.value})}
                        className="form-input"
                      ></textarea>
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 3 */}
              {step === 3 && (
                <div className="step-content">
                  <h3>Step 3: Environmental Survey</h3>
                  <p className="step-desc">Quantify the environmental factors causing vulnerability here.</p>
                  
                  <div className="survey-sliders">
                    {renderSurveySlider("Heat Impact Assessment", "heat_impact_rating", "Normal", "Emergency")}
                    {renderSurveySlider("Shade Availability", "shade_rating", "Lots of shade", "No shade at all")}
                    {renderSurveySlider("Water Availability", "water_rating", "Easily available", "None available")}
                  </div>
                </div>
              )}

              {/* STEP 4 */}
              {step === 4 && (
                <div className="step-content">
                  <h3>Step 4: Review & Submit</h3>
                  
                  <div className="review-box">
                    <div className="rv-row"><span className="rv-label">Location</span> <span className="rv-val">{position?.lat.toFixed(4)}, {position?.lng.toFixed(4)}</span></div>
                    <div className="rv-row"><span className="rv-label">Category</span> <span className="rv-val capitalize">{formData.category.replace(/_/g, ' ')}</span></div>
                    <div className="rv-row"><span className="rv-label">Severity</span> <span className="rv-val">{formData.severity}/5</span></div>
                    {formData.description && <div className="rv-row"><span className="rv-label">Notes</span> <span className="rv-val">{formData.description}</span></div>}
                    
                    <hr className="divider" />
                    
                    <div className="rv-row"><span className="rv-label">Heat Impact</span> <span className="rv-val">{formData.heat_impact_rating}/5</span></div>
                    <div className="rv-row"><span className="rv-label">Shade Rating</span> <span className="rv-val">{formData.shade_rating}/5</span></div>
                    <div className="rv-row"><span className="rv-label">Water Rating</span> <span className="rv-val">{formData.water_rating}/5</span></div>
                  </div>
                </div>
              )}

              <div className="wizard-footer">
                <button 
                  className="btn-outline" 
                  onClick={handlePrev} 
                  disabled={step === 1 || loading}
                >
                  <ArrowLeft size={16} /> Back
                </button>
                
                {step < 4 ? (
                  <button className="btn-primary" onClick={handleNext}>
                    Continue <ArrowRight size={16} />
                  </button>
                ) : (
                  <button className="btn-primary submit-btn" onClick={handleSubmit} disabled={loading}>
                    <AlertCircle size={16} /> {loading ? 'Submitting...' : 'Submit Report'}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
