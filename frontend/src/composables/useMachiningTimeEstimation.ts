/**
 * Machining Time Estimation Composable
 *
 * API integration for fetching batch estimation results
 */

import { ref } from 'vue'
import { apiClient } from '@/api/client'
import type { MachiningTimeEstimation, BatchEstimationResults } from '@/types/estimation'

export function useMachiningTimeEstimation() {
  const results = ref<MachiningTimeEstimation[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchBatchResults(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const response = await apiClient.get<MachiningTimeEstimation[]>('/api/machining-time/batch')
      results.value = response.data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load batch results'
      results.value = []
    } finally {
      loading.value = false
    }
  }

  async function fetchSingleEstimation(filename: string): Promise<MachiningTimeEstimation | null> {
    loading.value = true
    error.value = null

    try {
      const response = await apiClient.get<MachiningTimeEstimation>(
        `/api/estimation/${encodeURIComponent(filename)}`
      )
      return response.data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load estimation'
      return null
    } finally {
      loading.value = false
    }
  }

  return {
    results,
    loading,
    error,
    fetchBatchResults,
    fetchSingleEstimation
  }
}
