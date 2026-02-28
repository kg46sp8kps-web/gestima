import { apiClient, adminClient } from './client'
import type { MaterialItemDetail, MaterialItemListResponse } from '@/types/material-item'
import type { MaterialGroup, MaterialGroupUpdate, MaterialPriceCategory, MaterialPriceCategoryUpdate, MaterialPriceTier, MaterialPriceTierCreate, MaterialPriceTierUpdate } from '@/types/admin-user'

export interface MaterialItemUomUpdate {
  uom: string
  conv_uom: string | null
  conv_factor: number | null
  version: number
}

export interface MaterialItemListParams {
  group_id?: number
  skip?: number
  limit?: number
  search?: string
  shape?: string
  norm_query?: string
  diameter_min?: number
  diameter_max?: number
  width_min?: number
  width_max?: number
  thickness_min?: number
  thickness_max?: number
  wall_thickness_min?: number
  wall_thickness_max?: number
}

export async function getItems(params?: MaterialItemListParams): Promise<MaterialItemListResponse> {
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

export async function getPriceTiers(categoryId: number): Promise<MaterialPriceTier[]> {
  const { data } = await apiClient.get<MaterialPriceTier[]>('/materials/price-tiers', { params: { category_id: categoryId } })
  return data
}

export async function createPriceTier(payload: MaterialPriceTierCreate): Promise<MaterialPriceTier> {
  const { data } = await adminClient.post<MaterialPriceTier>('/materials/price-tiers', payload)
  return data
}

export async function updatePriceTier(id: number, payload: MaterialPriceTierUpdate): Promise<MaterialPriceTier> {
  const { data } = await adminClient.put<MaterialPriceTier>(`/materials/price-tiers/${id}`, payload)
  return data
}

export async function deletePriceTier(id: number): Promise<void> {
  await adminClient.delete(`/materials/price-tiers/${id}`)
}
