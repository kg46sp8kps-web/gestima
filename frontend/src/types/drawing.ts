/**
 * Drawing Types
 *
 * Represents PDF technical drawings attached to parts.
 * Each part can have multiple drawings with one marked as primary.
 */

export interface Drawing {
  id: number
  part_id: number
  filename: string
  file_hash: string
  file_size: number
  file_path: string
  is_primary: boolean
  file_type: 'pdf' | 'step'
  revision: string
  created_at: string
  updated_at: string
  created_by: string | null
  version: number
  /** Whether the file physically exists on disk (false = orphan record) */
  file_exists: boolean
}

export interface DrawingListResponse {
  drawings: Drawing[]
  primary_id: number | null
}

export interface DrawingUploadRequest {
  file: File
  revision?: string
}

export interface DrawingResponse {
  message: string
  drawing: Drawing
}
