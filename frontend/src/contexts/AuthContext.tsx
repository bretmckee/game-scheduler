import { createContext, useState, useEffect, ReactNode, FC } from 'react';
import { CurrentUser } from '../types';
import { apiClient } from '../api/client';

interface AuthContextType {
  user: CurrentUser | null;
  loading: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = async (): Promise<void> => {
    try {
      const response = await apiClient.get<CurrentUser>('/api/v1/auth/user');
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      throw error;
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      try {
        await fetchUser();
      } catch (error) {
        console.error('Failed to initialize auth:', error);
      }

      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async () => {
    await fetchUser();
  };

  const refreshUser = async () => {
    await fetchUser();
  };

  const logout = async () => {
    try {
      await apiClient.post('/api/v1/auth/logout');
    } catch (error) {
      console.error('Logout API call failed:', error);
    }
    
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};
