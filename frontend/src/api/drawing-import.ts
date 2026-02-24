/**
 * Drawing Import API Client
 *
 * 2-step workflow: scan share → preview → execute import.
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
  const { data } = await apiClient.get<ShareStatusResponse>(`${BASE}/status`)
  return data
}

export async function previewDrawingImport(): Promise<DrawingImportPreviewResponse> {
  const { data } = await apiClient.post<DrawingImportPreviewResponse>(`${BASE}/preview`)
  return data
}

export async function executeDrawingImport(
  request: DrawingImportExecuteRequest,
): Promise<DrawingImportExecuteResponse> {
  const { data } = await apiClient.post<DrawingImportExecuteResponse>(`${BASE}/execute`, request, {
    timeout: 600000,
  })
  return data
}
