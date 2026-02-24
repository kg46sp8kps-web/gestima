export type StockShape =
  | 'round_bar'
  | 'square_bar'
  | 'flat_bar'
  | 'hexagonal_bar'
  | 'plate'
  | 'tube'
  | 'casting'
  | 'forging'

export type UnitOfMeasure = 'kg' | 'ks' | 'm' | 'mm'

export interface MaterialItem {
  id: number
  material_number: string
  code: string
  name: string
  shape: StockShape
  diameter: number | null
  width: number | null
  height: number | null
  thickness: number | null
  wall_thickness: number | null
  // UOM (ADR-050)
  uom: UnitOfMeasure           // základní měrná jednotka (kg/ks)
  conv_uom: 'm' | 'mm' | null  // konverzní jednotka pro katalogový přepočet
  conv_factor: number | null   // 1 conv_uom = conv_factor uom (např. 1 m = 15.41 kg)
  weight_per_meter: number | null  // DEPRECATED — ponecháno pro backwards compat
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

export interface MaterialItemDetail extends MaterialItem {
  price_category: {
    id: number
    code: string
    name: string
  }
}
