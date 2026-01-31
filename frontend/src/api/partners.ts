/**
 * Partners API - All partner-related endpoints
 */

import { apiClient } from './client'
import type {
  Partner,
  PartnerCreate,
  PartnerUpdate,
  PartnersSearchResponse
} from '@/types/partner'

/**
 * Get all partners with pagination and optional type filter
 */
export async function getPartners(
  skip = 0,
  limit = 100,
  partnerType?: 'customer' | 'supplier'
): Promise<Partner[]> {
  const params: any = { skip, limit }
  if (partnerType) {
    params.partner_type = partnerType
  }
  const response = await apiClient.get<Partner[]>('/partners/', { params })
  return response.data
}

/**
 * Search partners by query (searches company_name, ico, email)
 */
export async function searchPartners(
  search: string,
  skip = 0,
  limit = 50
): Promise<PartnersSearchResponse> {
  const response = await apiClient.get<PartnersSearchResponse>('/partners/search', {
    params: { search, skip, limit }
  })
  return response.data
}

/**
 * Get single partner by partner_number
 */
export async function getPartner(partnerNumber: string): Promise<Partner> {
  const response = await apiClient.get<Partner>(`/partners/${partnerNumber}`)
  return response.data
}

/**
 * Create new partner
 */
export async function createPartner(data: PartnerCreate): Promise<Partner> {
  const response = await apiClient.post<Partner>('/partners/', data)
  return response.data
}

/**
 * Update existing partner
 */
export async function updatePartner(
  partnerNumber: string,
  data: PartnerUpdate
): Promise<Partner> {
  const response = await apiClient.put<Partner>(`/partners/${partnerNumber}`, data)
  return response.data
}

/**
 * Delete partner (hard delete)
 */
export async function deletePartner(partnerNumber: string): Promise<void> {
  await apiClient.delete(`/partners/${partnerNumber}`)
}
