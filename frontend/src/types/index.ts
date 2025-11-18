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
  id: string;
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
