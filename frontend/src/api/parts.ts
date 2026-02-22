import { apiClient } from './client'
import type { Part, PartCreate, PartUpdate, PartListResponse, PartListParams } from '@/types/part'

export async function getAll(params?: PartListParams): Promise<PartListResponse> {
  const clean: Record<string, string | number | boolean> = {}
  if (params?.skip != null) clean.skip = params.skip
  if (params?.limit != null) clean.limit = params.limit
  if (params?.search) clean.search = params.search
  if (params?.status) clean.status = params.status
  if (params?.source) clean.source = params.source
  if (params?.has_drawing != null) clean.has_drawing = params.has_drawing
  const { data } = await apiClient.get<PartListResponse>('/parts/', { params: clean })
  return data
}

export async function getByNumber(partNumber: string): Promise<Part> {
  const { data } = await apiClient.get<Part>(`/parts/${partNumber}`)
  return data
}

export async function create(payload: PartCreate): Promise<Part> {
  const { data } = await apiClient.post<Part>('/parts/', payload)
  return data
}

export async function update(partNumber: string, payload: PartUpdate): Promise<Part> {
  const { data } = await apiClient.put<Part>(`/parts/${partNumber}`, payload)
  return data
}

export async function remove(partNumber: string): Promise<void> {
  await apiClient.delete(`/parts/${partNumber}`)
}

export async function duplicate(partNumber: string): Promise<Part> {
  const { data } = await apiClient.post<Part>(`/parts/${partNumber}/duplicate`)
  return data
}
