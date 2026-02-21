/**
 * Drawing Import API
 */

import { apiClient } from './client'
import type {
  ShareStatusResponse,
  DrawingImportPreviewResponse,
  DrawingImportExecuteRequest,
  DrawingImportExecuteResponse,
} from '@/types/drawing-import'

const BASE = '/drawings/import'

export async function getDrawingShareStatus(): Promise<ShareStatusResponse> {
  const response = await apiClient.get<ShareStatusResponse>(`${BASE}/status`)
  return response.data
}

export async function previewDrawingImport(): Promise<DrawingImportPreviewResponse> {
  const response = await apiClient.post<DrawingImportPreviewResponse>(`${BASE}/preview`)
  return response.data
}

export async function executeDrawingImport(
  request: DrawingImportExecuteRequest
): Promise<DrawingImportExecuteResponse> {
  const response = await apiClient.post<DrawingImportExecuteResponse>(
    `${BASE}/execute`,
    request,
    { timeout: 600000 } // 10 min timeout for large imports
  )
  return response.data
}
