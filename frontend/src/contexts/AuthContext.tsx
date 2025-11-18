import { createContext, useState, useEffect, ReactNode, FC } from 'react';
import { CurrentUser } from '../types';
import { apiClient } from '../api/client';

interface AuthContextType {
  user: CurrentUser | null;
  loading: boolean;
  login: (tokens: { user_id: string; access_token?: string; refresh_token?: string }) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = async (userId: string): Promise<void> => {
    try {
      const response = await apiClient.get<CurrentUser>('/api/v1/auth/user', {
        headers: { 'X-User-Id': userId }
      });
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      throw error;
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const userId = localStorage.getItem('discord_user_id');

      if (userId) {
        try {
          await fetchUser(userId);
        } catch (error) {
          console.error('Failed to initialize auth:', error);
          localStorage.removeItem('discord_user_id');
        }
      }

      setLoading(false);
    };

    initAuth();
  }, []);

  const login = (tokens: { user_id: string; access_token?: string; refresh_token?: string }) => {
    localStorage.setItem('discord_user_id', tokens.user_id);
    
    // Fetch full user data after login
    fetchUser(tokens.user_id).catch(err => {
      console.error('Failed to fetch user after login:', err);
      // Set minimal user object on error
      setUser({ id: tokens.user_id, username: 'Loading...', discordId: tokens.user_id });
    });
  };

  const refreshUser = async () => {
    const userId = localStorage.getItem('discord_user_id');
    if (userId) {
      await fetchUser(userId);
    }
  };

  const logout = async () => {
    const userId = localStorage.getItem('discord_user_id');
    
    if (userId) {
      try {
        await apiClient.post('/api/v1/auth/logout');
      } catch (error) {
        console.error('Logout API call failed:', error);
      }
    }
    
    localStorage.removeItem('discord_user_id');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};
