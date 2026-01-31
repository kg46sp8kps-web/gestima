/**
 * Drawings API - PDF drawing management
 *
 * Endpoints:
 * - POST /api/uploads/temp - Upload temp file (returns temp_id)
 * - POST /api/parts/{pn}/drawing - Upload drawing to part
 * - GET /api/parts/{pn}/drawing - Get drawing URL
 * - DELETE /api/parts/{pn}/drawing - Delete drawing
 */

import { apiClient } from './client'

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
 * Upload drawing directly to part
 * Used in part detail when part already exists
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

/**
 * Get drawing URL for part
 * Returns full URL to PDF (e.g., /api/parts/{pn}/drawing)
 */
export function getDrawingUrl(partNumber: string): string {
  // Backend serves PDF at this endpoint
  return `/api/parts/${partNumber}/drawing`
}

/**
 * Delete drawing from part
 */
export async function deleteDrawing(partNumber: string): Promise<void> {
  await apiClient.delete(`/parts/${partNumber}/drawing`)
}

export const drawingsApi = {
  uploadTemp,
  uploadToPart,
  getDrawingUrl,
  deleteDrawing
}
