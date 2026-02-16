/**
 * Infor Jobs Import API Client
 *
 * API endpoints for importing Parts, Operations, and ProductionRecords from Infor SLJobs/SLJobRoutes
 */

import { apiClient } from './client'
import type {
  StagedPartRow,
  StagedRoutingRow,
  StagedProductionRow,
  WcMapping,
  ImportExecuteResponse
} from '@/types/infor'

/**
 * Preview Parts import (validation only, no DB changes)
 * @param rows - Raw Infor SLJobs rows
 * @returns Staged rows with validation results
 */
export async function previewPartsImport(rows: Record<string, unknown>[]) {
  const { data } = await apiClient.post<{
    rows: StagedPartRow[]
    valid_count: number
    error_count: number
    duplicate_count: number
  }>('/infor/import/parts/preview', { rows })
  return data
}

/**
 * Execute Parts import (create/update Part records)
 * @param rows - Validated staged rows
 * @returns Import result counts
 */
export async function executePartsImport(rows: StagedPartRow[]) {
  const payload = rows.map(r => ({
    ...r.mapped_data,
    duplicate_action: r.duplicate_action ?? 'skip'
  }))
  const { data } = await apiClient.post<ImportExecuteResponse>('/infor/import/parts/execute', { rows: payload })
  return data
}

/**
 * Batched preview for Routing import.
 * Splits rows into chunks of BATCH_SIZE, calls backend per chunk,
 * merges results. Calls onProgress after each chunk.
 */
const PREVIEW_BATCH_SIZE = 5000
const EXECUTE_BATCH_SIZE = 2000

/** POST with retry on 429 (rate limit) */
async function postWithRetry<T>(url: string, body: unknown, maxRetries = 3): Promise<T> {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const { data } = await apiClient.post<T>(url, body)
      return data
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number } }
      if (axiosErr.response?.status === 429 && attempt < maxRetries) {
        // Wait 5s before retry on rate limit
        await new Promise(r => setTimeout(r, 5000))
        continue
      }
      throw err
    }
  }
  throw new Error('Max retries exceeded')
}

export async function previewRoutingImport(
  rows: Record<string, unknown>[],
  onProgress?: (done: number, total: number) => void
) {
  const allRows: StagedRoutingRow[] = []
  let totalValid = 0
  let totalErrors = 0
  let totalDuplicates = 0

  for (let i = 0; i < rows.length; i += PREVIEW_BATCH_SIZE) {
    const chunk = rows.slice(i, i + PREVIEW_BATCH_SIZE)
    const data = await postWithRetry<{
      rows: StagedRoutingRow[]
      valid_count: number
      error_count: number
      duplicate_count: number
    }>('/infor/import/routing/preview', { rows: chunk })

    for (const row of data.rows) {
      row.row_index = allRows.length
      allRows.push(row)
    }
    totalValid += data.valid_count
    totalErrors += data.error_count
    totalDuplicates += data.duplicate_count

    onProgress?.(Math.min(i + PREVIEW_BATCH_SIZE, rows.length), rows.length)
  }

  return {
    rows: allRows,
    valid_count: totalValid,
    error_count: totalErrors,
    duplicate_count: totalDuplicates
  }
}

/**
 * Batched execute for Routing import.
 * Splits rows into chunks, calls backend per chunk, merges results.
 */
export async function executeRoutingImport(
  rows: StagedRoutingRow[],
  onProgress?: (done: number, total: number) => void
) {
  let totalCreated = 0
  let totalUpdated = 0
  let totalSkipped = 0
  const allErrors: string[] = []

  for (let i = 0; i < rows.length; i += EXECUTE_BATCH_SIZE) {
    const chunk = rows.slice(i, i + EXECUTE_BATCH_SIZE)
    const payload = chunk.map(r => ({
      ...r.mapped_data,
      duplicate_action: r.validation.is_duplicate ? 'update' : 'skip'
    }))
    const data = await postWithRetry<ImportExecuteResponse>(
      '/infor/import/routing/execute',
      { rows: payload }
    )

    totalCreated += data.created_count
    totalUpdated += data.updated_count
    totalSkipped += data.skipped_count
    allErrors.push(...data.errors)

    onProgress?.(Math.min(i + EXECUTE_BATCH_SIZE, rows.length), rows.length)
  }

  return {
    success: allErrors.length === 0,
    created_count: totalCreated,
    updated_count: totalUpdated,
    skipped_count: totalSkipped,
    errors: allErrors
  }
}

/**
 * Preview Production import (validation only, no DB changes)
 * @param rows - Raw Infor SLJobRoutes rows
 * @returns Staged rows with validation results
 */
export async function previewProductionImport(rows: Record<string, unknown>[]) {
  const { data } = await apiClient.post<{
    rows: StagedProductionRow[]
    valid_count: number
    error_count: number
  }>('/infor/import/production/preview', { rows })
  return data
}

/**
 * Execute Production import (create ProductionRecord records)
 * @param rows - Validated staged rows
 * @returns Import result counts
 */
export async function executeProductionImport(rows: StagedProductionRow[]) {
  const payload = rows.map(r => r.mapped_data)
  const { data } = await apiClient.post<ImportExecuteResponse>('/infor/import/production/execute', { rows: payload })
  return data
}

/**
 * Get Work Center mapping (Infor WC code → Gestima WC number)
 * @returns WC mapping dictionary
 */
export async function getWcMapping() {
  const { data } = await apiClient.get<WcMapping>('/infor/import/wc-mapping')
  return data
}

/**
 * Update Work Center mapping
 * @param mapping - New WC mapping dictionary
 */
export async function updateWcMapping(mapping: WcMapping) {
  await apiClient.put('/infor/import/wc-mapping', mapping)
}
