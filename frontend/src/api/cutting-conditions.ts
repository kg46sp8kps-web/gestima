/**
 * Cutting Conditions API
 */
import { apiClient } from './client'
import type { PivotResponse, CuttingConditionUpdate, CuttingConditionResponse } from '@/types/cutting-condition'

export async function getCuttingConditionsPivot(mode: string = 'mid'): Promise<PivotResponse> {
  const response = await apiClient.get<PivotResponse>('/cutting-conditions/pivot', {
    params: { mode }
  })
  return response.data
}

export async function updateCuttingCondition(id: number, data: CuttingConditionUpdate): Promise<CuttingConditionResponse> {
  const response = await apiClient.put<CuttingConditionResponse>(`/cutting-conditions/${id}`, data)
  return response.data
}

export async function seedCuttingConditions(): Promise<{ message: string; count: number }> {
  const response = await apiClient.post<{ message: string; count: number }>('/cutting-conditions/seed')
  return response.data
}
