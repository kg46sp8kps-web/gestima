import { apiClient } from './client'
import type { FileWithLinks, FileListResponse } from '@/types/file-record'

export async function listByEntity(entityType: string, entityId: number): Promise<FileWithLinks[]> {
  const { data } = await apiClient.get<FileListResponse>('/files', {
    params: { entity_type: entityType, entity_id: entityId, status: 'active' },
  })
  return data.files
}

export async function list(limit = 200): Promise<FileWithLinks[]> {
  const { data } = await apiClient.get<FileListResponse>('/files', {
    params: { status: 'active', limit },
  })
  return data.files
}

export function previewUrl(fileId: number): string {
  return `/api/files/${fileId}/preview`
}
