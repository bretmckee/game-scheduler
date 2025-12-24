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

import { StatusCodes } from 'http-status-codes';
import { apiClient } from '../api/client';

/**
 * Check if user has permission to create games on a guild by checking template access.
 * Returns true if user has access to at least one template, false otherwise.
 */
export async function canUserCreateGames(guildId: string): Promise<boolean> {
  try {
    const templates = await apiClient.get(`/api/v1/guilds/${guildId}/templates`);
    return templates.data && templates.data.length > 0;
  } catch {
    // User has no accessible templates (403 or other error)
    return false;
  }
}

/**
 * Check if user has bot manager permissions for a guild.
 * Bot managers can manage templates, channels, and have elevated permissions.
 * Returns true if user has bot manager role or MANAGE_GUILD permission.
 */
export async function canUserManageBotSettings(guildId: string): Promise<boolean> {
  try {
    const response = await apiClient.get(`/api/v1/guilds/${guildId}/config`);
    return response.status === StatusCodes.OK;
  } catch (error: any) {
    if (error.response?.status === StatusCodes.FORBIDDEN) {
      return false;
    }
    return false;
  }
}
