/**
 * Parts API - All part-related endpoints
 */

import { apiClient } from './client'
import type {
  Part,
  PartCreate,
  PartUpdate,
  PartsSearchResponse,
  StockCostResponse,
  PriceBreakdown
} from '@/types/part'

/**
 * Get all parts with pagination
 */
export async function getParts(skip = 0, limit = 100): Promise<Part[]> {
  const response = await apiClient.get<Part[]>('/parts/', {
    params: { skip, limit }
  })
  return response.data
}

/**
 * Search parts by query (searches part_number, name, article_number)
 */
export async function searchParts(
  search: string,
  skip = 0,
  limit = 50
): Promise<PartsSearchResponse> {
  const response = await apiClient.get<PartsSearchResponse>('/parts/search', {
    params: { search, skip, limit }
  })
  return response.data
}

/**
 * Get single part by part_number
 */
export async function getPart(partNumber: string): Promise<Part> {
  const response = await apiClient.get<Part>(`/parts/${partNumber}`)
  return response.data
}

/**
 * Get part with full eager-loaded relationships
 */
export async function getPartFull(partNumber: string): Promise<any> {
  const response = await apiClient.get(`/parts/${partNumber}/full`)
  return response.data
}

/**
 * Create new part
 */
export async function createPart(data: PartCreate): Promise<Part> {
  const response = await apiClient.post<Part>('/parts/', data)
  return response.data
}

/**
 * Update existing part
 */
export async function updatePart(
  partNumber: string,
  data: PartUpdate
): Promise<Part> {
  const response = await apiClient.put<Part>(`/parts/${partNumber}`, data)
  return response.data
}

/**
 * Duplicate part (creates new part with auto-generated part_number)
 */
export async function duplicatePart(partNumber: string): Promise<Part> {
  const response = await apiClient.post<Part>(`/parts/${partNumber}/duplicate`)
  return response.data
}

/**
 * Delete part (hard delete)
 */
export async function deletePart(partNumber: string): Promise<void> {
  await apiClient.delete(`/parts/${partNumber}`)
}

/**
 * Get stock cost calculation
 */
export async function getStockCost(
  partNumber: string
): Promise<StockCostResponse> {
  const response = await apiClient.get<StockCostResponse>(
    `/parts/${partNumber}/stock-cost`
  )
  return response.data
}

/**
 * Copy material geometry from MaterialItem to Part.stock_*
 */
export async function copyMaterialGeometry(
  partNumber: string
): Promise<{ message: string; version: number }> {
  const response = await apiClient.post<{ message: string; version: number }>(
    `/parts/${partNumber}/copy-material-geometry`
  )
  return response.data
}

/**
 * Get part pricing breakdown
 */
export async function getPartPricing(
  partNumber: string,
  quantity = 1
): Promise<PriceBreakdown> {
  const response = await apiClient.get<PriceBreakdown>(
    `/parts/${partNumber}/pricing`,
    { params: { quantity } }
  )
  return response.data
}

/**
 * Get series pricing (multiple quantities)
 */
export async function getSeriesPricing(
  partNumber: string,
  quantities: number[]
): Promise<PriceBreakdown[]> {
  const response = await apiClient.get<PriceBreakdown[]>(
    `/parts/${partNumber}/pricing/series`,
    { params: { quantities: quantities.join(',') } }
  )
  return response.data
}
