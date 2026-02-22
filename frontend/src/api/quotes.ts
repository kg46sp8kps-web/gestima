import { apiClient } from './client'
import type { QuoteListItem } from '@/types/quote'

export async function getAll(status?: string): Promise<QuoteListItem[]> {
  const { data } = await apiClient.get<QuoteListItem[]>('/quotes', {
    params: status ? { status } : undefined,
  })
  return data
}
