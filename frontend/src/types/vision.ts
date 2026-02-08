/**
 * Vision Debug types - PDF annotation refinement
 */

export interface VisionDebugPart {
  id: number
  part_number: string
  description: string | null
  drawing_path: string | null
}

export interface RefinementFeature {
  type: string
  dimension: number
  depth: number
  step_data: {
    r_avg: number
    length: number
  }
  dimension_error: number
  pdf_bbox: number[]
}

export interface RefinementStatus {
  iteration: number
  error: number
  converged: boolean
  features: RefinementFeature[]
  annotated_pdf_url: string
}

export interface VisionJobResponse {
  job_id: string
  status: string
}
