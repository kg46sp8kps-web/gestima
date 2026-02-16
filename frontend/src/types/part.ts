/**
 * Part types - matching backend Part model
 */

/**
 * Part status - matches backend PartStatus enum
 */
export type PartStatus = 'draft' | 'active' | 'archived' | 'quote'

/**
 * Part source - matches backend PartSource enum
 */
export type PartSource = 'manual' | 'infor_import' | 'quote_request'

export interface PartBase {
  part_number: string
  article_number: string | null
  name: string
  revision: string | null
  customer_revision: string | null
  drawing_number: string | null
  drawing_path: string | null
  status: PartStatus
  source: PartSource
  length: number
  notes: string
}

export interface Part extends PartBase {
  id: number
  version: number
  created_at: string
  updated_at: string
  created_by_name?: string | null
}

/**
 * Create new part - simplified (part_number auto-generated)
 */
export interface PartCreate {
  article_number?: string
  name?: string
  customer_revision?: string | null
  drawing_number?: string | null
  notes?: string | null
}

export interface PartUpdate extends Partial<PartBase> {
  version: number
}

export interface PartsSearchResponse {
  parts: Part[]
  total: number
  skip: number
  limit: number
}

export interface StockCostResponse {
  volume_mm3: number
  weight_kg: number
  price_per_kg: number
  cost: number
  density: number
}

export interface PriceBreakdown {
  machine_amortization: number
  machine_labor: number
  machine_tools: number
  machine_overhead: number
  machine_total: number
  machine_setup_time_min: number
  machine_setup_cost: number
  machine_operation_time_min: number
  machine_operation_cost: number
  overhead_coefficient: number
  work_with_overhead: number
  overhead_markup: number
  overhead_percent: number
  margin_coefficient: number
  work_with_margin: number
  margin_markup: number
  margin_percent: number
  coop_cost_raw: number
  coop_coefficient: number
  coop_cost: number
  material_cost_raw: number
  stock_coefficient: number
  material_cost: number
  total_cost: number
  quantity: number
  cost_per_piece: number
}
