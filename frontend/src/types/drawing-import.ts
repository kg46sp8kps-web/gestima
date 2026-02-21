/**
 * Drawing Import types (mirrors backend schemas/drawing_import.py)
 */

export interface ShareFileInfo {
  filename: string
  file_size: number
  file_type: string // "pdf" | "step"
}

export interface ShareFolderPreview {
  folder_name: string
  matched_part_id: number | null
  matched_part_number: string | null
  matched_article_number: string | null
  pdf_files: ShareFileInfo[]
  step_files: ShareFileInfo[]
  primary_pdf: string | null
  already_imported: boolean
  status: 'ready' | 'no_match' | 'already_imported' | 'no_pdf'
}

export interface DrawingImportPreviewResponse {
  share_path: string
  total_folders: number
  matched: number
  unmatched: number
  already_imported: number
  ready: number
  no_pdf: number
  skipped: number
  folders: ShareFolderPreview[]
}

export interface ShareStatusResponse {
  share_path: string
  is_accessible: boolean
  total_folders: number
  message: string
}

export interface ImportFolderRequest {
  folder_name: string
  part_id: number
  primary_pdf: string
  import_step: boolean
}

export interface DrawingImportExecuteRequest {
  folders: ImportFolderRequest[]
}

export interface DrawingImportExecuteResponse {
  success: boolean
  files_created: number
  links_created: number
  parts_updated: number
  skipped: number
  errors: string[]
}
