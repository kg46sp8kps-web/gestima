import { apiClient } from './client'
import type { CuttingConditionCell, CuttingConditionPivotResponse, CuttingConditionUpdate } from '@/types/cutting-condition'

export async function getPivot(mode: 'low' | 'mid' | 'high' = 'mid'): Promise<CuttingConditionPivotResponse> {
  const { data } = await apiClient.get<CuttingConditionPivotResponse>('/cutting-conditions/pivot', { params: { mode } })
  return data
}

export async function update(id: number, payload: CuttingConditionUpdate): Promise<CuttingConditionCell> {
  const { data } = await apiClient.put<CuttingConditionCell>(`/cutting-conditions/${id}`, payload)
  return data
}
