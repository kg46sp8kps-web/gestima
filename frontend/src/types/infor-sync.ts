export interface SyncState {
  id: number
  step_name: string
  ido_name: string
  interval_seconds: number
  enabled: boolean
  last_sync_at: string | null
  last_error: string | null
  created_count: number
  updated_count: number
  error_count: number
}

export interface SyncLog {
  id: number
  step_name: string
  status: string
  fetched_count: number
  created_count: number
  updated_count: number
  error_count: number
  duration_ms: number | null
  error_message: string | null
  created_at: string
}

export interface SyncStatus {
  running: boolean
  steps: SyncState[]
}

export interface SyncLogsResponse {
  items: SyncLog[]
  total: number
}

export interface ImportPreviewRow {
  [key: string]: string | number | boolean | null
}

export interface ImportPreviewResponse {
  valid_count: number
  error_count: number
  duplicate_count: number
  rows: ImportPreviewRow[]
}

export interface ImportExecuteResponse {
  success: boolean
  created_count: number
  updated_count: number
  skipped_count: number
  errors: string[]
}
