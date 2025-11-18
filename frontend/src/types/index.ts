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


export interface User {
  discordId: string;
  createdAt: string;
  updatedAt: string;
}

export interface Guild {
  id: string;
  guildId: string;
  guildName: string;
  defaultMaxPlayers: number;
  defaultReminderMinutes: number[];
  defaultRules: string;
  allowedHostRoleIds: string[];
  requireHostRole: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Channel {
  id: string;
  guildId: string;
  channelId: string;
  channelName: string;
  isActive: boolean;
  maxPlayers: number | null;
  reminderMinutes: number[] | null;
  defaultRules: string | null;
  allowedHostRoleIds: string[] | null;
  gameCategory: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface GameSession {
  id: string;
  title: string;
  description: string;
  scheduledAt: string;
  maxPlayers: number | null;
  guildId: string;
  channelId: string;
  messageId: string | null;
  hostId: string;
  rules: string | null;
  reminderMinutes: number[] | null;
  status: 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
  createdAt: string;
  updatedAt: string;
  participants?: Participant[];
}

export interface Participant {
  id: string;
  gameSessionId: string;
  userId: string | null;
  discordId: string | null;
  displayName: string | null;
  joinedAt: string;
  status: 'JOINED' | 'DROPPED' | 'WAITLIST' | 'PLACEHOLDER';
  isPrePopulated: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export interface CurrentUser {
  discordId: string;
  username?: string;
  discriminator?: string;
  avatar?: string;
  guilds?: DiscordGuild[];
}

export interface DiscordGuild {
  id: string;
  name: string;
  icon: string | null;
  owner: boolean;
  permissions: string;
}
