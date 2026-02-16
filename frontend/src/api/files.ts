/**
 * GESTIMA - Files API Client
 *
 * API client for centralized file management (ADR-044).
 * Calls /api/files/ endpoints on backend.
 */

import { apiClient } from './client'
import type {
  FileRecord,
  FileWithLinks,
  FileListResponse,
  FileLinkRequest,
  FileUploadResponse,
  FileFilters
} from '@/types/file'

const BASE_PATH = '/files'

export const filesApi = {
  /**
   * List files with optional filters
   */
  async list(params?: FileFilters): Promise<FileListResponse> {
    const response = await apiClient.get<FileListResponse>(BASE_PATH, { params })
    return response.data
  },

  /**
   * Get single file with links
   */
  async get(fileId: number): Promise<FileWithLinks> {
    const response = await apiClient.get<FileWithLinks>(`${BASE_PATH}/${fileId}`)
    return response.data
  },

  /**
   * Get download URL for file (returns URL string, not fetch call)
   */
  getDownloadUrl(fileId: number): string {
    return `${apiClient.defaults.baseURL}${BASE_PATH}/${fileId}/download`
  },

  /**
   * Get preview URL for PDF (no auth required — usable in iframe/pdf.js)
   */
  getPreviewUrl(fileId: number): string {
    return `${apiClient.defaults.baseURL}${BASE_PATH}/${fileId}/preview`
  },

  /**
   * Upload file
   */
  async upload(
    file: File,
    options?: {
      directory?: string
      entity_type?: string
      entity_id?: number
      is_primary?: boolean
      revision?: string
      link_type?: string
    }
  ): Promise<FileUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)

    if (options?.directory) formData.append('directory', options.directory)
    if (options?.entity_type) formData.append('entity_type', options.entity_type)
    if (options?.entity_id !== undefined) formData.append('entity_id', String(options.entity_id))
    if (options?.is_primary !== undefined) formData.append('is_primary', String(options.is_primary))
    if (options?.revision) formData.append('revision', options.revision)
    if (options?.link_type) formData.append('link_type', options.link_type)

    const response = await apiClient.post<FileUploadResponse>(`${BASE_PATH}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response.data
  },

  /**
   * Delete file (soft delete)
   */
  async delete(fileId: number): Promise<void> {
    await apiClient.delete(`${BASE_PATH}/${fileId}`)
  },

  /**
   * Link file to entity
   */
  async link(fileId: number, data: FileLinkRequest): Promise<{ id: number; message: string }> {
    const response = await apiClient.post<{ id: number; message: string }>(
      `${BASE_PATH}/${fileId}/link`,
      data
    )
    return response.data
  },

  /**
   * Unlink file from entity
   */
  async unlink(fileId: number, entityType: string, entityId: number): Promise<void> {
    await apiClient.delete(`${BASE_PATH}/${fileId}/link/${entityType}/${entityId}`)
  },

  /**
   * Set file as primary for entity
   */
  async setPrimary(fileId: number, entityType: string, entityId: number): Promise<void> {
    await apiClient.put(`${BASE_PATH}/${fileId}/primary/${entityType}/${entityId}`)
  },

  /**
   * Get orphan files (admin)
   */
  async getOrphans(): Promise<FileListResponse> {
    const response = await apiClient.get<FileListResponse>(`${BASE_PATH}/orphans`)
    return response.data
  }
}
