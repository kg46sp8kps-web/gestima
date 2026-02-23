import { apiClient } from './client'
import type { WorkCenter, WorkCenterUpdate } from '@/types/work-center'

export async function getAll(): Promise<WorkCenter[]> {
  const { data } = await apiClient.get<WorkCenter[]>('/work-centers/')
  return data
}

export async function update(wcNumber: string, payload: WorkCenterUpdate): Promise<WorkCenter> {
  const { data } = await apiClient.put<WorkCenter>(`/work-centers/${wcNumber}`, payload)
  return data
}
