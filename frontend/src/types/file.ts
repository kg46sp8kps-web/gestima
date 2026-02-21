/**
 * GESTIMA - File Manager TypeScript Types
 *
 * Types for centralized file management (ADR-044).
 * Maps to backend schemas in app/schemas/file_record.py
 */

export interface FileRecord {
  id: number
  file_hash: string
  file_path: string
  original_filename: string
  file_size: number
  file_type: string
  mime_type: string
  status: 'temp' | 'active' | 'archived'
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}

export interface FileLink {
  id: number
  file_id: number
  entity_type: string
  entity_id: number
  entity_name: string | null
  is_primary: boolean
  revision: string | null
  link_type: string
  created_at: string
  created_by: string | null
}

export interface FileWithLinks extends FileRecord {
  links: FileLink[]
}

export interface FileListResponse {
  files: FileWithLinks[]
  total: number
}

export interface FileLinkRequest {
  entity_type: string
  entity_id: number
  is_primary?: boolean
  revision?: string
  link_type?: string
}

export interface FileUploadOptions {
  directory?: string
  entity_type?: string
  entity_id?: number
  is_primary?: boolean
  revision?: string
  link_type?: string
}

export interface FileUploadResponse extends FileRecord {
  link: FileLink | null
}

export interface FileFilters {
  entity_type?: string
  entity_id?: number
  file_type?: string
  status?: string
}
