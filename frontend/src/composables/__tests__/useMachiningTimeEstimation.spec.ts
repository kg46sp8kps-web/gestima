import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useMachiningTimeEstimation } from '../useMachiningTimeEstimation'
import type { BatchEstimationResults } from '@/types/estimation'

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn()
  }
}))

describe('useMachiningTimeEstimation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should initialize with empty state', () => {
    const { results, loading, error } = useMachiningTimeEstimation()

    expect(results.value).toEqual([])
    expect(loading.value).toBe(false)
    expect(error.value).toBeNull()
  })

  it('should fetch batch results successfully', async () => {
    const { apiClient } = await import('@/api/client')
    const mockData: BatchEstimationResults = {
      results: [
        {
          filename: 'test.stp',
          part_type: 'ROT',
          roughing_time_min: 10,
          finishing_time_min: 2,
          setup_time_min: 5,
          total_time_min: 17,
          breakdown: {
            material: '1.4301',
            stock_volume_mm3: 100000,
            part_volume_mm3: 80000,
            material_to_remove_mm3: 20000,
            material_removal_percent: 20,
            surface_area_mm2: 10000,
            machining_strategy: {
              rough: { mrr_mm3_min: 2000, cutting_time_min: 10 },
              finish: { mrr_mm3_min: 500, cutting_time_min: 2 }
            },
            critical_constraints: [],
            constraint_multiplier: 1.0,
            pure_machining_time_min: 12
          }
        }
      ],
      total_files: 1,
      avg_time_min: 17,
      total_volume_removed_cm3: 20
    }

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockData })

    const { results, loading, fetchBatchResults } = useMachiningTimeEstimation()

    expect(loading.value).toBe(false)

    await fetchBatchResults()

    expect(loading.value).toBe(false)
    expect(results.value).toHaveLength(1)
    expect(results.value[0]?.filename).toBe('test.stp')
    expect(apiClient.get).toHaveBeenCalledWith('/api/estimation/batch')
  })

  it('should handle fetch errors gracefully', async () => {
    const { apiClient } = await import('@/api/client')
    vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'))

    const { results, error, fetchBatchResults } = useMachiningTimeEstimation()

    await fetchBatchResults()

    expect(error.value).toBe('Network error')
    expect(results.value).toEqual([])
  })
})
