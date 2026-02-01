/**
 * Part types - matching backend Part model
 */

/**
 * Stock shape - matches backend StockShape enum
 */
export type StockShape =
  | 'round_bar'     // Tyč kruhová
  | 'square_bar'    // Tyč čtvercová
  | 'flat_bar'      // Tyč plochá
  | 'hexagonal_bar' // Tyč šestihranná
  | 'plate'         // Plech
  | 'tube'          // Trubka
  | 'casting'       // Odlitek
  | 'forging'       // Výkovek

export interface PartBase {
  part_number: string
  article_number: string | null
  drawing_path: string | null
  name: string
  customer_revision: string | null
  drawing_number: string | null
  notes: string
  material_item_id: number | null
  price_category_id: number | null
  length: number
  stock_shape: StockShape | null
  stock_diameter: number | null
  stock_length: number | null
  stock_width: number | null
  stock_height: number | null
  stock_wall_thickness: number | null
}

export interface Part extends PartBase {
  id: number
  version: number
  created_at: string
  updated_at: string
}

/**
 * Create new part - simplified (part_number auto-generated)
 */
export interface PartCreate {
  article_number: string  // REQUIRED
  drawing_path?: string | null
  name: string  // REQUIRED
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
