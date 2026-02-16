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
 * Get parts with pagination, optional status filter and search.
 * Returns { parts, total, skip, limit }.
 */
export async function getParts(
  skip = 0,
  limit = 100,
  status?: string,
  search?: string
): Promise<PartsSearchResponse> {
  const params: Record<string, unknown> = { skip, limit }
  if (status) params.status = status
  if (search) params.search = search
  const response = await apiClient.get<PartsSearchResponse>('/parts/', { params })
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
 * Create new part (optionally copy from existing part)
 */
export async function createPart(
  data: PartCreate,
  copyFrom?: {
    sourcePartNumber: string
    copyOperations: boolean
    copyMaterial: boolean
    copyBatches: boolean
  }
): Promise<Part> {
  const params = copyFrom ? {
    copy_from: copyFrom.sourcePartNumber,
    copy_operations: copyFrom.copyOperations,
    copy_material: copyFrom.copyMaterial,
    copy_batches: copyFrom.copyBatches
  } : {}

  const response = await apiClient.post<Part>('/parts/', data, { params })
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
