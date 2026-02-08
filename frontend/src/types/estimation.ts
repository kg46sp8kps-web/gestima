/**
 * Machining Time Estimation Types
 *
 * Types for volume-based machining time calculations
 */

export interface MachiningStrategy {
  rough: {
    mrr_mm3_min: number
    cutting_time_min: number
  }
  semi_finish?: {
    mrr_mm3_min: number
    cutting_time_min: number
  }
  finish: {
    mrr_mm3_min: number
    cutting_time_min: number
  }
}

export interface EstimationBreakdown {
  material: string
  iso_group?: string
  stock_volume_mm3: number
  part_volume_mm3: number
  material_to_remove_mm3: number
  material_removal_percent?: number
  surface_area_mm2: number
  mrr_roughing_cm3_min: number
  finishing_rate_cm2_min: number
  machining_strategy?: MachiningStrategy
  critical_constraints: string[]
  constraint_multiplier: number
  pure_machining_time_min?: number
  stock_type?: string
}

export interface MachiningTimeEstimation {
  filename: string
  part_type?: string
  roughing_time_min: number
  roughing_time_main: number
  roughing_time_aux: number
  finishing_time_min: number
  finishing_time_main: number
  finishing_time_aux: number
  setup_time_min: number
  total_time_min: number
  breakdown: EstimationBreakdown
  deterministic: boolean
}

export interface BatchEstimationResults {
  results: MachiningTimeEstimation[]
  total_files: number
  avg_time_min: number
  total_volume_removed_cm3: number
}
