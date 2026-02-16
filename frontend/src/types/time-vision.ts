/**
 * TimeVision - Types for AI machining time estimation
 */

export interface DrawingEstimationInfo {
  estimation_id: number | null
  status: string | null
  ai_provider: string | null
  ai_model: string | null
}

export interface DrawingFileInfo {
  filename: string
  size_bytes: number
  has_estimation: boolean
  file_id: number | null
  estimation_id: number | null
  status: string | null
  has_openai_estimation: boolean
  ai_provider: string | null
  ai_model: string | null
  v1: DrawingEstimationInfo | null
  v2: DrawingEstimationInfo | null
}

export interface VisionExtraction {
  part_type: 'ROT' | 'PRI' | 'COMBINED'
  complexity: 'simple' | 'medium' | 'complex'
  max_diameter_mm: number | null
  max_length_mm: number | null
  max_width_mm: number | null
  max_height_mm: number | null
  material_hint: string | null
  part_number_hint: string | null
  manufacturing_description: string
  operations: string[]
  surface_finish: string | null
  requires_grinding: boolean
}

export interface OperationBreakdown {
  operation: string
  time_min: number
  notes: string | null
}

export interface SimilarPartMatch {
  estimation_id: number
  pdf_filename: string
  part_type: string
  complexity: string
  max_diameter_mm: number | null
  max_length_mm: number | null
  actual_time_min: number
  estimated_time_min: number | null
  similarity_score: number
  score_breakdown: Record<string, number>
}

export interface FeatureItem {
  type: string
  count: number
  detail: string
  location?: string
  time_sec?: number
}

export interface FeaturesExtraction {
  drawing_number?: string
  part_name?: string
  part_type?: string
  material?: {
    designation: string
    standard?: string
    group?: string
  }
  overall_dimensions?: {
    max_diameter_mm?: number | null
    max_length_mm?: number | null
    max_width_mm?: number | null
    max_height_mm?: number | null
  }
  features: FeatureItem[]
  general_notes?: string[]
  feature_summary?: {
    total_features: number
    holes_total: number
    threads_total: number
    tight_tolerances: number
    surface_finish_count: number
  }
}

export interface TimeVisionEstimation {
  id: number
  pdf_filename: string
  file_id: number | null
  part_id: number | null
  status: 'pending' | 'extracted' | 'estimated' | 'calibrated' | 'verified'

  part_type: string | null
  complexity: string | null
  material_detected: string | null
  material_coefficient: number

  max_diameter_mm: number | null
  max_length_mm: number | null
  max_width_mm: number | null
  max_height_mm: number | null
  shape_ratio: number | null

  manufacturing_description: string | null
  operations_detected: string | null

  estimated_time_min: number | null
  estimation_reasoning: string | null
  estimation_breakdown_json: string | null
  confidence: string | null

  similar_parts_json: string | null
  vision_extraction_json: string | null

  actual_time_min: number | null
  actual_notes: string | null
  human_estimate_min: number | null

  estimation_type: string
  features_json?: string
  features_corrected_json?: string
  calculated_time_min?: number | null

  created_at: string | null
  updated_at: string | null
  version: number
  ai_provider: string
  ai_model: string | null
}

export interface TimeVisionListItem {
  id: number
  pdf_filename: string
  file_id: number | null
  part_id: number | null
  status: string
  part_type: string | null
  complexity: string | null
  material_detected: string | null
  estimated_time_min: number | null
  actual_time_min: number | null
  human_estimate_min: number | null
  confidence: string | null
  created_at: string | null
  ai_provider: string
  ai_model: string | null
  estimation_type: string
  calculated_time_min?: number | null
}
