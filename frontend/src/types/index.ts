export interface User {
  discordId: string;
  createdAt: string;
  updatedAt: string;
}

export interface Guild {
  id: string;
  guild_id: string;
  guild_name: string;
  default_max_players: number;
  default_reminder_minutes: number[];
  default_rules: string;
  allowed_host_role_ids: string[];
  require_host_role: boolean;
  created_at: string;
  updated_at: string;
}

export interface Channel {
  id: string; // Database UUID (use for navigation and API calls)
  guild_id: string;
  channel_id: string; // Discord snowflake (internal only)
  channel_name: string;
  is_active: boolean;
  max_players: number | null;
  reminder_minutes: number[] | null;
  default_rules: string | null;
  allowed_host_role_ids: string[] | null;
  game_category: string | null;
  created_at: string;
  updated_at: string;
}

export interface GameSession {
  id: string;
  title: string;
  description: string;
  scheduled_at: string;
  scheduled_at_unix: number;
  min_players: number | null;
  max_players: number | null;
  guild_id: string;
  channel_id: string;
  message_id: string | null;
  host: Participant;
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
