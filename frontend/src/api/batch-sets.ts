import { apiClient } from './client'
import type { BatchSet } from '@/types/batch-set'

export async function getAll(status?: 'draft' | 'frozen'): Promise<BatchSet[]> {
  const { data } = await apiClient.get<BatchSet[]>('/pricing/batch-sets', {
    params: status ? { status } : undefined,
  })
  return data
}
