/**
 * Infor Jobs Import API Client
 *
 * API endpoints for importing Parts, Operations, ProductionRecords, Materials, and Documents
 * from Infor SLJobs/SLJobRoutes/SLItems/SLDocumentObjects_Exts.
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
  ImportExecuteResponse,
} from '@/types/infor'

const PREVIEW_BATCH_SIZE = 5000
const EXECUTE_BATCH_SIZE = 2000
const DOCUMENT_EXECUTE_BATCH_SIZE = 50

async function postWithRetry<T>(url: string, body: unknown, maxRetries = 3): Promise<T> {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const { data } = await apiClient.post<T>(url, body)
      return data
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number } }
      if (axiosErr.response?.status === 429 && attempt < maxRetries) {
        await new Promise((r) => setTimeout(r, 5000))
        continue
      }
      throw err
    }
  }
  throw new Error('Max retries exceeded')
}

// ---------------------------------------------------------------------------
// Parts import
// ---------------------------------------------------------------------------

export async function previewPartsImport(rows: Record<string, unknown>[]) {
  const { data } = await apiClient.post<{
    rows: StagedPartRow[]
    valid_count: number
    error_count: number
    duplicate_count: number
  }>('/infor/import/parts/preview', { rows })
  return data
}

export async function executePartsImport(rows: StagedPartRow[]) {
  const payload = rows.map((r) => ({
    ...r.mapped_data,
    duplicate_action: r.duplicate_action ?? 'skip',
  }))
  const { data } = await apiClient.post<ImportExecuteResponse>('/infor/import/parts/execute', {
    rows: payload,
  })
  return data
}

// ---------------------------------------------------------------------------
// Routing import (batched)
// ---------------------------------------------------------------------------

export async function previewRoutingImport(
  rows: Record<string, unknown>[],
  onProgress?: (done: number, total: number) => void,
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

  return { rows: allRows, valid_count: totalValid, error_count: totalErrors, duplicate_count: totalDuplicates }
}

export async function executeRoutingImport(
  rows: StagedRoutingRow[],
  onProgress?: (done: number, total: number) => void,
) {
  let totalCreated = 0
  let totalUpdated = 0
  let totalSkipped = 0
  const allErrors: string[] = []

  for (let i = 0; i < rows.length; i += EXECUTE_BATCH_SIZE) {
    const chunk = rows.slice(i, i + EXECUTE_BATCH_SIZE)
    const payload = chunk.map((r) => ({
      ...r.mapped_data,
      duplicate_action: r.validation.is_duplicate ? 'update' : 'skip',
    }))
    const data = await postWithRetry<ImportExecuteResponse>('/infor/import/routing/execute', {
      rows: payload,
    })
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
    errors: allErrors,
  }
}

// ---------------------------------------------------------------------------
// Production import (batched)
// ---------------------------------------------------------------------------

export async function previewProductionImport(
  rows: Record<string, unknown>[],
  onProgress?: (done: number, total: number) => void,
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

  return { rows: allRows, valid_count: totalValid, error_count: totalErrors, duplicate_count: totalDuplicates }
}

export async function executeProductionImport(
  rows: StagedProductionRow[],
  onProgress?: (done: number, total: number) => void,
) {
  let totalCreated = 0
  let totalUpdated = 0
  let totalSkipped = 0
  const allErrors: string[] = []

  for (let i = 0; i < rows.length; i += EXECUTE_BATCH_SIZE) {
    const chunk = rows.slice(i, i + EXECUTE_BATCH_SIZE)
    const payload = chunk.map((r) => ({
      ...r.mapped_data,
      duplicate_action: r.validation.is_duplicate ? 'update' : 'skip',
    }))
    const data = await postWithRetry<ImportExecuteResponse>('/infor/import/production/execute', {
      rows: payload,
    })
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
    errors: allErrors,
  }
}

// ---------------------------------------------------------------------------
// Job Materials import (batched)
// ---------------------------------------------------------------------------

export async function previewJobMaterialsImport(
  rows: Record<string, unknown>[],
  onProgress?: (done: number, total: number) => void,
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

  return { rows: allRows, valid_count: totalValid, error_count: totalErrors, duplicate_count: totalDuplicates }
}

export async function executeJobMaterialsImport(
  rows: StagedJobMaterialRow[],
  onProgress?: (done: number, total: number) => void,
) {
  let totalCreated = 0
  let totalUpdated = 0
  let totalSkipped = 0
  const allErrors: string[] = []

  for (let i = 0; i < rows.length; i += EXECUTE_BATCH_SIZE) {
    const chunk = rows.slice(i, i + EXECUTE_BATCH_SIZE)
    const payload = chunk.map((r) => ({
      ...r.mapped_data,
      duplicate_action: r.validation.is_duplicate ? 'update' : 'skip',
    }))
    const data = await postWithRetry<ImportExecuteResponse>('/infor/import/job-materials/execute', {
      rows: payload,
    })
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
    errors: allErrors,
  }
}

// ---------------------------------------------------------------------------
// WC Mapping
// ---------------------------------------------------------------------------

export async function getWcMapping(): Promise<WcMapping> {
  const { data } = await apiClient.get<WcMapping>('/infor/import/wc-mapping')
  return data
}

export async function updateWcMapping(mapping: WcMapping): Promise<void> {
  await apiClient.put('/infor/import/wc-mapping', mapping)
}

// ---------------------------------------------------------------------------
// Document import
// ---------------------------------------------------------------------------

export async function listDocuments(
  filter?: string,
  recordCap: number = 0,
): Promise<{ count: number; rows: Record<string, unknown>[] }> {
  const { data } = await apiClient.post<{ count: number; rows: Record<string, unknown>[] }>(
    '/infor/import/documents/list',
    { filter: filter || null, record_cap: recordCap },
  )
  return data
}

export async function previewDocumentImport(
  rows: Record<string, unknown>[],
  onProgress?: (done: number, total: number) => void,
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

  return { rows: allRows, valid_count: totalValid, error_count: totalErrors, duplicate_count: totalDuplicates }
}

export async function executeDocumentImport(
  rows: StagedDocumentRow[],
  onProgress?: (done: number, total: number) => void,
) {
  let totalCreated = 0
  let totalUpdated = 0
  let totalSkipped = 0
  const allErrors: string[] = []

  for (let i = 0; i < rows.length; i += DOCUMENT_EXECUTE_BATCH_SIZE) {
    const chunk = rows.slice(i, i + DOCUMENT_EXECUTE_BATCH_SIZE)
    const payload = chunk.map((r) => ({
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
      duplicate_action: r.duplicate_action,
    }))
    const data = await postWithRetry<ImportExecuteResponse>(
      '/infor/import/documents/execute',
      { rows: payload },
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
    errors: allErrors,
  }
}

// ---------------------------------------------------------------------------
// Material import
// ---------------------------------------------------------------------------

export async function previewMaterialImport(
  idoName: string,
  rows: Record<string, unknown>[],
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
  rows: Array<Record<string, unknown>>,
): Promise<ImportExecuteResponse> {
  const { data } = await apiClient.post<ImportExecuteResponse>('/infor/import/materials/execute', {
    rows,
  })
  return data
}

export async function testMaterialImportPattern(
  row: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const { data } = await apiClient.post<Record<string, unknown>>(
    '/infor/import/materials/test-pattern',
    { row },
  )
  return data
}
