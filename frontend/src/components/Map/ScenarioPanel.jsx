import { useState, useEffect } from 'react';
import { Sliders, Sun, TreeDeciduous, Download } from 'lucide-react';
import { simulateScenario, downloadCellReport } from '../../services/api';
import './ScenarioPanel.css';

export default function ScenarioPanel({ year = 2026, selectedCell = null }) {
  const [canopyDelta, setCanopyDelta] = useState(0);
  const [ndbiDelta, setNdbiDelta] = useState(0);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const handleSimulate = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        tree_canopy_delta: canopyDelta / 100,
        ndbi_delta: -ndbiDelta / 100,
        ndvi_delta: canopyDelta > 0 ? canopyDelta / 200 : 0,
        ndwi_delta: 0,
        year: year,
      };

      if (selectedCell) {
        payload.baseline_ndvi = selectedCell.ndvi;
        payload.baseline_ndbi = selectedCell.ndbi;
        payload.baseline_ndwi = selectedCell.ndwi;
        payload.baseline_tree_canopy_frac = selectedCell.tree_canopy_frac;
        payload.baseline_lst = selectedCell.lst_predicted;
        payload.baseline_hvi_score = selectedCell.hvi_score;
        payload.baseline_hvi_tier = selectedCell.hvi_tier;
      }

      const data = await simulateScenario(payload);
      setResults(data);
    } catch (err) {
      console.error('Simulation failed:', err);
      setError('Backend unreachable.');
    } finally {
      setLoading(false);
    }
  };

  const formatDelta = (val) => {
    if (val == null) return '—';
    const sign = val > 0 ? '+' : '';
    return `${sign}${val.toFixed(2)}`;
  };

  useEffect(() => {
    setResults(null);
  }, [selectedCell]);

  const handleDownload = async (e) => {
    const btn = e.currentTarget;
    const originalText = btn.innerHTML;
    btn.innerHTML = 'Generating...';
    btn.disabled = true;
    try {
      await downloadCellReport({
        cell_id: selectedCell.cell_id,
        year: year,
        baseline_lst: selectedCell.lst_predicted,
        baseline_ndvi: selectedCell.ndvi,
        baseline_ndbi: selectedCell.ndbi,
        baseline_hvi_score: selectedCell.hvi_score,
        baseline_hvi_tier: selectedCell.hvi_tier,
        simulated_lst: results?.simulated?.lst,
        simulated_hvi_tier: results?.simulated?.hvi_tier,
        lst_delta: results?.lst_delta,
        applied_canopy_delta: canopyDelta / 100,
        applied_ndbi_delta: ndbiDelta / 100,
      });
    } catch (err) {
      console.error("Failed to download block report", err);
      alert("Failed to generate report");
    } finally {
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  };

  return (
    <div className="scenario-panel glass-panel">
      <div className="panel-header">
        <h3><Sliders size={18} /> {selectedCell ? `Block Simulator (ID: ${selectedCell.cell_id})` : 'City Simulator'}</h3>
        <p className="subtitle">Model cooling interventions &amp; see predicted impact.</p>
      </div>

      <div className="slider-group">
        <label>
          <div className="sg-left">
            <TreeDeciduous size={16} />
            <span>Tree Canopy Afforestation</span>
          </div>
          <span className="value">+{canopyDelta}%</span>
        </label>
        <input
          type="range"
          min="0"
          max="50"
          step="5"
          value={canopyDelta}
          onChange={(e) => setCanopyDelta(Number(e.target.value))}
          className="styled-slider"
        />
        <div className="slider-marks">
          <span>0%</span>
          <span>50%</span>
        </div>
      </div>

      <div className="slider-group">
        <label>
          <div className="sg-left">
            <Sun size={16} />
            <span>Cool Roofs & Pavements</span>
          </div>
          <span className="value">+{ndbiDelta}%</span>
        </label>
        <input
          type="range"
          min="0"
          max="30"
          step="5"
          value={ndbiDelta}
          onChange={(e) => setNdbiDelta(Number(e.target.value))}
          className="styled-slider"
        />
        <div className="slider-marks">
          <span>0%</span>
          <span>30%</span>
        </div>
      </div>

      <button
        className="btn-primary"
        style={{ width: '100%', marginTop: '1rem', padding: '0.75rem' }}
        onClick={handleSimulate}
        disabled={loading}
      >
        {loading ? 'Simulating...' : 'Simulate Impact'}
      </button>

      {error && <div className="error-message" style={{ color: '#ef4444', marginTop: '1rem', fontSize: '0.85rem' }}>{error}</div>}

      {results && !loading && (
        <div className="results-box fade-in">
          <h4>SIMULATION RESULTS</h4>
          
          <div className="results-grid">
            <div className="result-metric">
              <span className="rm-label">Baseline LST</span>
              <span className="rm-value">{results.baseline.lst.toFixed(1)}°C</span>
            </div>
            
            <div className="result-metric">
              <span className="rm-label">Projected LST</span>
              <span className="rm-value text-blue">{results.simulated.lst.toFixed(1)}°C</span>
            </div>
          </div>
          
          <div className="delta-pill">
            Temperature change: <strong className={results.lst_delta < 0 ? 'text-blue' : ''}>{formatDelta(results.lst_delta)}°C</strong>
          </div>

          <hr className="divider" />

          <div className="results-grid">
            <div className="result-metric">
              <span className="rm-label">Baseline HVI</span>
              <div className="rm-badge-group">
                <span className="rm-value">{results.baseline.hvi_score?.toFixed(1) ?? '—'}</span>
                <span className={`badge badge-${results.baseline.hvi_tier?.toLowerCase().replace('-', '')}`}>
                  {results.baseline.hvi_tier ?? 'N/A'}
                </span>
              </div>
            </div>
            
            <div className="result-metric">
              <span className="rm-label">Projected HVI</span>
              <div className="rm-badge-group">
                <span className="rm-value">{results.simulated.hvi_score?.toFixed(1) ?? '—'}</span>
                <span className={`badge badge-${results.simulated.hvi_tier?.toLowerCase().replace('-', '')}`}>
                  {results.simulated.hvi_tier ?? 'N/A'}
                </span>
              </div>
            </div>
          </div>
          
          {selectedCell && (
            <button 
              className="btn btn-outline"
              style={{ width: '100%', marginTop: '1.5rem', fontSize: '0.85rem', padding: '0.5rem' }}
              onClick={handleDownload}
            >
              <Download size={14} /> Download Scenario Report
            </button>
          )}
        </div>
      )}
    </div>
  );
}
