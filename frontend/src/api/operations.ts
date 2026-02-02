/**
 * GESTIMA - Operations API Module
 *
 * API endpoints:
 *   GET    /api/operations/part/{part_id}  - List operations for part
 *   GET    /api/operations/{id}            - Get single operation
 *   POST   /api/operations/                - Create operation
 *   PUT    /api/operations/{id}            - Update operation
 *   DELETE /api/operations/{id}            - Delete operation
 *   POST   /api/operations/{id}/change-mode - Change cutting mode
 *
 * ADR-024: M:N linking endpoints (operation ↔ material)
 *   POST   /api/operations/{id}/link-material/{material_id}   - Link material to operation
 *   DELETE /api/operations/{id}/unlink-material/{material_id} - Unlink material from operation
 */

import { apiClient } from './client'
import type {
  Operation,
  OperationCreate,
  OperationUpdate,
  ChangeModeRequest,
  WorkCenter,
  WorkCenterCreate,
  WorkCenterUpdate
} from '@/types'
import type { MaterialInput } from '@/types/material'

export const operationsApi = {
  /**
   * List all operations for a part
   */
  async listByPart(partId: number): Promise<Operation[]> {
    const { data } = await apiClient.get<Operation[]>(`/operations/part/${partId}`)
    return data
  },

  /**
   * Get single operation by ID
   */
  async get(operationId: number): Promise<Operation> {
    const { data } = await apiClient.get<Operation>(`/operations/${operationId}`)
    return data
  },

  /**
   * Create new operation
   */
  async create(operation: OperationCreate): Promise<Operation> {
    const { data } = await apiClient.post<Operation>('/operations/', operation)
    return data
  },

  /**
   * Update operation (optimistic locking via version)
   */
  async update(operationId: number, operation: OperationUpdate): Promise<Operation> {
    const { data } = await apiClient.put<Operation>(`/operations/${operationId}`, operation)
    return data
  },

  /**
   * Delete operation
   */
  async delete(operationId: number): Promise<void> {
    await apiClient.delete(`/operations/${operationId}`)
  },

  /**
   * Change cutting mode (low/mid/high)
   */
  async changeMode(operationId: number, request: ChangeModeRequest): Promise<Operation> {
    const { data } = await apiClient.post<Operation>(
      `/operations/${operationId}/change-mode`,
      request
    )
    return data
  },

  // ═══════════════════════════════════════════════════════════════
  // M:N Linking (Operation ↔ MaterialInput) - ADR-024
  // ═══════════════════════════════════════════════════════════════

  /**
   * Link material to operation (M:N relationship)
   * @param consumedQuantity Optional: how much of this material is consumed in this operation
   */
  async linkMaterial(
    operationId: number,
    materialId: number,
    consumedQuantity?: number
  ): Promise<void> {
    await apiClient.post(`/operations/${operationId}/link-material/${materialId}`, {
      consumed_quantity: consumedQuantity
    })
  },

  /**
   * Unlink material from operation
   */
  async unlinkMaterial(operationId: number, materialId: number): Promise<void> {
    await apiClient.delete(`/operations/${operationId}/unlink-material/${materialId}`)
  }
}

/**
 * Work Centers API (for operations dropdown)
 */
export const workCentersApi = {
  /**
   * List all work centers
   */
  async list(): Promise<WorkCenter[]> {
    const { data } = await apiClient.get<WorkCenter[]>('/work-centers/')
    return data
  },

  /**
   * List active work centers only
   */
  async listActive(): Promise<WorkCenter[]> {
    const all = await this.list()
    return all.filter(wc => wc.is_active)
  },

  /**
   * Get single work center by number
   */
  async get(workCenterNumber: string): Promise<WorkCenter> {
    const { data } = await apiClient.get<WorkCenter>(`/work-centers/${workCenterNumber}`)
    return data
  },

  /**
   * Create new work center
   */
  async create(workCenter: WorkCenterCreate): Promise<WorkCenter> {
    const { data } = await apiClient.post<WorkCenter>('/work-centers/', workCenter)
    return data
  },

  /**
   * Update work center by number
   */
  async update(workCenterNumber: string, workCenter: WorkCenterUpdate): Promise<WorkCenter> {
    const { data } = await apiClient.put<WorkCenter>(`/work-centers/${workCenterNumber}`, workCenter)
    return data
  },

  /**
   * Delete work center by number
   */
  async delete(workCenterNumber: string): Promise<void> {
    await apiClient.delete(`/work-centers/${workCenterNumber}`)
  }
}
