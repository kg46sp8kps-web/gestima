/**
 * Infor Sync API Client
 *
 * API endpoints for automatic Infor sync status and control.
 */

import { apiClient } from './client'
import type {
  SyncStatusResponse,
  SyncLog,
  SyncState,
  SyncTriggerResponse
} from '@/types/infor-sync'

/**
 * Get sync daemon status and step states
 */
export async function getSyncStatus(): Promise<SyncStatusResponse> {
  const { data } = await apiClient.get<SyncStatusResponse>('/infor/sync/status')
  return data
}

/**
 * Get recent sync logs
 * @param limit - Number of logs to return (default 50)
 */
export async function getSyncLogs(limit = 50): Promise<SyncLog[]> {
  const { data } = await apiClient.get<SyncLog[]>('/infor/sync/logs', { params: { limit } })
  return data
}

/**
 * Manually trigger a sync step
 * @param stepName - Name of the sync step to trigger
 */
export async function triggerSyncStep(stepName: string): Promise<SyncTriggerResponse> {
  const { data } = await apiClient.post<SyncTriggerResponse>(`/infor/sync/trigger/${stepName}`)
  return data
}

/**
 * Update sync step configuration
 * @param stepName - Name of the sync step
 * @param update - Partial update (enabled and/or interval_seconds)
 */
export async function updateSyncStep(
  stepName: string,
  update: Partial<Pick<SyncState, 'enabled' | 'interval_seconds'>>
): Promise<SyncState> {
  const { data } = await apiClient.put<SyncState>(`/infor/sync/steps/${stepName}`, update)
  return data
}

/**
 * Start the sync daemon
 */
export async function startSync(): Promise<void> {
  await apiClient.post('/infor/sync/start')
}

/**
 * Stop the sync daemon
 */
export async function stopSync(): Promise<void> {
  await apiClient.post('/infor/sync/stop')
}
