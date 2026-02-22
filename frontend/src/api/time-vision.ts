import { apiClient } from './client'
import type { TimeVisionListItem } from '@/types/admin-user'

export async function listEstimations(limit = 100): Promise<TimeVisionListItem[]> {
  const { data } = await apiClient.get<TimeVisionListItem[]>('/time-vision/estimations', {
    params: { limit },
  })
  return data
}
