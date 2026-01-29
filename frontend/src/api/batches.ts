/**
 * Batches API - All batch and batch set related endpoints
 */

import { apiClient } from './client'
import type {
  Batch,
  BatchCreate,
  BatchSet,
  BatchSetWithBatches,
  BatchSetListItem,
  BatchSetCreate,
  BatchSetUpdate
} from '@/types/batch'

// =============================================================================
// Batches
// =============================================================================

/**
 * Get all batches for a part
 */
export async function getBatchesForPart(partId: number): Promise<Batch[]> {
  const response = await apiClient.get<Batch[]>(`/batches/part/${partId}`)
  return response.data
}

/**
 * Get single batch by batch_number
 */
export async function getBatch(batchNumber: string): Promise<Batch> {
  const response = await apiClient.get<Batch>(`/batches/${batchNumber}`)
  return response.data
}

/**
 * Create new batch
 */
export async function createBatch(data: BatchCreate): Promise<Batch> {
  const response = await apiClient.post<Batch>('/batches/', data)
  return response.data
}

/**
 * Delete batch
 */
export async function deleteBatch(batchNumber: string): Promise<void> {
  await apiClient.delete(`/batches/${batchNumber}`)
}

/**
 * Freeze batch
 */
export async function freezeBatch(batchNumber: string): Promise<Batch> {
  const response = await apiClient.post<Batch>(`/batches/${batchNumber}/freeze`)
  return response.data
}

/**
 * Clone batch
 */
export async function cloneBatch(batchNumber: string): Promise<Batch> {
  const response = await apiClient.post<Batch>(`/batches/${batchNumber}/clone`)
  return response.data
}

/**
 * Recalculate single batch
 */
export async function recalculateBatch(batchNumber: string): Promise<Batch> {
  const response = await apiClient.post<Batch>(`/batches/${batchNumber}/recalculate`)
  return response.data
}

/**
 * Recalculate all batches for a part
 */
export async function recalculateBatchesForPart(partId: number): Promise<void> {
  await apiClient.post(`/batches/part/${partId}/recalculate`)
}

// =============================================================================
// Batch Sets
// =============================================================================

/**
 * Get all batch sets (global list)
 */
export async function getBatchSets(): Promise<BatchSetListItem[]> {
  const response = await apiClient.get<BatchSetListItem[]>('/pricing/batch-sets')
  return response.data
}

/**
 * Get batch sets for a part
 */
export async function getBatchSetsForPart(partId: number): Promise<BatchSetListItem[]> {
  const response = await apiClient.get<BatchSetListItem[]>(`/pricing/part/${partId}/batch-sets`)
  return response.data
}

/**
 * Get batch set with batches
 */
export async function getBatchSet(setId: number): Promise<BatchSetWithBatches> {
  const response = await apiClient.get<BatchSetWithBatches>(`/pricing/batch-sets/${setId}`)
  return response.data
}

/**
 * Create new batch set
 */
export async function createBatchSet(data: BatchSetCreate): Promise<BatchSet> {
  const response = await apiClient.post<BatchSet>('/pricing/batch-sets', data)
  return response.data
}

/**
 * Update batch set
 */
export async function updateBatchSet(setId: number, data: BatchSetUpdate): Promise<BatchSet> {
  const response = await apiClient.put<BatchSet>(`/pricing/batch-sets/${setId}`, data)
  return response.data
}

/**
 * Delete batch set
 */
export async function deleteBatchSet(setId: number): Promise<void> {
  await apiClient.delete(`/pricing/batch-sets/${setId}`)
}

/**
 * Freeze batch set (freezes all batches in the set)
 */
export async function freezeBatchSet(setId: number): Promise<BatchSetWithBatches> {
  const response = await apiClient.post<BatchSetWithBatches>(`/pricing/batch-sets/${setId}/freeze`)
  return response.data
}

/**
 * Recalculate all batches in a set
 */
export async function recalculateBatchSet(setId: number): Promise<BatchSetWithBatches> {
  const response = await apiClient.post<BatchSetWithBatches>(`/pricing/batch-sets/${setId}/recalculate`)
  return response.data
}

/**
 * Clone batch set
 */
export async function cloneBatchSet(setId: number): Promise<BatchSet> {
  const response = await apiClient.post<BatchSet>(`/pricing/batch-sets/${setId}/clone`)
  return response.data
}

/**
 * Add batch to set
 */
export async function addBatchToSet(setId: number, batchData: BatchCreate): Promise<Batch> {
  const response = await apiClient.post<Batch>(`/pricing/batch-sets/${setId}/batches`, batchData)
  return response.data
}

/**
 * Remove batch from set
 */
export async function removeBatchFromSet(setId: number, batchId: number): Promise<void> {
  await apiClient.delete(`/pricing/batch-sets/${setId}/batches/${batchId}`)
}

/**
 * Freeze loose batches as a new set
 */
export async function freezeLooseBatchesAsSet(partId: number): Promise<BatchSetWithBatches> {
  const response = await apiClient.post<BatchSetWithBatches>(`/pricing/parts/${partId}/freeze-batches-as-set`)
  return response.data
}
