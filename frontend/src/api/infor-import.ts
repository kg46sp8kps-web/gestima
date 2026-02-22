import { apiClient } from './client'
import type { ImportPreviewResponse, ImportExecuteResponse } from '@/types/infor-sync'

type ImportType = 'parts' | 'routing' | 'production'

export async function preview(type: ImportType, file: File): Promise<ImportPreviewResponse> {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await apiClient.post<ImportPreviewResponse>(`/infor/import/${type}/preview`, fd)
  return data
}

export async function execute(type: ImportType, file: File): Promise<ImportExecuteResponse> {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await apiClient.post<ImportExecuteResponse>(`/infor/import/${type}/execute`, fd)
  return data
}
