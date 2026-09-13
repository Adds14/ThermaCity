import { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { fetchGrid, fetchHVISummary, fetchReports, fetchWardSummary, fetchWardGeometries } from '../../services/api';
import WARDS from '../../data/wards';
import './HeatMap.css';

const PUNE_CENTER = [18.5204, 73.8567];
const PUNE_BOUNDS = [[18.40, 73.72], [18.65, 73.99]];
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

export default function HeatMap({ year: externalYear, onCellSelect }) {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const gridLayerRef = useRef(null);
  const reportsLayerRef = useRef(null);
  const wardLayerRef = useRef(null);
  const abortControllerRef = useRef(null);

  const onCellSelectRef = useRef(onCellSelect);
  useEffect(() => {
    onCellSelectRef.current = onCellSelect;
  }, [onCellSelect]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [year, setYear] = useState(externalYear || 2026);
  const [summary, setSummary] = useState(null);
  const [cellCount, setCellCount] = useState(0);
  const [showHeatmap, setShowHeatmap] = useState(true);

  // Two-level navigation state
  const [viewMode, setViewMode] = useState('wards'); // 'wards' or 'blocks'
  const [selectedWard, setSelectedWard] = useState(null);
  const [wardSummaries, setWardSummaries] = useState([]);

  // Sync external year prop
  useEffect(() => {
    if (externalYear && externalYear !== year) {
      setYear(externalYear);
    }
  }, [externalYear]);

  // Read URL params for auto-drilldown
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const wardId = parseInt(params.get('ward'));
    if (wardId) {
      const ward = WARDS.find(w => w.id === wardId);
      if (ward) {
        setSelectedWard(ward);
        setViewMode('blocks');
      }
    }
  }, []);

  // Initialize Leaflet map
  useEffect(() => {
    if (mapInstance.current) return;

    const puneBounds = L.latLngBounds(PUNE_BOUNDS);

    mapInstance.current = L.map(mapRef.current, {
      center: PUNE_CENTER,
      zoom: 12,
      minZoom: 11,
      maxZoom: 16,
      maxBounds: puneBounds.pad(0.1),
      maxBoundsViscosity: 1.0,
      zoomControl: false,
      attributionControl: false,
      preferCanvas: true,
      renderer: L.canvas({ padding: 0.5, tolerance: 5 }),
    });

    // Light tile layer (CartoDB Positron)
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
      subdomains: 'abcd',
      maxZoom: 16,
    }).addTo(mapInstance.current);

    L.control.zoom({ position: 'topright' }).addTo(mapInstance.current);
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

  // ── Load ward polygons (Level 1) ──────────────────────────
  const loadWards = useCallback(async () => {
    setLoading(true);
    setError(null);

    if (abortControllerRef.current) abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();

    try {
      const [wardGeoData, wardData, reportsData] = await Promise.all([
        fetchWardGeometries(year, abortControllerRef.current.signal),
        fetchWardSummary(year, abortControllerRef.current.signal),
        fetchReports(true).catch(err => { console.warn('Reports fetch failed (non-critical):', err.message); return { features: [] }; }),
      ]);

      setWardSummaries(wardData);

      // Clear existing layers
      if (gridLayerRef.current && mapInstance.current) {
        mapInstance.current.removeLayer(gridLayerRef.current);
        gridLayerRef.current = null;
      }
      if (wardLayerRef.current && mapInstance.current) {
        mapInstance.current.removeLayer(wardLayerRef.current);
        wardLayerRef.current = null;
      }
      if (reportsLayerRef.current && mapInstance.current) {
        mapInstance.current.removeLayer(reportsLayerRef.current);
        reportsLayerRef.current = null;
      }

      // Create ward polygons layer from GeoJSON
      const labels = [];
      const geoLayer = L.geoJSON(wardGeoData, {
        style: (feature) => {
          const tier = feature.properties.hvi_tier || 'Heat-Safe';
          return {
            fillColor: getTierColor(tier),
            fillOpacity: TIER_FILL_OPACITY[tier] || 0.5,
            color: '#1e293b',
            weight: 2,
            opacity: 0.8,
          };
        },
        onEachFeature: (feature, layer) => {
          const p = feature.properties;
          const tier = p.hvi_tier || 'Heat-Safe';
          const color = getTierColor(tier);

          // Add ward name label at centroid
          const center = layer.getBounds().getCenter();
          const label = L.divIcon({
            html: `<div style="
              color: #fff; font-size: 10px; font-weight: 700;
              white-space: nowrap; text-shadow: 0 1px 3px rgba(0,0,0,0.8);
              pointer-events: none;
            ">${p.ward_id}</div>`,
            className: 'ward-number-label',
            iconSize: [24, 24],
            iconAnchor: [12, 12],
          });
          const labelMarker = L.marker(center, { icon: label, interactive: false });
          labels.push(labelMarker);

          // Popup
          const popupContent = `
            <div class="cell-popup">
              <h4 style="margin-bottom:2px;">Ward ${p.ward_id}</h4>
              <div style="font-size:0.85rem; color:#94a3b8; margin-bottom:8px;">${p.ward_name}</div>
              <div class="popup-score">
                <span class="big" style="color: ${color}">${p.avg_hvi.toFixed(1)}</span>
                <span class="badge badge-${tier.toLowerCase().replace('-', '')}">${tier}</span>
              </div>
              <div class="popup-metrics">
                <div class="popup-metric">
                  <span class="metric-label">Avg LST</span>
                  <span class="metric-value">${p.avg_lst?.toFixed(1) ?? '—'}°C</span>
                </div>
                <div class="popup-metric">
                  <span class="metric-label">Blocks</span>
                  <span class="metric-value">${p.cell_count}</span>
                </div>
              </div>
              <button onclick="window.__drillIntoWard(${p.ward_id})" style="
                margin-top: 10px; width: 100%; padding: 6px 12px; border: none;
                background: #3b82f6; color: #fff; border-radius: 6px;
                cursor: pointer; font-weight: 600; font-size: 0.85rem;
              ">View Blocks →</button>
            </div>
          `;
          layer.bindPopup(popupContent, { maxWidth: 250, className: 'dark-popup' });

          // Hover effect
          layer.on('mouseover', () => {
            layer.setStyle({ weight: 3, fillOpacity: 0.9 });
            layer.bringToFront();
          });
          layer.on('mouseout', () => {
            geoLayer.resetStyle(layer);
          });
        },
      });

      wardLayerRef.current = L.featureGroup([geoLayer, ...labels]);

      if (mapInstance.current && showHeatmap) {
        wardLayerRef.current.addTo(mapInstance.current);
      }

      // Add reports layer
      addReportsLayer(reportsData);

      // Compute city-wide summary from ward data
      if (wardData.length > 0) {
        const totalCells = wardData.reduce((s, w) => s + w.cell_count, 0);
        const avgHvi = wardData.reduce((s, w) => s + w.avg_hvi * w.cell_count, 0) / (totalCells || 1);
        const tierDist = {};
        wardData.forEach(w => { tierDist[w.hvi_tier] = (tierDist[w.hvi_tier] || 0) + 1; });
        setSummary({
          avg_hvi: avgHvi,
          tier_distribution: tierDist,
          total_cells: totalCells,
        });
        setCellCount(totalCells);
      }

      setLoading(false);
    } catch (err) {
      if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') return;
      console.error('Failed to load ward data:', err);
      setError(err.message || 'Failed to connect to backend');
      setLoading(false);
    }
  }, [year, showHeatmap]);

  // ── Load grid blocks for a specific ward (Level 2) ───────
  const loadWardBlocks = useCallback(async (ward) => {
    setLoading(true);
    setError(null);

    if (abortControllerRef.current) abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    try {
      // ~1.5 km bbox around ward center
      const R = 0.015;
      const bbox = `${ward.lng - R},${ward.lat - R},${ward.lng + R},${ward.lat + R}`;

      const [gridData, reportsData] = await Promise.all([
        fetchGrid(year, 5000, bbox, signal),
        fetchReports(true),
      ]);

      // Clear ward markers
      if (wardLayerRef.current && mapInstance.current) {
        mapInstance.current.removeLayer(wardLayerRef.current);
        wardLayerRef.current = null;
      }
      if (gridLayerRef.current && mapInstance.current) {
        mapInstance.current.removeLayer(gridLayerRef.current);
        gridLayerRef.current = null;
      }
      if (reportsLayerRef.current && mapInstance.current) {
        mapInstance.current.removeLayer(reportsLayerRef.current);
        reportsLayerRef.current = null;
      }

      const features = gridData.features || [];
      setCellCount(features.length);

      if (features.length > 0) {
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
              if (onCellSelectRef.current) onCellSelectRef.current(p);

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

              try {
                import('../../services/api').then(async ({ explainCell }) => {
                  const expl = await explainCell({
                    ndvi: p.ndvi, ndbi: p.ndbi, ndwi: p.ndwi,
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
                    const lst = p.lst_predicted ?? p.lst_observed ?? 0;
                    const maxPos = expl.contributions.reduce((prev, current) => (prev.impact > current.impact) ? prev : current);
                    const maxNeg = expl.contributions.reduce((prev, current) => (prev.impact < current.impact) ? prev : current);
                    
                    let dynamicExplanation = "";
                    if (lst > 40 && (p.hvi_score < 50)) {
                      dynamicExplanation = `Although the surface temperature is high (${lst.toFixed(1)}°C), the vulnerability score is downgraded to <strong>${p.hvi_tier}</strong> because human exposure is lower (e.g. fewer residents, or better wind/shade).<br><br>`;
                    } else if (lst < 39 && p.hvi_score >= 50) {
                      dynamicExplanation = `Even though the surface temperature is relatively moderate (${lst.toFixed(1)}°C), the vulnerability score is elevated to <strong>${p.hvi_tier}</strong> due to compounding human factors (e.g. dense population or lack of canopy).<br><br>`;
                    } else {
                      dynamicExplanation = `The score of <strong>${p.hvi_tier}</strong> reflects a balanced combination of the surface heat (${lst.toFixed(1)}°C) and the human exposure factors in this block.<br><br>`;
                    }
                    
                    if (maxPos.impact > 0.1) {
                      dynamicExplanation += `🌡️ The heat in this specific area is primarily driven by <strong>${maxPos.label.toLowerCase()}</strong>. `;
                    }
                    if (maxNeg.impact < -0.1) {
                      dynamicExplanation += `🧊 However, <strong>${maxNeg.label.toLowerCase()}</strong> is providing some cooling relief.`;
                    }

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
                        
                        <div style="margin-top: 12px;">
                          <button onclick="document.getElementById('explain-box-${p.cell_id}').style.display = 'block'; this.style.display='none'" 
                                  style="width: 100%; padding: 6px; background: transparent; border: 1px solid #475569; color: #94a3b8; border-radius: 4px; cursor: pointer; font-size: 0.75rem;">
                            Why is the score ${p.hvi_tier === 'Heat-Safe' ? 'only' : ''} ${p.hvi_tier}?
                          </button>
                          <div id="explain-box-${p.cell_id}" style="display:none; font-size: 0.75rem; color: #cbd5e1; margin-top: 8px; padding: 10px; background: #1e293b; border-radius: 4px; border: 1px solid #334155; line-height: 1.4;">
                            <strong style="color: #60a5fa; display: block; margin-bottom: 4px;">HVI vs Temperature</strong>
                            ${dynamicExplanation}
                          </div>
                        </div>
                      </div>
                    `;
                    if (layer.isPopupOpen()) layer.setPopupContent(updatedPopup);
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
              if (gridLayerRef.current) gridLayerRef.current.resetStyle(layer);
            });
          },
        });

        if (mapInstance.current && showHeatmap) {
          gridLayerRef.current.addTo(mapInstance.current);
        }
      }

      // Add reports
      addReportsLayer(reportsData);

      // Compute block-level summary
      if (features.length > 0) {
        const scores = features.map(f => f.properties.hvi_score);
        const avgHvi = scores.reduce((a, b) => a + b, 0) / scores.length;
        const tierDist = {};
        features.forEach(f => {
          const t = f.properties.hvi_tier;
          tierDist[t] = (tierDist[t] || 0) + 1;
        });
        setSummary({ avg_hvi: avgHvi, tier_distribution: tierDist, total_cells: features.length });
      }

      // Zoom to ward
      if (mapInstance.current) {
        mapInstance.current.flyTo([ward.lat, ward.lng], 15, { duration: 0.8 });
      }

      setLoading(false);
    } catch (err) {
      if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') return;
      console.error('Failed to load block data:', err);
      setError(err.message || 'Failed to load ward blocks');
      setLoading(false);
    }
  }, [year, showHeatmap]); // Removed onCellSelect to prevent infinite re-render

  // Helper: add verified reports markers
  const addReportsLayer = (reportsData) => {
    if (!reportsData || !reportsData.features || reportsData.features.length === 0) return;

    reportsLayerRef.current = L.geoJSON(reportsData, {
      pointToLayer: (feature, latlng) => {
        const iconHtml = `
          <div style="
            background: #ef4444; border: 2px solid white; color: white;
            width: 24px; height: 24px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 0 10px rgba(0,0,0,0.5);
            font-weight: bold; font-size: 14px;
          ">!</div>
        `;
        return L.marker(latlng, {
          icon: L.divIcon({
            html: iconHtml, className: 'custom-report-marker',
            iconSize: [24, 24], iconAnchor: [12, 12]
          })
        });
      },
      onEachFeature: (feature, layer) => {
        const p = feature.properties;
        layer.bindPopup(`
          <div class="cell-popup">
            <h4 style="margin-bottom:4px; color:#60a5fa;">Verified Report</h4>
            <div style="font-size:0.85rem; color:#f8fafc; margin-bottom:8px;">
              <strong>Category:</strong> ${p.category.replace(/_/g, ' ')}
            </div>
            <div class="popup-metrics">
              <div class="popup-metric"><span class="metric-label">Heat</span><span class="metric-value">${p.heat_impact_rating}/5</span></div>
              <div class="popup-metric"><span class="metric-label">Shade</span><span class="metric-value">${p.shade_rating}/5</span></div>
              <div class="popup-metric"><span class="metric-label">Water</span><span class="metric-value">${p.water_rating}/5</span></div>
            </div>
          </div>
        `, { maxWidth: 250, className: 'dark-popup' });
      }
    });

    if (mapInstance.current) reportsLayerRef.current.addTo(mapInstance.current);
  };

  // ── Drill-down handler (called from popup button) ────────
  const drillIntoWard = useCallback((wardId) => {
    const ward = WARDS.find(w => w.id === wardId);
    if (!ward) return;
    // Close any open popup
    if (mapInstance.current) mapInstance.current.closePopup();
    setSelectedWard(ward);
    setViewMode('blocks');
  }, []);

  // Expose drill-down to popup buttons
  useEffect(() => {
    window.__drillIntoWard = drillIntoWard;
    return () => { delete window.__drillIntoWard; };
  }, [drillIntoWard]);

  // ── Back to wards handler ────────────────────────────────
  const backToWards = useCallback(() => {
    setSelectedWard(null);
    setViewMode('wards');
    if (mapInstance.current) {
      mapInstance.current.flyTo(PUNE_CENTER, 12, { duration: 0.8 });
    }
  }, []);

  // ── React to viewMode / year changes ─────────────────────
  useEffect(() => {
    if (!mapInstance.current) return;
    if (viewMode === 'wards') {
      loadWards();
    } else if (viewMode === 'blocks' && selectedWard) {
      loadWardBlocks(selectedWard);
    }
  }, [viewMode, year, selectedWard, loadWards, loadWardBlocks]);

  // Toggle heatmap visibility
  useEffect(() => {
    if (!mapInstance.current) return;
    const layer = viewMode === 'wards' ? wardLayerRef.current : gridLayerRef.current;
    if (!layer) return;
    if (showHeatmap) {
      if (!mapInstance.current.hasLayer(layer)) layer.addTo(mapInstance.current);
    } else {
      if (mapInstance.current.hasLayer(layer)) mapInstance.current.removeLayer(layer);
    }
  }, [showHeatmap, viewMode]);

  return (
    <div className="map-wrapper">
      <div ref={mapRef} className="map-container" />

      {/* Loading overlay */}
      {loading && (
        <div className="map-loading">
          <div className="spinner" />
          <p>{viewMode === 'wards' ? 'Loading ward data…' : `Loading blocks for ${selectedWard?.name}…`}</p>
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="map-error">
          <div className="error-icon">⚠️</div>
          <h3>Connection Error</h3>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={() => viewMode === 'wards' ? loadWards() : loadWardBlocks(selectedWard)}>Retry</button>
        </div>
      )}

      {/* KPI Overlay */}
      {summary && !loading && showHeatmap && (
        <div className="kpi-overlay glass-panel">
          <div className="kpi-header">
            <h4>PUNE HEAT STATUS</h4>
          </div>
          <div className="kpi-grid">
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
              <span className="label">{viewMode === 'wards' ? 'Wards' : 'Blocks'}</span>
              <span className="value">{viewMode === 'wards' ? wardSummaries.length : cellCount.toLocaleString()}</span>
            </div>
          </div>
        </div>
      )}

      {/* Secondary Controls (Back Button & Ward Name) */}
      {viewMode === 'blocks' && selectedWard && (
        <div className="ward-controls-overlay">
          <button onClick={backToWards} className="btn-back-wards">
            ← Back to Wards
          </button>
          
          {!loading && (
            <div className="ward-name-badge">
              Ward {selectedWard.id}: {selectedWard.name}
            </div>
          )}
        </div>
      )}

      {/* Normal / Heatmap toggle */}
      <div className="map-toggle-overlay">
        <button
          onClick={() => setShowHeatmap(false)}
          className={`toggle-btn ${!showHeatmap ? 'active' : ''}`}
        >
          🗺️ Base
        </button>
        <button
          onClick={() => setShowHeatmap(true)}
          className={`toggle-btn ${showHeatmap ? 'active-heat' : ''}`}
        >
          🌡️ Heat
        </button>
      </div>

      {/* Year selector / Timeline */}
      <div className="year-timeline glass-panel">
        <div className="timeline-track">
          {YEARS.map((y, idx) => (
            <div key={y} className="timeline-node">
              <button
                className={`year-dot ${y === year ? 'active' : ''}`}
                onClick={() => setYear(y)}
              />
              <span className={`year-label ${y === year ? 'active' : ''}`}>{y}</span>
              {idx < YEARS.length - 1 && <div className="timeline-line" />}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
