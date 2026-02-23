import { apiClient } from './client'
import type { BatchSet, BatchSetWithBatches, BatchSetUpdate } from '@/types/batch-set'
import type { Batch } from '@/types/batch'

export async function getAll(status?: 'draft' | 'frozen'): Promise<BatchSet[]> {
  const { data } = await apiClient.get<BatchSet[]>('/pricing/batch-sets', {
    params: status ? { status } : undefined,
  })
  return data
}

export async function getByPartId(partId: number): Promise<BatchSet[]> {
  const { data } = await apiClient.get<BatchSet[]>(`/pricing/part/${partId}/batch-sets`)
  return data
}

export async function getById(setId: number): Promise<BatchSetWithBatches> {
  const { data } = await apiClient.get<BatchSetWithBatches>(`/pricing/batch-sets/${setId}`)
  return data
}

export async function create(partId: number): Promise<BatchSet> {
  const { data } = await apiClient.post<BatchSet>('/pricing/batch-sets', { part_id: partId })
  return data
}

export async function update(setId: number, payload: BatchSetUpdate): Promise<BatchSet> {
  const { data } = await apiClient.put<BatchSet>(`/pricing/batch-sets/${setId}`, payload)
  return data
}

export async function remove(setId: number): Promise<void> {
  await apiClient.delete(`/pricing/batch-sets/${setId}`)
}

export async function freeze(setId: number): Promise<BatchSetWithBatches> {
  const { data } = await apiClient.post<BatchSetWithBatches>(
    `/pricing/batch-sets/${setId}/freeze`,
  )
  return data
}

export async function recalculate(setId: number): Promise<BatchSetWithBatches> {
  const { data } = await apiClient.post<BatchSetWithBatches>(
    `/pricing/batch-sets/${setId}/recalculate`,
  )
  return data
}

export async function clone(setId: number): Promise<BatchSet> {
  const { data } = await apiClient.post<BatchSet>(`/pricing/batch-sets/${setId}/clone`)
  return data
}

export async function addBatch(setId: number, quantity: number): Promise<Batch> {
  const { data } = await apiClient.post<Batch>(
    `/pricing/batch-sets/${setId}/batches`,
    null,
    { params: { quantity } },
  )
  return data
}

export async function removeBatch(setId: number, batchId: number): Promise<void> {
  await apiClient.delete(`/pricing/batch-sets/${setId}/batches/${batchId}`)
}

export async function freezeLooseBatches(partId: number): Promise<BatchSetWithBatches> {
  const { data } = await apiClient.post<BatchSetWithBatches>(
    `/pricing/parts/${partId}/freeze-batches-as-set`,
  )
  return data
}
