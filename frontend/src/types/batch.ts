export interface Batch {
  id: number
  batch_number: string
  part_id: number
  batch_set_id: number | null
  quantity: number
  is_default: boolean
  unit_time_min: number
  material_cost: number
  machining_cost: number
  setup_cost: number
  overhead_cost: number
  margin_cost: number
  coop_cost: number
  unit_cost: number
  unit_cost_net: number
  total_cost: number
  material_percent: number
  machining_percent: number
  setup_percent: number
  overhead_percent: number
  margin_percent: number
  coop_percent: number
  unit_price: number
  material_weight_kg: number | null
  material_price_per_kg: number | null
  is_frozen: boolean
  frozen_at: string | null
  frozen_by_id: number | null
  unit_price_frozen: number | null
  total_price_frozen: number | null
  version: number
  created_at: string
  updated_at: string
}

export interface BatchCreate {
  part_id: number
  quantity: number
  is_default?: boolean
}

export interface BatchUpdate {
  quantity?: number
  is_default?: boolean
  version: number
}
