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
