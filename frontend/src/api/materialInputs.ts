/**
 * MaterialInput API Client
 *
 * ADR-024: MaterialInput refactor (v1.8.0)
 * Endpoints from material_inputs_router.py
 *
 * Features:
 * - CRUD operations for MaterialInput
 * - M:N linking MaterialInput ↔ Operation
 * - Optimistic locking (version field)
 */

import { apiClient } from './client'
import type {
  MaterialInput,
  MaterialInputWithOperations,
  MaterialInputCreate,
  MaterialInputUpdate
} from '@/types/material'

// =============================================================================
// CRUD Operations
// =============================================================================

/**
 * Get all material inputs for a part (ordered by seq)
 */
export async function getMaterialInputs(partId: number): Promise<MaterialInputWithOperations[]> {
  const response = await apiClient.get<MaterialInputWithOperations[]>(
    `/material-inputs/parts/${partId}`
  )
  return response.data
}

/**
 * Get single material input by ID
 */
export async function getMaterialInput(materialId: number): Promise<MaterialInputWithOperations> {
  const response = await apiClient.get<MaterialInputWithOperations>(
    `/material-inputs/${materialId}`
  )
  return response.data
}

/**
 * Create new material input
 */
export async function createMaterialInput(data: MaterialInputCreate): Promise<MaterialInput> {
  const response = await apiClient.post<MaterialInput>('/material-inputs', data)
  return response.data
}

/**
 * Update material input (optimistic locking)
 * @throws 409 Conflict if version mismatch
 */
export async function updateMaterialInput(
  materialId: number,
  data: MaterialInputUpdate
): Promise<MaterialInput> {
  const response = await apiClient.put<MaterialInput>(`/material-inputs/${materialId}`, data)
  return response.data
}

/**
 * Delete material input (soft delete)
 */
export async function deleteMaterialInput(materialId: number): Promise<void> {
  await apiClient.delete(`/material-inputs/${materialId}`)
}

// =============================================================================
// M:N Linking (MaterialInput ↔ Operation)
// =============================================================================

/**
 * Link material input to operation
 * @param consumedQuantity Optional: how much of this material is consumed in this operation
 */
export async function linkMaterialToOperation(
  materialId: number,
  operationId: number,
  consumedQuantity?: number
): Promise<void> {
  await apiClient.post(`/material-inputs/${materialId}/link-operation/${operationId}`, {
    consumed_quantity: consumedQuantity
  })
}

/**
 * Unlink material input from operation
 */
export async function unlinkMaterialFromOperation(
  materialId: number,
  operationId: number
): Promise<void> {
  await apiClient.delete(`/material-inputs/${materialId}/unlink-operation/${operationId}`)
}

/**
 * Get all materials used in an operation
 */
export async function getOperationMaterials(operationId: number): Promise<MaterialInput[]> {
  const response = await apiClient.get<MaterialInput[]>(
    `/material-inputs/operations/${operationId}/materials`
  )
  return response.data
}

// =============================================================================
// Helpers
// =============================================================================

/**
 * Reorder material inputs (update seq)
 */
export async function reorderMaterialInputs(
  materialInputs: Array<{ id: number; seq: number; version: number }>
): Promise<void> {
  // Update seq for each material input sequentially
  for (const { id, seq, version } of materialInputs) {
    await updateMaterialInput(id, { seq, version })
  }
}
