import { apiClient } from './client'
import type { ProductionRecord } from '@/types/production-record'

export async function getByPartId(partId: number): Promise<ProductionRecord[]> {
  const { data } = await apiClient.get<ProductionRecord[]>(`/production-records/part/${partId}`)
  return data
}
