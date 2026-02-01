/**
 * Materials API - Material groups, price categories, and items
 *
 * Endpoints from materials_router.py
 */

import { apiClient, adminClient } from './client'
import type {
  MaterialNorm,
  MaterialNormCreate,
  MaterialNormUpdate,
  MaterialGroup,
  MaterialGroupCreate,
  MaterialGroupUpdate,
  MaterialPriceCategory,
  MaterialPriceCategoryCreate,
  MaterialPriceCategoryUpdate,
  MaterialPriceCategoryWithTiers,
  MaterialPriceTier,
  MaterialPriceTierCreate,
  MaterialPriceTierUpdate,
  MaterialItem,
  MaterialItemWithGroup,
  StockCost,
  MaterialParseResult
} from '@/types/material'

// =============================================================================
// Material Norms (Admin only)
// =============================================================================

/**
 * Get all material norms
 */
export async function getMaterialNorms(): Promise<MaterialNorm[]> {
  const response = await adminClient.get<MaterialNorm[]>('/material-norms')
  return response.data
}

/**
 * Search material norms
 */
export async function searchMaterialNorms(query: string, limit = 50): Promise<MaterialNorm[]> {
  const response = await adminClient.get<MaterialNorm[]>('/material-norms/search', {
    params: { q: query, limit }
  })
  return response.data
}

/**
 * Create material norm
 */
export async function createMaterialNorm(data: MaterialNormCreate): Promise<MaterialNorm> {
  const response = await adminClient.post<MaterialNorm>('/material-norms', data)
  return response.data
}

/**
 * Update material norm
 */
export async function updateMaterialNorm(normId: number, data: MaterialNormUpdate): Promise<MaterialNorm> {
  const response = await adminClient.put<MaterialNorm>(`/material-norms/${normId}`, data)
  return response.data
}

/**
 * Delete material norm (soft delete)
 */
export async function deleteMaterialNorm(normId: number): Promise<void> {
  await adminClient.delete(`/material-norms/${normId}`)
}

// =============================================================================
// Material Groups
// =============================================================================

/**
 * Get all material groups (for calculations: density, cutting conditions)
 */
export async function getMaterialGroups(): Promise<MaterialGroup[]> {
  const response = await apiClient.get<MaterialGroup[]>('/materials/groups')
  return response.data
}

/**
 * Get single material group
 */
export async function getMaterialGroup(groupId: number): Promise<MaterialGroup> {
  const response = await apiClient.get<MaterialGroup>(`/materials/groups/${groupId}`)
  return response.data
}

// =============================================================================
// Material Groups (Admin CRUD)
// =============================================================================

/**
 * Get all material groups (Admin)
 */
export async function getAdminMaterialGroups(): Promise<MaterialGroup[]> {
  const response = await adminClient.get<MaterialGroup[]>('/material-groups')
  return response.data
}

/**
 * Create material group (Admin)
 */
export async function createMaterialGroup(data: MaterialGroupCreate): Promise<MaterialGroup> {
  const response = await adminClient.post<MaterialGroup>('/material-groups', data)
  return response.data
}

/**
 * Update material group (Admin)
 */
export async function updateMaterialGroup(groupId: number, data: MaterialGroupUpdate): Promise<MaterialGroup> {
  const response = await adminClient.put<MaterialGroup>(`/material-groups/${groupId}`, data)
  return response.data
}

/**
 * Delete material group (Admin, soft delete)
 */
export async function deleteMaterialGroup(groupId: number): Promise<void> {
  await adminClient.delete(`/material-groups/${groupId}`)
}

// =============================================================================
// Price Categories
// =============================================================================

/**
 * Get all price categories (for material dropdown)
 */
export async function getPriceCategories(): Promise<MaterialPriceCategory[]> {
  const response = await apiClient.get<MaterialPriceCategory[]>('/materials/price-categories')
  return response.data
}

/**
 * Get price category with tiers
 */
export async function getPriceCategoryWithTiers(categoryId: number): Promise<MaterialPriceCategoryWithTiers> {
  const response = await apiClient.get<MaterialPriceCategoryWithTiers>(`/materials/price-categories/${categoryId}`)
  return response.data
}

/**
 * Get all price tiers (optional filtering)
 */
export async function getPriceTiers(categoryId?: number): Promise<MaterialPriceTier[]> {
  const params = categoryId ? { category_id: categoryId } : {}
  const response = await apiClient.get<MaterialPriceTier[]>('/materials/price-tiers', { params })
  return response.data
}

// =============================================================================
// Price Categories (Admin CRUD)
// =============================================================================

/**
 * Create price category (Admin)
 */
export async function createPriceCategory(data: MaterialPriceCategoryCreate): Promise<MaterialPriceCategory> {
  const response = await adminClient.post<MaterialPriceCategory>('/material-price-categories', data)
  return response.data
}

/**
 * Update price category (Admin)
 */
export async function updatePriceCategory(categoryId: number, data: MaterialPriceCategoryUpdate): Promise<MaterialPriceCategory> {
  const response = await adminClient.put<MaterialPriceCategory>(`/material-price-categories/${categoryId}`, data)
  return response.data
}

/**
 * Delete price category (Admin, soft delete)
 */
export async function deletePriceCategory(categoryId: number): Promise<void> {
  await adminClient.delete(`/material-price-categories/${categoryId}`)
}

// =============================================================================
// Price Tiers (CRUD)
// =============================================================================

/**
 * Create price tier
 */
export async function createPriceTier(data: MaterialPriceTierCreate): Promise<MaterialPriceTier> {
  const response = await apiClient.post<MaterialPriceTier>('/materials/price-tiers', data)
  return response.data
}

/**
 * Update price tier
 */
export async function updatePriceTier(tierId: number, data: MaterialPriceTierUpdate): Promise<MaterialPriceTier> {
  const response = await apiClient.put<MaterialPriceTier>(`/materials/price-tiers/${tierId}`, data)
  return response.data
}

/**
 * Delete price tier
 */
export async function deletePriceTier(tierId: number): Promise<void> {
  await apiClient.delete(`/materials/price-tiers/${tierId}`)
}

// =============================================================================
// Material Items
// =============================================================================

/**
 * Get material items (with optional filtering)
 */
export async function getMaterialItems(params?: {
  group_id?: number
  shape?: string
  skip?: number
  limit?: number
}): Promise<MaterialItem[]> {
  const response = await apiClient.get<MaterialItem[]>('/materials/items', { params })
  return response.data
}

/**
 * Get material item by number
 */
export async function getMaterialItem(materialNumber: string): Promise<MaterialItemWithGroup> {
  const response = await apiClient.get<MaterialItemWithGroup>(`/materials/items/${materialNumber}`)
  return response.data
}

// =============================================================================
// Stock Cost Calculation
// =============================================================================

/**
 * Calculate stock cost for a part
 */
export async function getStockCost(partNumber: string): Promise<StockCost> {
  const response = await apiClient.get<StockCost>(`/parts/${partNumber}/stock-cost`)
  return response.data
}

// =============================================================================
// Material Parser
// =============================================================================

/**
 * Parse material description (AI-powered)
 * Example: "KR D30 L100 ocel" → { shape: 'round_bar', diameter: 30, length: 100 }
 */
export async function parseMaterialDescription(description: string): Promise<MaterialParseResult> {
  // Backend expects query parameter
  const response = await apiClient.post<MaterialParseResult>(
    '/materials/parse',
    null,
    {
      params: { description }
    }
  )
  return response.data
}

// =============================================================================
// Reference Data (for dropdowns)
// =============================================================================

/**
 * Get price categories for dropdown (simplified)
 */
export async function getPriceCategoriesForDropdown(): Promise<Array<{
  id: number
  code: string
  name: string
}>> {
  const categories = await getPriceCategories()
  return categories.map(c => ({
    id: c.id,
    code: c.code,
    name: c.name
  }))
}
