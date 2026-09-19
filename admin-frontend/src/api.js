import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'https://thermacity-backend.onrender.com/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.response?.status, error.message);
    return Promise.reject(error);
  }
);

export async function fetchUnverifiedReports() {
  const { data } = await api.get('/reports', { params: { is_verified: false } });
  return data;
}

export async function fetchVerifiedReports() {
  const { data } = await api.get('/reports', { params: { is_verified: true } });
  return data;
}

export async function verifyReport(id) {
  const { data } = await api.patch(`/reports/${id}/verify`);
  return data;
}

export async function deleteReport(id) {
  const { data } = await api.delete(`/reports/${id}`);
  return data;
}

export default api;
