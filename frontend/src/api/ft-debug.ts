import { apiClient } from './client'

export async function getFtDebugParts(minVp: number) {
  const { data } = await apiClient.get('/ft/debug/parts', { params: { min_vp: minVp } })
  return data
}

export async function exportFtDebug(partsIds: number[]) {
  const { data } = await apiClient.post('/ft/debug/export', { part_ids: partsIds }, { responseType: 'blob' })
  return data
}

export async function runFtInference(partId: number) {
  const { data } = await apiClient.post('/ft/debug/inference', { part_id: partId })
  return data
}
