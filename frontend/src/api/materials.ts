import { apiClient } from './client'
import type { MaterialItemDetail, MaterialItemListResponse } from '@/types/material-item'
import type { MaterialGroup, MaterialGroupUpdate, MaterialPriceCategory, MaterialPriceCategoryUpdate } from '@/types/admin-user'

export interface MaterialItemUomUpdate {
  uom: string
  conv_uom: string | null
  conv_factor: number | null
  version: number
}

export async function getItems(params?: { group_id?: number; skip?: number; limit?: number }): Promise<MaterialItemListResponse> {
  const { data } = await apiClient.get<MaterialItemListResponse>('/materials/items', { params })
  return data
}

export async function getByNumber(materialNumber: string): Promise<MaterialItemDetail> {
  const { data } = await apiClient.get<MaterialItemDetail>(`/materials/items/${encodeURIComponent(materialNumber)}`)
  return data
}

export async function updateItem(materialNumber: string, payload: MaterialItemUomUpdate): Promise<MaterialItemDetail> {
  const { data } = await apiClient.put<MaterialItemDetail>(`/materials/items/${encodeURIComponent(materialNumber)}`, payload)
  return data
}

export async function getGroups(): Promise<MaterialGroup[]> {
  const { data } = await apiClient.get<MaterialGroup[]>('/materials/groups')
  return data
}

export async function updateGroup(id: number, payload: MaterialGroupUpdate): Promise<MaterialGroup> {
  const { data } = await apiClient.put<MaterialGroup>(`/materials/groups/${id}`, payload)
  return data
}

export async function getPriceCategories(): Promise<MaterialPriceCategory[]> {
  const { data } = await apiClient.get<MaterialPriceCategory[]>('/materials/price-categories')
  return data
}

export async function updatePriceCategory(id: number, payload: MaterialPriceCategoryUpdate): Promise<MaterialPriceCategory> {
  const { data } = await apiClient.put<MaterialPriceCategory>(`/materials/price-categories/${id}`, payload)
  return data
}
