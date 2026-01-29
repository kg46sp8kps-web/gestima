/**
 * Materials API - Material groups, price categories, and items
 *
 * Endpoints from materials_router.py
 */

import { apiClient } from './client'
import type {
  MaterialGroup,
  MaterialPriceCategory,
  MaterialPriceCategoryWithTiers,
  MaterialPriceTier,
  MaterialItem,
  MaterialItemWithGroup,
  StockCost,
  MaterialParseResult
} from '@/types/material'

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
  // Backend expects form data, not JSON body
  const formData = new URLSearchParams()
  formData.append('description', description)

  const response = await apiClient.post<MaterialParseResult>(
    '/materials/parse',
    formData,
    {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
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
