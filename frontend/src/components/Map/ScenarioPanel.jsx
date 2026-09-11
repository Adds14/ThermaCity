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
      setError('Backend unreachable. Start the server with: uvicorn app.main:app --reload');
    } finally {
      setLoading(false);
    }
  };

  const formatDelta = (val) => {
    if (val == null) return '—';
    const sign = val > 0 ? '+' : '';
    return `${sign}${val.toFixed(2)}`;
  };

  // Reset results if selected cell changes
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
        <h3><Sliders size={18} /> {selectedCell ? `Block Simulator (ID: ${selectedCell.cell_id})` : 'City Average Simulator'}</h3>
        <p className="subtitle">Model cooling interventions &amp; see predicted temperature change</p>
      </div>

      <div className="slider-group">
        <label>
          <TreeDeciduous size={16} />
          <span>Tree Canopy Afforestation</span>
          <span className="value">+{canopyDelta}%</span>
        </label>
        <input
          type="range"
          min="0"
          max="50"
          step="1"
          value={canopyDelta}
          onChange={(e) => setCanopyDelta(Number(e.target.value))}
        />
        <div className="slider-labels">
          <span>0%</span>
          <span>+50%</span>
        </div>
      </div>

      <div className="slider-group">
        <label>
          <Sun size={16} />
          <span>Cool Roofs (Albedo ↑)</span>
          <span className="value">+{ndbiDelta}%</span>
        </label>
        <input
          type="range"
          min="0"
          max="30"
          step="1"
          value={ndbiDelta}
          onChange={(e) => setNdbiDelta(Number(e.target.value))}
        />
        <div className="slider-labels">
          <span>0%</span>
          <span>30%</span>
        </div>
      </div>

      <button
        className={`btn btn-primary full-width ${loading ? 'loading' : ''}`}
        onClick={handleSimulate}
        disabled={loading || (canopyDelta === 0 && ndbiDelta === 0)}
      >
        {loading ? 'Running AI Model…' : 'Simulate Impact'}
      </button>

      {error && (
        <div className="sim-error">
          <p>{error}</p>
        </div>
      )}

      {results && !error && (
        <div className="sim-results">
          <h4>Simulation Results</h4>

          <div className="result-row">
            <span className="result-label">Baseline LST</span>
            <span className="result-value">{results.baseline?.lst?.toFixed(1) ?? '—'}°C</span>
          </div>

          <div className="result-row">
            <span className="result-label">Simulated LST</span>
            <span className="result-value">{results.simulated?.lst?.toFixed(1) ?? '—'}°C</span>
          </div>

          <div className="result-row">
            <span className="result-label">Temperature Change</span>
            <span className={`result-delta ${results.lst_delta < 0 ? 'delta-negative' : 'delta-positive'}`}>
              {formatDelta(results.lst_delta)}°C
            </span>
          </div>

          <div className="result-row">
            <span className="result-label">Baseline Tier</span>
            <span className={`badge badge-${(results.baseline?.hvi_tier || '').toLowerCase().replace('-', '')}`}>
              {results.baseline?.hvi_tier ?? '—'}
            </span>
          </div>

          <div className="result-row">
            <span className="result-label">Simulated Tier</span>
            <span className={`badge badge-${(results.simulated?.hvi_tier || '').toLowerCase().replace('-', '')}`}>
              {results.simulated?.hvi_tier ?? '—'}
            </span>
          </div>

          <div className="result-row">
            <span className="result-label">HVI Change</span>
            <span className={`result-delta ${results.hvi_delta < 0 ? 'delta-negative' : 'delta-positive'}`}>
              {formatDelta(results.hvi_delta)} pts
            </span>
          </div>

          {selectedCell && (
            <button
              className="btn btn-outline full-width"
              style={{ marginTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
              onClick={handleDownload}
            >
              <Download size={16} />
              Export Block Report
            </button>
          )}
        </div>
      )}
    </div>
  );
}
