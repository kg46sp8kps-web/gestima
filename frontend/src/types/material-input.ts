export type StockShape =
  | 'round_bar'
  | 'square_bar'
  | 'flat_bar'
  | 'hexagonal_bar'
  | 'plate'
  | 'tube'
  | 'casting'
  | 'forging'

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

export interface OperationSummary {
  id: number
  seq: number
  name: string
  type: string
}

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
  weight_kg: number | null
  cost_per_piece: number | null
  price_per_kg: number | null
  material_item: MaterialItemSummary | null
  price_category: PriceCategorySummary | null
  operations: OperationSummary[]
  version: number
  created_at: string
  updated_at: string
}
