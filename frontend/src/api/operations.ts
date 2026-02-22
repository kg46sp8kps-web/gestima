import { apiClient } from './client'
import type { Operation, OperationCreate, OperationUpdate } from '@/types/operation'

export async function getByPartId(partId: number): Promise<Operation[]> {
  const { data } = await apiClient.get<Operation[]>(`/operations/part/${partId}`)
  return data
}

export async function getById(operationId: number): Promise<Operation> {
  const { data } = await apiClient.get<Operation>(`/operations/${operationId}`)
  return data
}

export async function create(payload: OperationCreate): Promise<Operation> {
  const { data } = await apiClient.post<Operation>('/operations/', payload)
  return data
}

export async function update(operationId: number, payload: OperationUpdate): Promise<Operation> {
  const { data } = await apiClient.put<Operation>(`/operations/${operationId}`, payload)
  return data
}

export async function remove(operationId: number): Promise<void> {
  await apiClient.delete(`/operations/${operationId}`)
}
