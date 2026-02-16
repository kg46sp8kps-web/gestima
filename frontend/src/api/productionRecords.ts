/**
 * Production Records API - All production record endpoints
 */

import { apiClient } from './client'
import type {
  ProductionRecord,
  ProductionRecordCreate,
  ProductionRecordUpdate,
  ProductionSummary
} from '@/types/productionRecord'

/**
 * Get all production records for a part
 */
export async function getProductionRecords(partId: number): Promise<ProductionRecord[]> {
  const response = await apiClient.get<ProductionRecord[]>(`/production-records/part/${partId}`)
  return response.data
}

/**
 * Get production summary statistics for a part
 */
export async function getProductionSummary(partId: number): Promise<ProductionSummary> {
  const response = await apiClient.get<ProductionSummary>(`/production-records/part/${partId}/summary`)
  return response.data
}

/**
 * Create new production record
 */
export async function createProductionRecord(
  data: ProductionRecordCreate
): Promise<ProductionRecord> {
  const response = await apiClient.post<ProductionRecord>('/production-records/', data)
  return response.data
}

/**
 * Update existing production record
 */
export async function updateProductionRecord(
  id: number,
  data: ProductionRecordUpdate
): Promise<ProductionRecord> {
  const response = await apiClient.put<ProductionRecord>(`/production-records/${id}`, data)
  return response.data
}

/**
 * Delete production record
 */
export async function deleteProductionRecord(id: number): Promise<void> {
  await apiClient.delete(`/production-records/${id}`)
}

/**
 * Bulk create production records
 */
export async function bulkCreateProductionRecords(
  records: ProductionRecordCreate[]
): Promise<ProductionRecord[]> {
  const response = await apiClient.post<ProductionRecord[]>('/production-records/bulk', records)
  return response.data
}
