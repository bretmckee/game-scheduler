import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false,
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('discord_access_token');
    const userId = localStorage.getItem('discord_user_id');
    
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    if (userId && config.headers) {
      config.headers['X-User-Id'] = userId;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('discord_refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token } = response.data;
          localStorage.setItem('discord_access_token', access_token);

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          localStorage.removeItem('discord_access_token');
          localStorage.removeItem('discord_refresh_token');
          localStorage.removeItem('discord_user_id');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }

      window.location.href = '/login';
    }

    return Promise.reject(error);
  }
);
