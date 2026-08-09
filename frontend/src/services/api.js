import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

// Response interceptor for error logging
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.response?.status, error.message);
    return Promise.reject(error);
  }
);

// ── Grid & Summary ──────────────────────────────────────────

export async function fetchGrid(year = 2024, limit = 36000, bbox = null, signal = null) {
  const params = { year, limit };
  if (bbox) params.bbox = bbox;
  const { data } = await api.get('/demo/grid', { params, signal });
  return data;
}

export async function fetchHVISummary(year = 2024, signal = null) {
  const { data } = await api.get('/demo/summary', { params: { year }, signal });
  return data;
}

// ── Prediction & Simulation ─────────────────────────────────

export async function predictLST(features) {
  const { data } = await api.post('/demo/predict', features);
  return data;
}

export async function simulateScenario(params) {
  const { data } = await api.post('/demo/simulate', params);
  return data;
}

// ── SHAP Explainability ─────────────────────────────────────

export async function explainCell(features) {
  const { data } = await api.post('/demo/explain', features);
  return data;
}

// ── PDF Report Download ─────────────────────────────────────

export async function downloadReport(year = 2024) {
  const response = await api.get('/reports/download', {
    params: { year },
    responseType: 'blob',
  });
  
  // Create download link
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `ThermaCity_Report_${year}.pdf`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export async function downloadCellReport(payload) {
  const response = await api.post('/demo/report/cell', payload, {
    responseType: 'blob',
  });
  
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `thermacity_block_${payload.cell_id}.pdf`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export default api;
