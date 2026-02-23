import { apiClient } from './client'
import type { FileWithLinks, FileListResponse } from '@/types/file-record'

interface FileUploadResponse { file: FileWithLinks }

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

export async function upload(
  file: File,
  entityType: string,
  entityId: number,
  linkType: string = 'drawing',
): Promise<FileWithLinks> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('directory', `${entityType}s/${entityId}`)
  formData.append('entity_type', entityType)
  formData.append('entity_id', String(entityId))
  formData.append('link_type', linkType)
  const { data } = await apiClient.post<FileUploadResponse>('/files/upload', formData)
  return data.file
}

export async function deleteFile(fileId: number): Promise<void> {
  await apiClient.delete(`/files/${fileId}`)
}
