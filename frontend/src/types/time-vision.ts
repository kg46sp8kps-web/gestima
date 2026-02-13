/**
 * TimeVision - Types for AI machining time estimation
 */

export interface DrawingFileInfo {
  filename: string
  size_bytes: number
  has_estimation: boolean
  estimation_id: number | null
  status: string | null
  has_openai_estimation: boolean
  ai_provider: string | null
  ai_model: string | null
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

export interface TimeVisionEstimation {
  id: number
  pdf_filename: string
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

  created_at: string | null
  updated_at: string | null
  version: number
  ai_provider: string
  ai_model: string | null
}

export interface TimeVisionListItem {
  id: number
  pdf_filename: string
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
}
