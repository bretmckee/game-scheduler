import axios from 'axios';

// Use empty baseURL to leverage proxy configuration (Vite dev server or nginx)
// Only use VITE_API_URL if explicitly set for external API access
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

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

    // Skip interceptor logic if we're already on login or callback pages
    const isAuthPage =
      window.location.pathname === '/login' ||
      window.location.pathname === '/auth/callback' ||
      window.location.pathname === '/';

    // Don't retry if this is already a retry, or if this is the refresh endpoint itself
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/refresh') &&
      !isAuthPage
    ) {
      originalRequest._retry = true;

      try {
        await apiClient.post('/api/v1/auth/refresh');
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed, redirect to login
        window.location.href = '/login';
        return new Promise(() => {}); // Never resolves, prevents further processing
      }
    }

    // For 401 on refresh endpoint or already retried requests, redirect to login (unless already on login page)
    if (error.response?.status === 401 && !isAuthPage) {
      window.location.href = '/login';
      return new Promise(() => {}); // Never resolves, prevents further processing
    }

    return Promise.reject(error);
  }
);
