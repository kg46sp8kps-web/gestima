/**
 * FT Debug API Client
 *
 * API endpoints for fine-tuning debug data export and inference.
 */

import { apiClient } from './client'

export interface FtPartOperation {
  category: string
  machine: string
  operation_time_min: number
  setup_time_min: number
  manning_pct: number
  num_operations: number
  n_vp: number
  planned_time_min: number | null
  norm_ratio: number | null
  cv: number | null
  manning_cv: number | null
}

export interface FtPartSummary {
  part_id: number
  article_number: string
  name: string | null
  file_id: number | null
  vp_count: number
  material_norm: string | null
  stock_shape: string | null
  operations: FtPartOperation[]
  max_cv: number | null
  total_production_time: number
  total_planned_time: number | null
  norm_ratio: number | null
  skip_reason: string | null
  is_eligible: boolean
}

export interface FtDebugPartsResponse {
  parts: FtPartSummary[]
  total: number
  eligible: number
  skipped: number
}

export interface FtInferenceComparison {
  category: string
  ai_time: number
  gt_time: number
  delta: number
  ai_setup: number
  gt_setup: number
}

export interface FtInferenceResult {
  material_gt: string | null
  material_ai: string | null
  material_match: boolean
  comparisons: FtInferenceComparison[]
  mape: number | null
  tokens_used: number
  cost_estimate: number
}

export async function getFtDebugParts(minVp: number): Promise<FtDebugPartsResponse> {
  const { data } = await apiClient.get<FtDebugPartsResponse>('/ft/debug/parts', {
    params: { min_vp: minVp },
  })
  return data
}

export async function exportFtDebug(partIds: number[]): Promise<Blob> {
  const { data } = await apiClient.post<Blob>(
    '/ft/debug/export',
    { part_ids: partIds },
    { responseType: 'blob' },
  )
  return data
}

export async function runFtInference(partId: number): Promise<FtInferenceResult> {
  const { data } = await apiClient.post<FtInferenceResult>('/ft/debug/inference', {
    part_id: partId,
  })
  return data
}
