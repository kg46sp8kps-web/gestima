/**
 * Drawings API - PDF/STEP drawing management
 *
 * Endpoints:
 * - GET /api/parts/{pn}/drawings - List all drawings for part
 * - POST /api/parts/{pn}/drawings - Upload new drawing
 * - PUT /api/parts/{pn}/drawings/{id}/primary - Set drawing as primary
 * - DELETE /api/parts/{pn}/drawings/{id} - Delete specific drawing
 * - GET /api/parts/{pn}/drawings/{id} - Get specific drawing URL
 */

import { apiClient } from './client'
import type { Drawing, DrawingListResponse, DrawingResponse } from '@/types/drawing'

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
 * @param drawingId Optional drawing ID. If not provided, returns primary (legacy)
 */
export function getDrawingUrl(partNumber: string, drawingId?: number): string {
  if (drawingId !== undefined) {
    return `/api/parts/${partNumber}/drawings/${drawingId}`
  }
  // Legacy: primary drawing URL via drawings_router
  return `/api/parts/${partNumber}/drawing`
}

export const drawingsApi = {
  listDrawings,
  uploadDrawing,
  setPrimaryDrawing,
  deleteDrawingById,
  getDrawingUrl
}
