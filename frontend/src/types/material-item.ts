export type StockShape =
  | 'round_bar'
  | 'square_bar'
  | 'flat_bar'
  | 'hexagonal_bar'
  | 'plate'
  | 'tube'
  | 'casting'
  | 'forging'

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
  surface_treatment: string | null
  supplier: string | null
  stock_available: number | null
  material_group_id: number
  price_category_id: number
  version: number
  created_at: string
  updated_at: string
}

export interface MaterialItemListResponse {
  items: MaterialItem[]
  total: number
}
