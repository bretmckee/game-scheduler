// Copyright 2025 Bret McKee (bret.mckee@gmail.com)
//
// This file is part of Game_Scheduler. (https://github.com/game-scheduler)
//
// Game_Scheduler is free software: you can redistribute it and/or
// modify it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or (at your
// option) any later version.
//
// Game_Scheduler is distributed in the hope that it will be
// useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
// Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License along
// with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


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
