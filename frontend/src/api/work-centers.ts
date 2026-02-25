import { apiClient } from './client'
import type { WorkCenter, WorkCenterCreate, WorkCenterUpdate } from '@/types/work-center'

export async function getAll(): Promise<WorkCenter[]> {
  const { data } = await apiClient.get<WorkCenter[]>('/work-centers/')
  return data
}

export async function create(payload: WorkCenterCreate): Promise<WorkCenter> {
  const { data } = await apiClient.post<WorkCenter>('/work-centers/', payload)
  return data
}

export async function update(wcNumber: string, payload: WorkCenterUpdate): Promise<WorkCenter> {
  const { data } = await apiClient.put<WorkCenter>(`/work-centers/${wcNumber}`, payload)
  return data
}

export async function deleteWc(wcNumber: string): Promise<void> {
  await apiClient.delete(`/work-centers/${wcNumber}`)
}
