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

import { apiClient } from './client';
import { GameTemplate, TemplateCreateRequest, TemplateUpdateRequest } from '../types';

export const getTemplates = async (guildId: string): Promise<GameTemplate[]> => {
  const response = await apiClient.get<GameTemplate[]>(`/api/v1/guilds/${guildId}/templates`);
  return response.data;
};

export const getTemplate = async (templateId: string): Promise<GameTemplate> => {
  const response = await apiClient.get<GameTemplate>(`/api/v1/templates/${templateId}`);
  return response.data;
};

export const createTemplate = async (template: TemplateCreateRequest): Promise<GameTemplate> => {
  const response = await apiClient.post<GameTemplate>(
    `/api/v1/guilds/${template.guild_id}/templates`,
    template
  );
  return response.data;
};

export const updateTemplate = async (
  templateId: string,
  updates: TemplateUpdateRequest
): Promise<GameTemplate> => {
  const response = await apiClient.put<GameTemplate>(`/api/v1/templates/${templateId}`, updates);
  return response.data;
};

export const deleteTemplate = async (templateId: string): Promise<void> => {
  await apiClient.delete(`/api/v1/templates/${templateId}`);
};

export const setDefaultTemplate = async (templateId: string): Promise<GameTemplate> => {
  const response = await apiClient.post<GameTemplate>(
    `/api/v1/templates/${templateId}/set-default`
  );
  return response.data;
};

export const reorderTemplates = async (templateIds: string[]): Promise<void> => {
  await apiClient.post('/api/v1/templates/reorder', { template_ids: templateIds });
};
