import { apiClient } from './client'
import type { MaterialInput } from '@/types/material-input'

export async function getByPartId(partId: number): Promise<MaterialInput[]> {
  const { data } = await apiClient.get<MaterialInput[]>(`/material-inputs/parts/${partId}`)
  return data
}
