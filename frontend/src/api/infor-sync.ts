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
