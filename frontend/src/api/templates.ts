// Copyright 2025-2026 Bret McKee
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

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
