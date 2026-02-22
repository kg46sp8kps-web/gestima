import { apiClient } from './client'
import type { MaterialInput, MaterialInputCreate, MaterialInputUpdate, ParseResult } from '@/types/material-input'

export async function getByPartId(partId: number): Promise<MaterialInput[]> {
  const { data } = await apiClient.get<MaterialInput[]>(`/material-inputs/parts/${partId}`)
  return data
}

export async function create(payload: MaterialInputCreate): Promise<MaterialInput> {
  const { data } = await apiClient.post<MaterialInput>('/material-inputs', payload)
  return data
}

export async function update(materialId: number, payload: MaterialInputUpdate): Promise<MaterialInput> {
  const { data } = await apiClient.put<MaterialInput>(`/material-inputs/${materialId}`, payload)
  return data
}

export async function linkOperation(materialId: number, operationId: number): Promise<void> {
  await apiClient.post(`/material-inputs/${materialId}/link-operation/${operationId}`, {})
}

export async function unlinkOperation(materialId: number, operationId: number): Promise<void> {
  await apiClient.delete(`/material-inputs/${materialId}/unlink-operation/${operationId}`)
}

export async function parse(description: string): Promise<ParseResult> {
  const { data } = await apiClient.post<ParseResult>('/materials/parse', null, {
    params: { description },
  })
  return data
}
