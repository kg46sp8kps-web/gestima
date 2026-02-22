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
  length: number
  notes: string
  file_id: number | null
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
  notes?: string
}

export interface PartUpdate {
  part_number?: string
  article_number?: string
  name?: string
  revision?: string
  customer_revision?: string
  drawing_number?: string
  status?: PartStatus
  length?: number
  notes?: string
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
