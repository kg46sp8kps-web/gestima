import { apiClient } from './client'
import type { Partner, PartnerSearchResponse } from '@/types/partner'

export async function getAll(partnerType?: 'customer' | 'supplier'): Promise<Partner[]> {
  const { data } = await apiClient.get<Partner[]>('/partners', {
    params: partnerType ? { partner_type: partnerType } : undefined,
  })
  return data
}

export async function search(
  query: string,
  partnerType?: 'customer' | 'supplier',
): Promise<PartnerSearchResponse> {
  const { data } = await apiClient.get<PartnerSearchResponse>('/partners/search', {
    params: { search: query, ...(partnerType ? { partner_type: partnerType } : {}) },
  })
  return data
}
