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
  scheduled_at: string;
  scheduled_at_unix: number;
  max_players: number | null;
  guild_id: string;
  channel_id: string;
  message_id: string | null;
  host_id: string;
  host_discord_id: string;
  rules: string | null;
  reminder_minutes: number[] | null;
  status: 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
  participant_count: number;
  participants?: Participant[];
  created_at: string;
  updated_at: string;
}

export interface Participant {
  id: string;
  game_session_id: string;
  user_id: string | null;
  discord_id: string | null;
  display_name: string | null;
  joined_at: string;
  status: 'JOINED' | 'DROPPED' | 'WAITLIST' | 'PLACEHOLDER';
  is_pre_populated: boolean;
}

export interface GameListResponse {
  games: GameSession[];
  total: number;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export interface CurrentUser {
  id: string;
  user_uuid: string;
  username: string;
  discordId?: string;  // For backward compatibility
  discriminator?: string;
  avatar?: string | null;
  guilds?: DiscordGuild[];
}

export interface DiscordGuild {
  id: string;
  name: string;
  icon: string | null;
  owner: boolean;
  permissions: string;
}
