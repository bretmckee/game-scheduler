import { createContext, useState, useEffect, ReactNode, FC } from 'react';
import { CurrentUser } from '../types';
import { apiClient } from '../api/client';

interface AuthContextType {
  user: CurrentUser | null;
  loading: boolean;
  login: (tokens: { access_token: string; refresh_token: string; user_id: string }) => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('discord_access_token');
      const userId = localStorage.getItem('discord_user_id');

      if (token && userId) {
        try {
          const response = await apiClient.get<CurrentUser>('/api/v1/auth/user');
          setUser(response.data);
        } catch (error) {
          console.error('Failed to fetch user:', error);
          localStorage.removeItem('discord_access_token');
          localStorage.removeItem('discord_refresh_token');
          localStorage.removeItem('discord_user_id');
        }
      }

      setLoading(false);
    };

    initAuth();
  }, []);

  const login = (tokens: { access_token: string; refresh_token: string; user_id: string }) => {
    localStorage.setItem('discord_access_token', tokens.access_token);
    localStorage.setItem('discord_refresh_token', tokens.refresh_token);
    localStorage.setItem('discord_user_id', tokens.user_id);
    setUser({ discordId: tokens.user_id });
  };

  const logout = () => {
    localStorage.removeItem('discord_access_token');
    localStorage.removeItem('discord_refresh_token');
    localStorage.removeItem('discord_user_id');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
