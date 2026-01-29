/**
 * Batch and BatchSet types - matching backend models
 */

/**
 * Batch - single pricing calculation for a quantity
 */
export interface Batch {
  id: number
  batch_number: string
  part_id: number
  batch_set_id: number | null
  quantity: number
  is_default: boolean
  unit_time_min: number

  // Costs
  material_cost: number
  machining_cost: number
  setup_cost: number
  overhead_cost: number
  margin_cost: number
  coop_cost: number
  unit_cost: number
  unit_price: number  // Alias/computed field
  total_cost: number

  // Material snapshot (ADR-017)
  material_weight_kg: number | null
  material_price_per_kg: number | null

  // Freeze fields (ADR-012)
  is_frozen: boolean
  frozen_at: string | null
  frozen_by_id: number | null
  snapshot_data: Record<string, any> | null
  unit_price_frozen: number | null
  total_price_frozen: number | null

  // Computed percentages (from backend)
  material_percent: number
  machining_percent: number
  setup_percent: number
  overhead_percent: number
  margin_percent: number
  coop_percent: number

  // Audit
  version: number
  created_at: string
  updated_at: string
}

export interface BatchCreate {
  part_id: number
  quantity: number
  batch_number?: string
  is_default?: boolean
}

export interface BatchUpdate {
  quantity?: number
  is_default?: boolean
  version: number
}

/**
 * BatchSet - groups multiple batches for a part
 */
export interface BatchSet {
  id: number
  set_number: string
  part_id: number | null
  name: string
  status: 'draft' | 'frozen'
  frozen_at: string | null
  frozen_by_id: number | null
  created_at: string
  updated_at: string
  version: number
}

export interface BatchSetWithBatches extends BatchSet {
  batches: Batch[]
  batch_count: number
  total_value: number
}

export interface BatchSetListItem extends BatchSet {
  batch_count: number
}

export interface BatchSetCreate {
  part_id: number
  name?: string
}

export interface BatchSetUpdate {
  name?: string
  version: number
}

/**
 * Response types
 */
export interface BatchesForPartResponse {
  batches: Batch[]
  total: number
}

/**
 * Helper type for cost breakdown display
 */
export interface CostBreakdown {
  label: string
  value: number
  percent: number
  color: string
}
