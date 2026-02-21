/**
 * Module Defaults API Client
 * Handles saving and loading window size and layout defaults
 * ADR-031: Module Defaults Persistence System
 */

import { apiClient } from './client'
import type { ModuleDefaults, ModuleDefaultsCreate } from '@/types/module-defaults'

/**
 * Get module defaults by module type
 * @param moduleType - Window module type (e.g., 'part-main', 'quotes-list')
 * @returns Module defaults or null if not found (404)
 */
export async function getModuleDefaults(
  moduleType: string
): Promise<ModuleDefaults | null> {
  try {
    const response = await apiClient.get<ModuleDefaults>(`/module-defaults/${moduleType}`)
    return response.data
  } catch (error: unknown) {
    // 404 = No defaults found (expected)
    const err = error as { response?: { status: number } }
    if (err.response?.status === 404) {
      return null
    }
    throw error
  }
}

/**
 * Save or update module defaults (UPSERT)
 * @param data - Module defaults to save
 * @returns Saved module defaults
 */
export async function saveModuleDefaults(
  data: ModuleDefaultsCreate
): Promise<ModuleDefaults> {
  const response = await apiClient.post<ModuleDefaults>('/module-defaults', data)
  return response.data
}
