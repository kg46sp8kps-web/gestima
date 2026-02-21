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
  StagedJobMaterialRow,
  StagedDocumentRow,
  StagedMaterialRow,
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
 * Batched preview for Production import.
 * Splits rows into chunks of PREVIEW_BATCH_SIZE, calls backend per chunk,
 * merges results. Calls onProgress after each chunk.
 */
export async function previewProductionImport(
  rows: Record<string, unknown>[],
  onProgress?: (done: number, total: number) => void
) {
  const allRows: StagedProductionRow[] = []
  let totalValid = 0
  let totalErrors = 0
  let totalDuplicates = 0

  for (let i = 0; i < rows.length; i += PREVIEW_BATCH_SIZE) {
    const chunk = rows.slice(i, i + PREVIEW_BATCH_SIZE)
    const data = await postWithRetry<{
      rows: StagedProductionRow[]
      valid_count: number
      error_count: number
      duplicate_count: number
    }>('/infor/import/production/preview', { rows: chunk })

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
 * Batched execute for Production import.
 * Splits rows into chunks, calls backend per chunk, merges results.
 */
export async function executeProductionImport(
  rows: StagedProductionRow[],
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
      '/infor/import/production/execute',
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
 * Batched preview for Job Materials import.
 * Splits rows into chunks, calls backend per chunk, merges results.
 */
export async function previewJobMaterialsImport(
  rows: Record<string, unknown>[],
  onProgress?: (done: number, total: number) => void
) {
  const allRows: StagedJobMaterialRow[] = []
  let totalValid = 0
  let totalErrors = 0
  let totalDuplicates = 0

  for (let i = 0; i < rows.length; i += PREVIEW_BATCH_SIZE) {
    const chunk = rows.slice(i, i + PREVIEW_BATCH_SIZE)
    const data = await postWithRetry<{
      rows: StagedJobMaterialRow[]
      valid_count: number
      error_count: number
      duplicate_count: number
    }>('/infor/import/job-materials/preview', { rows: chunk })

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
 * Batched execute for Job Materials import.
 * Splits rows into chunks, calls backend per chunk, merges results.
 */
export async function executeJobMaterialsImport(
  rows: StagedJobMaterialRow[],
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
      '/infor/import/job-materials/execute',
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

/**
 * List all documents from Infor with automatic pagination.
 * Backend handles bookmark-based pagination internally.
 */
export async function listDocuments(
  filter?: string,
  recordCap: number = 0,
): Promise<{ count: number; rows: Record<string, unknown>[] }> {
  const { data } = await apiClient.post<{ count: number; rows: Record<string, unknown>[] }>(
    '/infor/import/documents/list',
    { filter: filter || null, record_cap: recordCap }
  )
  return data
}

/**
 * Document import batch size — small because each row triggers heavy binary download on backend.
 */
const DOCUMENT_EXECUTE_BATCH_SIZE = 50

/**
 * Batched preview for Document import.
 * Splits rows into chunks of PREVIEW_BATCH_SIZE, calls backend per chunk, merges results.
 * Calls onProgress after each chunk.
 */
export async function previewDocumentImport(
  rows: Record<string, unknown>[],
  onProgress?: (done: number, total: number) => void
) {
  const allRows: StagedDocumentRow[] = []
  let totalValid = 0
  let totalErrors = 0
  let totalDuplicates = 0

  for (let i = 0; i < rows.length; i += PREVIEW_BATCH_SIZE) {
    const chunk = rows.slice(i, i + PREVIEW_BATCH_SIZE)
    const data = await postWithRetry<{
      rows: StagedDocumentRow[]
      valid_count: number
      error_count: number
      duplicate_count: number
    }>('/infor/import/documents/preview', { rows: chunk })

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
 * Batched execute for Document import.
 * Uses small batch size (20) because each row triggers a heavy binary download on backend.
 * Calls onProgress after each chunk.
 */
export async function executeDocumentImport(
  rows: StagedDocumentRow[],
  onProgress?: (done: number, total: number) => void
) {
  let totalCreated = 0
  let totalUpdated = 0
  let totalSkipped = 0
  const allErrors: string[] = []

  for (let i = 0; i < rows.length; i += DOCUMENT_EXECUTE_BATCH_SIZE) {
    const chunk = rows.slice(i, i + DOCUMENT_EXECUTE_BATCH_SIZE)
    const payload = chunk.map(r => ({
      row_pointer: r.row_pointer,
      document_name: r.document_name,
      document_extension: r.document_extension,
      sequence: r.sequence,
      description: r.description,
      matched_part_id: r.matched_part_id,
      matched_article_number: r.matched_article_number,
      matched_part_number: r.matched_part_number,
      is_valid: r.is_valid,
      is_duplicate: r.is_duplicate,
      duplicate_action: r.duplicate_action
    }))
    const data = await postWithRetry<ImportExecuteResponse>(
      '/infor/import/documents/execute',
      { rows: payload }
    )

    totalCreated += data.created_count
    totalUpdated += data.updated_count
    totalSkipped += data.skipped_count
    allErrors.push(...data.errors)

    onProgress?.(Math.min(i + DOCUMENT_EXECUTE_BATCH_SIZE, rows.length), rows.length)
  }

  return {
    success: allErrors.length === 0,
    created_count: totalCreated,
    updated_count: totalUpdated,
    skipped_count: totalSkipped,
    errors: allErrors
  }
}

// ----------------------------------------------------------------------------
// Shared Infor Browser/Discovery/Connection helpers (used across UI tabs)
// ----------------------------------------------------------------------------

export interface InforIdoInfoField {
  name: string
  dataType?: string
  required?: boolean
  readOnly?: boolean
}

export interface InforIdoInfoResponse {
  info: InforIdoInfoField[]
}

export interface InforIdoDataParams {
  properties: string
  limit?: number
  filter?: string
  order_by?: string
}

export interface InforIdoDataResponse {
  data: Record<string, unknown>[]
}

export async function getInforIdoInfo(idoName: string): Promise<InforIdoInfoResponse> {
  const { data } = await apiClient.get<InforIdoInfoResponse>(`/infor/ido/${idoName}/info`)
  return data
}

export async function getInforIdoData(
  idoName: string,
  params: InforIdoDataParams
): Promise<InforIdoDataResponse> {
  const { data } = await apiClient.get<InforIdoDataResponse>(`/infor/ido/${idoName}/data`, { params })
  return data
}

export async function discoverInforIdos(customNames?: string): Promise<{ found: string[]; not_found: string[] }> {
  const params = customNames ? { custom_names: customNames } : {}
  const { data } = await apiClient.get<{ found: string[]; not_found: string[] }>('/infor/discover-idos', { params })
  return data
}

export async function testInforConnection(): Promise<Record<string, unknown>> {
  const { data } = await apiClient.get<Record<string, unknown>>('/infor/test-connection')
  return data
}

export async function previewMaterialImport(
  idoName: string,
  rows: Record<string, unknown>[]
): Promise<{
  valid_count: number
  error_count: number
  duplicate_count: number
  rows: StagedMaterialRow[]
}> {
  const { data } = await apiClient.post<{
    valid_count: number
    error_count: number
    duplicate_count: number
    rows: StagedMaterialRow[]
  }>('/infor/import/materials/preview', { ido_name: idoName, rows })
  return data
}

export async function executeMaterialImport(
  rows: Array<Record<string, unknown>>
): Promise<ImportExecuteResponse> {
  const { data } = await apiClient.post<ImportExecuteResponse>('/infor/import/materials/execute', { rows })
  return data
}

export async function testMaterialImportPattern(
  row: Record<string, unknown>
): Promise<Record<string, unknown>> {
  const { data } = await apiClient.post<Record<string, unknown>>('/infor/import/materials/test-pattern', { row })
  return data
}
