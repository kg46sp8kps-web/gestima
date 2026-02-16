/**
 * GESTIMA - Technology Builder API
 *
 * POST /api/technology/generate — Generate complete tech plan from AI estimation
 */

import { apiClient } from './client'
import type { Operation } from '@/types/operation'

export interface GenerateTechnologyRequest {
  estimation_id: number
  part_id: number
  material_input_id?: number
  cutting_mode?: string
}

export interface GenerateTechnologyResponse {
  operations: Operation[]
  warnings: string[]
}

/**
 * Generate complete technology plan (OP10 rezani + OP20 strojni + OP100 kontrola)
 */
export async function generateTechnology(
  request: GenerateTechnologyRequest
): Promise<GenerateTechnologyResponse> {
  const { data } = await apiClient.post<GenerateTechnologyResponse>(
    '/technology/generate',
    request
  )
  return data
}
