// GESTIMA - Manual Time Estimation Types (Phase 4)

export type PartType = 'ROT' | 'PRI'

export interface MachiningTimeBreakdown {
  material: string
  material_category: string
  iso_group: string
  stock_volume_mm3: number
  part_volume_mm3: number
  material_to_remove_mm3: number
  surface_area_mm2: number
  mrr_roughing_cm3_min: number
  finishing_rate_cm2_min: number
  constraint_multiplier: number
  critical_constraints: string[]
  stock_type: string
}

export interface EstimationRecord {
  id: number
  filename: string
  part_type: PartType
  extraction_timestamp: string
  part_volume_mm3: number
  removal_ratio: number
  surface_area_mm2: number
  bbox_x_mm: number
  bbox_y_mm: number
  bbox_z_mm: number
  max_dimension_mm: number
  rotational_score: number
  cylindrical_surface_ratio: number
  planar_surface_ratio: number
  material_group_code: string
  material_machinability_index: number
  estimated_time_min: number | null
  estimated_by_user_id: number | null
  estimation_date: string | null
  actual_time_min: number | null
  actual_time_source: string | null
  actual_time_date: string | null
  data_source?: string | null
  confidence?: number | null
  needs_manual_review?: boolean | null
  decision_log?: string | null
  created_at: string
  corrected_material_code?: string | null
  correction_notes?: string | null
  // Time estimation fields (from MachiningTimeEstimateResponse)
  total_time_min?: number
  roughing_time_min?: number
  roughing_time_main?: number
  roughing_time_aux?: number
  finishing_time_min?: number
  finishing_time_main?: number
  finishing_time_aux?: number
  breakdown?: MachiningTimeBreakdown
}

export interface SimilarPart {
  id: number
  filename: string
  part_type: PartType
  rotational_score: number
  estimated_time_min: number | null
  similarity_score: number
}

// Legacy types (DEPRECATED - kept for backward compatibility with old UI)
export type MachiningTimeEstimation = EstimationRecord
export type BatchEstimationResults = EstimationRecord[]
