/**
 * Drawings API - PDF drawing management
 *
 * Endpoints (Phase B - Multiple Drawings):
 * - POST /api/uploads/temp - Upload temp file (returns temp_id)
 * - GET /api/parts/{pn}/drawings - List all drawings for part
 * - POST /api/parts/{pn}/drawings - Upload new drawing
 * - PUT /api/parts/{pn}/drawings/{id}/primary - Set drawing as primary
 * - DELETE /api/parts/{pn}/drawings/{id} - Delete specific drawing
 * - GET /api/parts/{pn}/drawings/{id} - Get specific drawing URL
 *
 * Legacy endpoints (Phase A - Single Drawing):
 * - POST /api/parts/{pn}/drawing - Upload drawing (deprecated)
 * - GET /api/parts/{pn}/drawing - Get primary drawing URL (deprecated)
 * - DELETE /api/parts/{pn}/drawing - Delete drawing (deprecated)
 */

import { apiClient } from './client'
import type { Drawing, DrawingListResponse, DrawingResponse } from '@/types/drawing'

export interface TempUploadResponse {
  temp_id: string
  filename: string
  size: number
}

export interface DrawingUploadResponse {
  message: string
  drawing_path: string
  version: number
}

/**
 * Upload file to temporary storage
 * Used in create form before part is created
 */
export async function uploadTemp(file: File): Promise<TempUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await apiClient.post<TempUploadResponse>(
    '/uploads/temp',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }
  )

  return response.data
}

/**
 * Upload drawing directly to part (LEGACY - Phase A)
 * @deprecated Use uploadDrawing instead
 */
export async function uploadToPart(
  partNumber: string,
  file: File
): Promise<DrawingUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await apiClient.post<DrawingUploadResponse>(
    `/parts/${partNumber}/drawing`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }
  )

  return response.data
}

// ============================================================================
// PHASE B - MULTIPLE DRAWINGS API
// ============================================================================

/**
 * List all drawings for a part
 */
export async function listDrawings(partNumber: string): Promise<DrawingListResponse> {
  const response = await apiClient.get<DrawingListResponse>(`/parts/${partNumber}/drawings`)
  return response.data
}

/**
 * Upload new drawing to part
 */
export async function uploadDrawing(
  partNumber: string,
  file: File,
  revision?: string
): Promise<DrawingResponse> {
  const formData = new FormData()
  formData.append('file', file)
  if (revision) {
    formData.append('revision', revision)
  }

  const response = await apiClient.post<DrawingResponse>(
    `/parts/${partNumber}/drawings`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }
  )

  return response.data
}

/**
 * Set drawing as primary
 */
export async function setPrimaryDrawing(
  partNumber: string,
  drawingId: number
): Promise<DrawingResponse> {
  const response = await apiClient.put<DrawingResponse>(
    `/parts/${partNumber}/drawings/${drawingId}/primary`
  )
  return response.data
}

/**
 * Delete specific drawing
 */
export async function deleteDrawingById(
  partNumber: string,
  drawingId: number
): Promise<void> {
  await apiClient.delete(`/parts/${partNumber}/drawings/${drawingId}`)
}

/**
 * Get drawing URL for specific drawing or primary
 * @param partNumber Part number
 * @param drawingId Optional drawing ID. If not provided, returns primary drawing URL
 */
export function getDrawingUrl(partNumber: string, drawingId?: number): string {
  if (drawingId !== undefined) {
    return `/api/parts/${partNumber}/drawings/${drawingId}`
  }
  // Legacy: primary drawing URL
  return `/api/parts/${partNumber}/drawing`
}

/**
 * Delete drawing from part (LEGACY - Phase A)
 * @deprecated Use deleteDrawingById instead
 */
export async function deleteDrawing(partNumber: string): Promise<void> {
  await apiClient.delete(`/parts/${partNumber}/drawing`)
}

export const drawingsApi = {
  // Temp upload (used in create form)
  uploadTemp,

  // Legacy API (Phase A)
  uploadToPart,
  deleteDrawing,

  // New API (Phase B)
  listDrawings,
  uploadDrawing,
  setPrimaryDrawing,
  deleteDrawingById,
  getDrawingUrl
}
