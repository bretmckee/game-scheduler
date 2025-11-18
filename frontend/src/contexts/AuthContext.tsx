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
