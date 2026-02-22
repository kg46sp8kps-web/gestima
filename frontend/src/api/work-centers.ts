import { apiClient } from './client'
import type { WorkCenter } from '@/types/work-center'

export async function getAll(): Promise<WorkCenter[]> {
  const { data } = await apiClient.get<WorkCenter[]>('/work-centers/')
  return data
}
