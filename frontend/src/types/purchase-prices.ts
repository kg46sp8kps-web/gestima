export interface TierAnalysis {
  tier_id: number
  tier_label: string
  min_weight: number
  max_weight: number | null
  avg_price_per_kg: number
  total_qty_kg: number
  total_cost_czk: number
  po_line_count: number
  min_price: number
  max_price: number
  current_price: number | null
  diff_pct: number | null
  current_tier_version: number
  sufficient_data: boolean
}

export interface SuggestedBoundary {
  tier_index: number
  current_max_weight: number | null
  suggested_max_weight: number | null
  reason: string
}

export interface WeightDistribution {
  p25: number
  p50: number
  p75: number
  min_qty: number
  max_qty: number
  avg_qty: number
  sample_count: number
  suggested_boundaries: SuggestedBoundary[]
}

export interface TierBoundaryUpdate {
  tier_id: number
  new_min_weight: number
  new_max_weight: number | null
  version: number
}

export interface ApplyBoundariesRequest {
  category_id: number
  tier_boundaries: TierBoundaryUpdate[]
}

export interface PriceCategoryAnalysis {
  price_category_id: number
  price_category_code: string
  price_category_name: string
  material_group_id: number | null
  material_group_name: string | null
  shape: string | null
  total_po_lines: number
  total_qty_received_kg: number
  total_cost_czk: number
  weighted_avg_price_per_kg: number
  min_unit_price: number
  max_unit_price: number
  unique_vendors: number
  top_vendors: string[]
  tiers: TierAnalysis[]
  weight_distribution: WeightDistribution | null
  quarterly_prices: Record<string, number>
}

export interface UnmatchedItem {
  item: string
  description: string
  w_nr: string | null
  reason: string
  total_cost: number
  count: number
}

export interface PurchasePriceAnalysisResponse {
  year_from: number
  date_range: string
  total_po_lines_fetched: number
  total_po_lines_matched: number
  total_po_lines_unmatched: number
  unique_materials: number
  categories: PriceCategoryAnalysis[]
  unmatched: UnmatchedItem[]
  cached: boolean
  fetch_time_seconds: number
}

export interface TierUpdate {
  tier_id: number
  new_price: number
  version: number
}

export interface ApplyPriceRequest {
  category_id: number
  tier_updates: TierUpdate[]
}

export interface ApplyPriceResponse {
  success: boolean
  updated_count: number
  errors: string[]
}
