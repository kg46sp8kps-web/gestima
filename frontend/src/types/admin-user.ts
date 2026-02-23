export interface AdminUser {
  id: number
  username: string
  email: string | null
  full_name: string | null
  role: string  // 'admin' | 'operator' | 'viewer'
  is_active: boolean
  created_at: string
  version: number
}

export interface AdminUserUpdate {
  email?: string | null
  role?: string
  is_active?: boolean
  version: number
}

export interface MaterialGroup {
  id: number
  code: string
  name: string
  density: number
  iso_group?: string | null
  hardness_hb?: number | null
  cutting_speed_turning?: number | null
  cutting_speed_milling?: number | null
  cutting_data_source?: string | null
  version: number
}

export interface MaterialGroupUpdate {
  code?: string
  name?: string
  density?: number | null
  iso_group?: string | null
  hardness_hb?: number | null
  cutting_speed_turning?: number | null
  cutting_speed_milling?: number | null
  version: number
}

export interface MaterialPriceCategory {
  id: number
  code: string
  name: string
  shape: string | null
  iso_group: string | null
  density: number | null
  cutting_speed_turning: number | null
  cutting_speed_milling: number | null
  material_group_id: number | null
  material_group: MaterialGroup | null
  version: number
}

export interface MaterialPriceCategoryUpdate {
  name?: string
  shape?: string | null
  iso_group?: string | null
  cutting_speed_turning?: number | null
  cutting_speed_milling?: number | null
  version: number
}

export interface MaterialNormUpdate {
  w_nr?: string | null
  en_iso?: string | null
  csn?: string | null
  aisi?: string | null
  material_group_id?: number | null
  note?: string | null
  version: number
}

export interface MaterialNorm {
  id: number
  w_nr: string | null
  en_iso: string | null
  csn: string | null
  aisi: string | null
  material_group_id: number | null
  material_group: MaterialGroup | null
  note: string | null
  version: number
  created_at: string
  updated_at: string
}

export interface TimeVisionListItem {
  id: number
  pdf_filename: string
  status: string
  ai_provider: string
  ai_model: string | null
  file_id: number | null
  part_id: number | null
  part_type: string | null
  complexity: string | null
  material_detected: string | null
  estimated_time_min: number | null
  actual_time_min: number | null
  human_estimate_min: number | null
  confidence: string | null
  created_at: string | null
  estimation_type: string
  calculated_time_min: number | null
}
