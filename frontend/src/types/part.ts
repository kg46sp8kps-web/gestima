export type PartStatus = 'draft' | 'active' | 'archived' | 'quote'
export type PartSource = 'manual' | 'infor_import' | 'quote_request'

export interface Part {
  id: number
  part_number: string
  article_number: string | null
  name: string | null
  revision: string | null
  customer_revision: string | null
  drawing_number: string | null
  status: PartStatus
  source: PartSource
  file_id: number | null
  scrap_rate_percent: number   // Zmetkovitost v % (default 0)
  // UOM (ADR-050)
  uom: 'ks'                    // vždy ks pro díly
  unit_weight: number | null   // kg/ks (pro Infor, expedici)
  version: number
  created_at: string
  updated_at: string
  created_by_name: string | null
}

export interface PartCreate {
  article_number: string
  name: string
  customer_revision?: string
  drawing_number?: string
}

export interface PartUpdate {
  part_number?: string
  article_number?: string
  name?: string
  revision?: string
  customer_revision?: string
  drawing_number?: string
  status?: PartStatus
  scrap_rate_percent?: number
  unit_weight?: number | null
  version: number
}

export interface PartListResponse {
  parts: Part[]
  total: number
  skip: number
  limit: number
}

export interface PartListParams {
  skip?: number
  limit?: number
  status?: PartStatus | ''
  source?: PartSource | ''
  search?: string
  has_drawing?: boolean
}
