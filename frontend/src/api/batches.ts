import { apiClient } from './client'
import type { Batch, BatchCreate, BatchUpdate } from '@/types/batch'

export async function getByPartId(partId: number): Promise<Batch[]> {
  const { data } = await apiClient.get<Batch[]>(`/batches/part/${partId}`)
  return data
}

export async function getByNumber(batchNumber: string): Promise<Batch> {
  const { data } = await apiClient.get<Batch>(`/batches/${batchNumber}`)
  return data
}

export async function create(payload: BatchCreate): Promise<Batch> {
  const { data } = await apiClient.post<Batch>('/batches/', payload)
  return data
}

export async function update(batchNumber: string, payload: BatchUpdate): Promise<Batch> {
  const { data } = await apiClient.put<Batch>(`/batches/${batchNumber}`, payload)
  return data
}

export async function remove(batchNumber: string): Promise<void> {
  await apiClient.delete(`/batches/${batchNumber}`)
}

export async function recalculate(batchNumber: string): Promise<Batch> {
  const { data } = await apiClient.post<Batch>(`/batches/${batchNumber}/recalculate`)
  return data
}

export async function freeze(batchNumber: string): Promise<Batch> {
  const { data } = await apiClient.post<Batch>(`/batches/${batchNumber}/freeze`)
  return data
}

export async function recalculateByPartId(partId: number): Promise<void> {
  await apiClient.post(`/batches/part/${partId}/recalculate`)
}
