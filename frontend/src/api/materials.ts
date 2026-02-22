import { apiClient } from './client'
import type { MaterialItem, MaterialItemListResponse } from '@/types/material-item'
import type { MaterialGroup, MaterialPriceCategory } from '@/types/admin-user'

export async function getItems(params?: { group_id?: number; skip?: number; limit?: number }): Promise<MaterialItemListResponse> {
  const { data } = await apiClient.get<MaterialItemListResponse>('/materials/items', { params })
  return data
}

export async function getGroups(): Promise<MaterialGroup[]> {
  const { data } = await apiClient.get<MaterialGroup[]>('/materials/groups')
  return data
}

export async function getPriceCategories(): Promise<MaterialPriceCategory[]> {
  const { data } = await apiClient.get<MaterialPriceCategory[]>('/materials/price-categories')
  return data
}
