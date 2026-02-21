/**
 * Infor Sync Types
 *
 * Types for the Infor automatic sync dashboard.
 */

export interface SyncState {
  id: number
  step_name: string
  ido_name: string
  filter_template: string
  properties: string
  date_field: string
  interval_seconds: number
  enabled: boolean
  last_sync_at: string | null
  last_error: string | null
  created_count: number
  updated_count: number
  error_count: number
  created_at: string
  updated_at: string
}

export interface SyncLog {
  id: number
  step_name: string
  status: 'success' | 'error' | 'skipped'
  fetched_count: number
  created_count: number
  updated_count: number
  error_count: number
  duration_ms: number | null
  error_message: string | null
  created_at: string
}

export interface SyncStatusResponse {
  running: boolean
  steps: SyncState[]
}

export interface SyncTriggerResponse {
  status: string
  step_name: string
  fetched: number
  created: number
  updated: number
  errors: number
  duration_ms: number
}
