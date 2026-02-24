import { apiClient } from './client'
import type { SyncStatus, SyncLogsResponse } from '@/types/infor-sync'

export async function getStatus(): Promise<SyncStatus> {
  const { data } = await apiClient.get<SyncStatus>('/infor/sync/status')
  return data
}

export async function getLogs(params?: { skip?: number; limit?: number }): Promise<SyncLogsResponse> {
  const { data } = await apiClient.get<SyncLogsResponse>('/infor/sync/logs', { params })
  return data
}

export async function triggerStep(stepName: string): Promise<{ created: number; updated: number; errors: number }> {
  const { data } = await apiClient.post<{ created: number; updated: number; errors: number }>(
    `/infor/sync/trigger/${stepName}`,
  )
  return data
}

export async function updateStep(stepName: string, payload: { enabled: boolean }): Promise<void> {
  await apiClient.put(`/infor/sync/steps/${stepName}`, payload)
}

export async function startSync(): Promise<void> {
  await apiClient.post('/infor/sync/start')
}

export async function stopSync(): Promise<void> {
  await apiClient.post('/infor/sync/stop')
}
