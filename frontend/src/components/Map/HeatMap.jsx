import { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { fetchGrid, fetchHVISummary } from '../../services/api';
import './HeatMap.css';

const PUNE_CENTER = [18.5204, 73.8567];
const YEARS = [2021, 2022, 2023, 2024, 2025, 2026];

const TIER_COLORS = {
  'Heat-Safe': '#10b981',
  'Caution': '#fbbf24',
  'Stressed': '#f97316',
  'Emergency': '#ef4444',
};

const TIER_FILL_OPACITY = {
  'Heat-Safe': 0.5,
  'Caution': 0.6,
  'Stressed': 0.7,
  'Emergency': 0.85,
};

function getTierColor(tier) {
  return TIER_COLORS[tier] || '#334155';
}

// Debounce utility
function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

export default function HeatMap({ year: externalYear, onCellSelect }) {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const gridLayerRef = useRef(null);
  const abortControllerRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [year, setYear] = useState(externalYear || 2024);
  const [summary, setSummary] = useState(null);
  const [cellCount, setCellCount] = useState(0);

  // Sync external year prop
  useEffect(() => {
    if (externalYear && externalYear !== year) {
      setYear(externalYear);
    }
  }, [externalYear]);

  // Initialize Leaflet map with Canvas renderer
  useEffect(() => {
    if (mapInstance.current) return;

    mapInstance.current = L.map(mapRef.current, {
      center: PUNE_CENTER,
      zoom: 12,
      zoomControl: false,
      attributionControl: false,
      preferCanvas: true,       // ← Canvas renderer for 35k+ polygons
      renderer: L.canvas({      // ← Explicit canvas renderer with tolerance
        padding: 0.5,
        tolerance: 5,
      }),
    });

    // Dark tile layer (CartoDB Dark Matter)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(mapInstance.current);

    // Add zoom control to top-right
    L.control.zoom({ position: 'topright' }).addTo(mapInstance.current);

    // Attribution bottom-right
    L.control.attribution({ position: 'bottomright' }).addTo(mapInstance.current);

    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Load grid data — fetches from /demo/grid with optional bbox
  const loadData = useCallback(async (useBbox = false) => {
    setLoading(true);
    setError(null);

    // Cancel any previous requests
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    try {
      // Get map bounds for viewport-based filtering
      let bbox = null;
      if (useBbox && mapInstance.current) {
        const bounds = mapInstance.current.getBounds();
        bbox = `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;
      }

      const [gridData, summaryData] = await Promise.all([
        fetchGrid(year, 36000, bbox, signal),
        fetchHVISummary(year, signal),
      ]);

      setSummary(summaryData);

      // Clear existing grid layer
      if (gridLayerRef.current) {
        mapInstance.current.removeLayer(gridLayerRef.current);
      }

      const features = gridData.features || [];
      setCellCount(features.length);

      if (features.length === 0) {
        setLoading(false);
        return;
      }

      // Create GeoJSON layer (uses Canvas renderer from map init)
      gridLayerRef.current = L.geoJSON(gridData, {
        style: (feature) => {
          const tier = feature.properties.hvi_tier || 'Heat-Safe';
          return {
            fillColor: getTierColor(tier),
            fillOpacity: TIER_FILL_OPACITY[tier] || 0.5,
            color: getTierColor(tier),
            weight: 0.3,
            opacity: 0.6,
          };
        },
        onEachFeature: (feature, layer) => {
          const p = feature.properties;
          const tierClass = (p.hvi_tier || 'Heat-Safe').toLowerCase().replace('-', '');

          layer.on('click', async () => {
            if (onCellSelect) onCellSelect(p);

            // Initial loading popup
            const initialPopup = `
              <div class="cell-popup">
                <h4>Cell ${p.cell_id ?? '—'}</h4>
                <div class="popup-score">
                  <span class="big" style="color: ${getTierColor(p.hvi_tier)}">${(p.hvi_score ?? 0).toFixed(1)}</span>
                  <span class="badge badge-${tierClass}">${p.hvi_tier || '—'}</span>
                </div>
                <div class="popup-metrics">
                  <div class="popup-metric">
                    <span class="metric-label">LST</span>
                    <span class="metric-value">${(p.lst_predicted ?? p.lst_observed ?? 0).toFixed(1)}°C</span>
                  </div>
                </div>
                <div class="shap-container">
                  <div class="spinner small"></div>
                  <span class="loading-text">Analyzing risk factors...</span>
                </div>
              </div>
            `;
            layer.bindPopup(initialPopup, { maxWidth: 300, className: 'dark-popup' }).openPopup();

            // Fetch SHAP explainability
            try {
              import('../../services/api').then(async ({ explainCell }) => {
                const expl = await explainCell({
                  ndvi: p.ndvi,
                  ndbi: p.ndbi,
                  ndwi: p.ndwi,
                  tree_canopy_frac: p.tree_canopy_frac
                });

                if (expl && expl.contributions) {
                  const contribsHtml = expl.contributions.map(c => `
                    <div class="shap-item ${c.direction}">
                      <div class="shap-header">
                        <span class="shap-label">${c.label}</span>
                        <span class="shap-impact">${c.impact > 0 ? '+' : ''}${c.impact.toFixed(2)}°C</span>
                      </div>
                      <div class="shap-bar-bg">
                        <div class="shap-bar" style="width: ${Math.min(c.impact_pct, 100)}%"></div>
                      </div>
                      <div class="shap-desc">${c.description}</div>
                    </div>
                  `).join('');

                  const updatedPopup = `
                    <div class="cell-popup">
                      <h4>Cell ${p.cell_id ?? '—'}</h4>
                      <div class="popup-score">
                        <span class="big" style="color: ${getTierColor(p.hvi_tier)}">${(p.hvi_score ?? 0).toFixed(1)}</span>
                        <span class="badge badge-${tierClass}">${p.hvi_tier || '—'}</span>
                      </div>
                      <div class="shap-container">
                        <h5>Key Vulnerability Factors</h5>
                        ${contribsHtml}
                      </div>
                    </div>
                  `;
                  if (layer.isPopupOpen()) {
                    layer.setPopupContent(updatedPopup);
                  }
                }
              });
            } catch (err) {
              console.error("SHAP fetch failed:", err);
            }
          });

          layer.on('mouseover', () => {
            layer.setStyle({ weight: 2, fillOpacity: 0.9 });
            layer.bringToFront();
          });

          layer.on('mouseout', () => {
            if (gridLayerRef.current) {
              gridLayerRef.current.resetStyle(layer);
            }
          });
        },
      });

      if (mapInstance.current) {
        gridLayerRef.current.addTo(mapInstance.current);
      }
      setLoading(false);
    } catch (err) {
      if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
        console.log('Request aborted due to new action');
        return;
      }
      console.error('Failed to load grid data:', err);
      setError(err.message || 'Failed to connect to backend');
      setLoading(false);
    }
  }, [year, onCellSelect]);

  // Initial full load when year changes
  useEffect(() => {
    if (mapInstance.current) {
      loadData(false); // Full load (no bbox) on year change
    }
  }, [year]);

  // Viewport-based refetch on pan/zoom (debounced)
  useEffect(() => {
    if (!mapInstance.current) return;

    const debouncedRefetch = debounce(() => {
      const zoom = mapInstance.current.getZoom();
      // Only use bbox filtering when zoomed in enough (zoom >= 13)
      // At city-wide view, load all cells
      if (zoom >= 13) {
        loadData(true);
      }
    }, 500);

    mapInstance.current.on('moveend', debouncedRefetch);
    mapInstance.current.on('zoomend', debouncedRefetch);

    return () => {
      if (mapInstance.current) {
        mapInstance.current.off('moveend', debouncedRefetch);
        mapInstance.current.off('zoomend', debouncedRefetch);
      }
    };
  }, [loadData]);

  return (
    <div className="map-wrapper">
      <div ref={mapRef} className="map-container" />

      {/* Loading overlay */}
      {loading && (
        <div className="map-loading">
          <div className="spinner" />
          <p>Loading {year} heat vulnerability data…</p>
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="map-error">
          <div className="error-icon">⚠️</div>
          <h3>Connection Error</h3>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={() => loadData(false)}>Retry</button>
        </div>
      )}

      {/* KPI Overlay */}
      {summary && !loading && (
        <div className="kpi-overlay glass-panel">
          <div className="kpi-card">
            <span className="label">Avg HVI</span>
            <span className="value">{summary.avg_hvi?.toFixed(1) ?? '—'}</span>
          </div>
          <div className="kpi-card danger">
            <span className="label">Emergency</span>
            <span className="value">{(summary.tier_distribution?.['Emergency'] ?? 0).toLocaleString()}</span>
          </div>
          <div className="kpi-card warning">
            <span className="label">Stressed</span>
            <span className="value">{(summary.tier_distribution?.['Stressed'] ?? 0).toLocaleString()}</span>
          </div>
          <div className="kpi-card safe">
            <span className="label">Cells</span>
            <span className="value">{cellCount.toLocaleString()}</span>
          </div>
        </div>
      )}

      {/* Year selector */}
      <div className="year-overlay glass-panel">
        {YEARS.map((y) => (
          <button
            key={y}
            className={`year-btn ${y === year ? 'active' : ''}`}
            onClick={() => setYear(y)}
          >
            {y}
          </button>
        ))}
      </div>

      {/* Legend */}
      <div className="map-legend glass-panel">
        <h4>HVI Tier</h4>
        {Object.entries(TIER_COLORS).map(([tier, color]) => (
          <div key={tier} className="legend-row">
            <div className="legend-color" style={{ background: color }} />
            <span>{tier}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
