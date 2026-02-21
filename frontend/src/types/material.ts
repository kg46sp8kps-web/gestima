/**
 * Material Types for Vue SPA
 *
 * Maps to backend:
 * - app/models/material.py
 * - app/models/enums.py (StockShape)
 */

/**
 * Stock shape - matches backend StockShape enum (app/models/material.py)
 */
export type StockShape = 'round_bar' | 'square_bar' | 'flat_bar' | 'hexagonal_bar' | 'plate' | 'tube' | 'casting' | 'forging'

/**
 * Stock shape options for dropdown
 */
export const STOCK_SHAPE_OPTIONS: Array<{ value: StockShape; label: string }> = [
  { value: 'round_bar', label: 'Tyč kruhová' },
  { value: 'square_bar', label: 'Tyč čtvercová' },
  { value: 'flat_bar', label: 'Tyč plochá' },
  { value: 'hexagonal_bar', label: 'Tyč šestihranná' },
  { value: 'plate', label: 'Plech / Deska' },
  { value: 'tube', label: 'Trubka' },
  { value: 'casting', label: 'Odlitek' },
  { value: 'forging', label: 'Výkovek' }
]

/**
 * Get label for stock shape
 */
export function getStockShapeLabel(shape: StockShape | null | undefined): string {
  if (!shape) return '-'
  const option = STOCK_SHAPE_OPTIONS.find(o => o.value === shape)
  return option?.label || shape
}

/**
 * Get which dimension fields to show based on shape
 */
export function getShapeDimensionFields(shape: StockShape | null | undefined): {
  showDiameter: boolean
  showWidth: boolean
  showHeight: boolean
  showWallThickness: boolean
} {
  if (!shape) {
    return { showDiameter: false, showWidth: false, showHeight: false, showWallThickness: false }
  }

  return {
    showDiameter: ['round_bar', 'hexagonal_bar', 'tube', 'casting', 'forging'].includes(shape),
    showWidth: ['flat_bar', 'square_bar', 'plate'].includes(shape),
    showHeight: ['flat_bar', 'plate'].includes(shape),
    showWallThickness: shape === 'tube'
  }
}

// =============================================================================
// Material Norm (conversion table: W.Nr | EN ISO | ČSN | AISI → MaterialGroup)
// =============================================================================

export interface MaterialNorm {
  id: number
  w_nr: string | null
  en_iso: string | null
  csn: string | null
  aisi: string | null
  material_group_id: number
  material_group?: MaterialGroup | null
  note: string | null
  version: number
  created_at: string
  updated_at: string
}

export interface MaterialNormCreate {
  w_nr?: string | null
  en_iso?: string | null
  csn?: string | null
  aisi?: string | null
  material_group_id: number
  note?: string | null
}

export interface MaterialNormUpdate {
  w_nr?: string | null
  en_iso?: string | null
  csn?: string | null
  aisi?: string | null
  material_group_id?: number
  note?: string | null
  version: number
}

// =============================================================================
// Material Group (for calculations: density, cutting conditions)
// =============================================================================

export interface MaterialGroup {
  id: number
  code: string
  name: string
  density: number  // kg/dm³
  version: number
  created_at: string
  updated_at: string

  // Cutting parameters (nullable)
  iso_group?: string | null
  hardness_hb?: number | null
  mrr_turning_roughing?: number | null
  mrr_turning_finishing?: number | null
  mrr_milling_roughing?: number | null
  mrr_milling_finishing?: number | null
  cutting_speed_turning?: number | null
  cutting_speed_milling?: number | null
  feed_turning?: number | null
  feed_milling?: number | null
  deep_pocket_penalty?: number | null
  thin_wall_penalty?: number | null
  cutting_data_source?: string | null
}

export interface MaterialGroupCreate {
  code: string
  name: string
  density: number
}

export interface MaterialGroupUpdate {
  code?: string
  name?: string
  density?: number

  // Cutting parameters (nullable)
  iso_group?: string | null
  hardness_hb?: number | null
  mrr_turning_roughing?: number | null
  mrr_turning_finishing?: number | null
  mrr_milling_roughing?: number | null
  mrr_milling_finishing?: number | null
  cutting_speed_turning?: number | null
  cutting_speed_milling?: number | null
  feed_turning?: number | null
  feed_milling?: number | null
  deep_pocket_penalty?: number | null
  thin_wall_penalty?: number | null
  cutting_data_source?: string | null

  version: number  // Required for optimistic locking
}

// =============================================================================
// Material Price Category (groups stock items by price tiers)
// =============================================================================

export interface MaterialPriceCategory {
  id: number
  code: string
  name: string
  material_group_id: number | null
  version: number
  created_at: string
  updated_at: string
}

export interface MaterialPriceCategoryWithGroup extends MaterialPriceCategory {
  material_group: MaterialGroup | null
}

export interface MaterialPriceTier {
  id: number
  price_category_id: number
  min_weight: number
  max_weight: number | null
  price_per_kg: number
  version: number
  created_at: string
  updated_at: string
}

export interface MaterialPriceCategoryWithTiers extends MaterialPriceCategory {
  tiers: MaterialPriceTier[]
}

export interface MaterialPriceCategoryCreate {
  code: string
  name: string
  material_group_id: number | null
}

export interface MaterialPriceCategoryUpdate {
  code?: string
  name?: string
  material_group_id?: number | null
  version: number  // Required for optimistic locking
}

export interface MaterialPriceTierCreate {
  price_category_id: number
  min_weight: number
  max_weight: number | null
  price_per_kg: number
}

export interface MaterialPriceTierUpdate {
  min_weight?: number
  max_weight?: number | null
  price_per_kg?: number
  version: number  // Required for optimistic locking
}

// =============================================================================
// Material Item (specific stock item)
// =============================================================================

export interface MaterialItem {
  id: number
  material_number: string
  code: string
  name: string
  shape: StockShape
  diameter: number | null
  width: number | null
  thickness: number | null
  wall_thickness: number | null
  weight_per_meter: number | null
  standard_length: number | null
  norms: string | null
  supplier_code: string | null
  supplier: string | null
  stock_available: number
  material_group_id: number
  price_category_id: number
  version: number
  created_at: string
  updated_at: string
}

export interface MaterialItemWithGroup extends MaterialItem {
  group: MaterialGroup
  price_category: MaterialPriceCategory
}

// =============================================================================
// Stock Cost (calculated by backend)
// =============================================================================

export interface StockCost {
  cost: number
  weight_kg: number
  volume_mm3: number
  price_per_kg: number
}

// =============================================================================
// Material Summary (cost calculation with price tier details)
// =============================================================================

export interface MaterialSummary {
  weight_kg: number
  total_weight_kg: number
  price_category: {
    code: string
    name: string
  }
  price_tier: {
    min_weight: number
    max_weight: number | null
    price_per_kg: number
  } | null
  price_per_kg: number
  cost_per_piece: number
  total_cost: number
  tier_range: string
  tier_id: number | null  // ID of selected tier for highlighting
}

// =============================================================================
// Material Parse Result (from AI parser)
// =============================================================================

export interface MaterialParseResult {
  shape: StockShape | null
  diameter: number | null
  length: number | null
  width: number | null
  height: number | null
  thickness: number | null
  wall_thickness: number | null
  material_norm: string | null
  material_category: string | null
  confidence: number

  // MaterialGroup (z MaterialNorm FK)
  suggested_material_group_id: number | null
  suggested_material_group_code: string | null
  suggested_material_group_name: string | null
  suggested_material_group_density: number | null

  // PriceCategory (shape + group match)
  suggested_price_category_id: number | null
  suggested_price_category_code: string | null
  suggested_price_category_name: string | null

  // MaterialItem - konkrétní položka (když najde přesnou shodu)
  suggested_material_item_id: number | null
  suggested_material_item_code: string | null
  suggested_material_item_name: string | null

  raw_input: string
  matched_pattern: string
  warnings: string[]
}

// =============================================================================
// MaterialInput (ADR-024: v1.8.0 refactor)
// Part → N MaterialInputs (multiple materials per part, M:N with operations)
// =============================================================================

export interface MaterialInput {
  id: number
  part_id: number
  seq: number
  price_category_id: number
  material_item_id: number | null
  stock_shape: StockShape
  stock_diameter: number | null
  stock_length: number | null
  stock_width: number | null
  stock_height: number | null
  stock_wall_thickness: number | null
  quantity: number
  notes: string | null
  version: number
  created_at: string
  updated_at: string
}

export interface MaterialItemSummary {
  id: number
  code: string
  name: string
  material_number: string
}

export interface PriceCategorySummary {
  id: number
  code: string
  name: string
}

export interface MaterialInputWithOperations extends MaterialInput {
  operations: Array<{
    id: number
    seq: number
    name: string
    type: string
  }>
  weight_kg?: number | null
  cost_per_piece?: number | null
  price_per_kg?: number | null
  material_item?: MaterialItemSummary | null
  price_category?: PriceCategorySummary | null
}

export interface MaterialInputCreate {
  part_id: number
  seq?: number
  price_category_id: number
  material_item_id?: number | null
  stock_shape: StockShape
  stock_diameter?: number | null
  stock_length?: number | null
  stock_width?: number | null
  stock_height?: number | null
  stock_wall_thickness?: number | null
  quantity?: number
  notes?: string | null
}

export interface MaterialInputUpdate {
  seq?: number
  price_category_id?: number
  material_item_id?: number | null
  stock_shape?: StockShape
  stock_diameter?: number | null
  stock_length?: number | null
  stock_width?: number | null
  stock_height?: number | null
  stock_wall_thickness?: number | null
  quantity?: number
  notes?: string | null
  version: number  // Required for optimistic locking
}

// =============================================================================
// DEPRECATED (v1.8.0) - Part no longer has stock_* fields!
// Use MaterialInput instead. Will be removed in v2.0.
// =============================================================================

/** @deprecated Use MaterialInput instead */
export interface PartMaterialData {
  stock_shape: StockShape | null
  price_category_id: number | null
  stock_diameter: number
  stock_length: number
  stock_width: number
  stock_height: number
  stock_wall_thickness: number
  version: number
}

/** @deprecated Use MaterialInputUpdate instead */
export interface PartMaterialUpdate {
  stock_shape?: StockShape | null
  price_category_id?: number | null
  stock_diameter?: number
  stock_length?: number
  stock_width?: number
  stock_height?: number
  stock_wall_thickness?: number
  version: number
}
