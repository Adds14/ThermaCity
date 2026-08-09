import { useState } from 'react';
import { MapPin, Camera, AlertCircle } from 'lucide-react';
import './ReportForm.css';

export default function ReportForm() {
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    location: '',
    description: '',
    intensity: 'High',
    needsTanker: false,
  });
  
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    // API Call goes here: /api/v1/reports
    setSubmitted(true);
    setTimeout(() => {
      setSubmitted(false);
      setFormData({
        name: '', phone: '', location: '', description: '', intensity: 'High', needsTanker: false
      });
    }, 3000);
  };

  return (
    <div className="report-container animate-slide-in">
      <header className="page-header">
        <h2>Report Community Heat Impact</h2>
        <p className="subtitle">Crowdsource real-time vulnerability data. Request water tankers or report heat emergencies.</p>
      </header>

      <div className="report-layout">
        <div className="form-panel glass-panel">
          {submitted ? (
            <div className="success-message">
              <div className="success-icon">✓</div>
              <h3>Report Submitted</h3>
              <p>Thank you. Your report has been routed to the disaster management cell.</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="impact-form">
              <div className="form-group">
                <label>Location (Pin on Map or enter area)</label>
                <div className="input-with-icon">
                  <MapPin size={18} />
                  <input 
                    type="text" 
                    placeholder="e.g. Near Kasba Ganpati"
                    value={formData.location}
                    onChange={(e) => setFormData({...formData, location: e.target.value})}
                    required
                  />
                </div>
              </div>

              <div className="form-group row">
                <div className="half">
                  <label>Reporter Name</label>
                  <input type="text" value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} />
                </div>
                <div className="half">
                  <label>Contact Number</label>
                  <input type="tel" value={formData.phone} onChange={(e) => setFormData({...formData, phone: e.target.value})} />
                </div>
              </div>

              <div className="form-group">
                <label>Heat Impact Intensity</label>
                <div className="radio-group">
                  {['Moderate', 'High', 'Severe', 'Emergency'].map(level => (
                    <label key={level} className={`radio-btn ${formData.intensity === level ? 'active' : ''}`}>
                      <input 
                        type="radio" 
                        name="intensity" 
                        value={level}
                        checked={formData.intensity === level}
                        onChange={(e) => setFormData({...formData, intensity: e.target.value})}
                      />
                      {level}
                    </label>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label className="checkbox-label">
                  <input 
                    type="checkbox" 
                    checked={formData.needsTanker}
                    onChange={(e) => setFormData({...formData, needsTanker: e.target.checked})}
                  />
                  <span>Urgent: Request Water Tanker Dispatch</span>
                </label>
              </div>

              <div className="form-group">
                <label>Description of conditions</label>
                <textarea 
                  rows="4" 
                  placeholder="Describe the situation (e.g. multiple heat strokes, water scarcity for 3 days)..."
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                ></textarea>
              </div>

              <button type="submit" className="btn btn-primary submit-btn">
                <AlertCircle size={18} /> Submit Impact Report
              </button>
            </form>
          )}
        </div>

        <div className="info-panel">
          <div className="glass-panel feed-panel">
            <h3>Recent Reports</h3>
            <div className="feed-list">
              <div className="feed-item">
                <span className="badge badge-emergency">Emergency</span>
                <p className="feed-loc">Bhavani Peth • 10 mins ago</p>
                <p className="feed-desc">Water tanker requested immediately. Severe dehydration cases.</p>
              </div>
              <div className="feed-item">
                <span className="badge badge-stressed">Stressed</span>
                <p className="feed-loc">Shivajinagar • 45 mins ago</p>
                <p className="feed-desc">High ambient heat in tin-roof structures.</p>
              </div>
              <div className="feed-item">
                <span className="badge badge-caution">Caution</span>
                <p className="feed-loc">Kothrud • 2 hours ago</p>
                <p className="feed-desc">Minor heat exhaustion reported at construction site.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
