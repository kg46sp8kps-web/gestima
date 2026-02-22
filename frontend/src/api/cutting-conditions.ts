import { apiClient } from './client'
import type { CuttingConditionPivotResponse } from '@/types/cutting-condition'

export async function getPivot(mode: 'low' | 'mid' | 'high' = 'mid'): Promise<CuttingConditionPivotResponse> {
  const { data } = await apiClient.get<CuttingConditionPivotResponse>('/cutting-conditions/pivot', { params: { mode } })
  return data
}
