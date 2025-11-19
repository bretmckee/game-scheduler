import axios from 'axios';

// In development, use empty baseURL to leverage Vite's proxy configuration
// In production (Docker), use the configured API URL
const API_BASE_URL = import.meta.env.MODE === 'development' 
  ? '' 
  : (import.meta.env.VITE_API_URL || 'http://localhost:8000');

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        await apiClient.post('/api/v1/auth/refresh');
        return apiClient(originalRequest);
      } catch (refreshError) {
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);
