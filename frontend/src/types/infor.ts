/**
 * GESTIMA - Infor Integration Types
 *
 * Type definitions for Infor CloudSuite Industrial import functionality.
 */

import type { StockShape } from './material'

/**
 * Surface treatment codes from Infor Item suffix
 * Format: {W.Nr}-{SHAPE}{dimensions}-{SURFACE}
 * Example: 1.0503-HR016x016-T
 */
export const SURFACE_TREATMENT_LABELS: Record<string, string> = {
  'T': 'Tažená (cold drawn)',
  'V': 'Válená (hot rolled)',
  'P': 'Lisovaná (pressed)',
  'O': 'Loupaná (peeled)',
  'F': 'Frézovaná (milled)',
  'K': 'Kovaná (forged)',
  'L': 'Litá (cast)',
  'H': 'Kalená (hardened)',
  'N': 'Normalizovaná (normalized)',
  'Z': 'Pozinkovaná (galvanized)',
  'S': 'Svařovaná (welded)',
  'Sv': 'Svařovaná (welded)',
  'Vs': 'Válcovaná za studena (cold rolled)',
  'B': 'Broušená (ground)',
  'BLOK': 'Blok (block)',
  'EP': 'Elox Plus (anodized)',
}

/**
 * Get surface treatment label for display
 * @param code Surface treatment code (e.g., "T")
 * @returns Label with description (e.g., "T - Tažená (cold drawn)") or just code if unknown
 */
export function getSurfaceTreatmentLabel(code: string | null | undefined): string {
  if (!code) return ''
  const label = SURFACE_TREATMENT_LABELS[code]
  return label ? `${code} - ${label}` : code
}

/**
 * Generic Infor IDO row (dynamic fields based on selected columns)
 */
export interface InforRow {
  [key: string]: any
}

/**
 * Validation result for a single staged row
 */
export interface ValidationResult {
  is_valid: boolean
  is_duplicate: boolean
  errors: string[]
  warnings: string[]
  needs_manual_group: boolean
  needs_manual_shape: boolean
}

/**
 * Staged material row for import preview
 */
export interface StagedMaterialRow {
  row_index: number
  infor_data: InforRow
  mapped_data: {
    code: string
    name: string
    shape: StockShape | null
    diameter?: number | null
    width?: number | null
    thickness?: number | null
    wall_thickness?: number | null
    weight_per_meter?: number | null
    standard_length?: number | null
    norms?: string | null
    supplier_code?: string | null
    supplier?: string | null
    stock_available?: number | null
    surface_treatment?: string | null
    material_group_id: number | null
    price_category_id: number | null
  }
  validation: ValidationResult
  duplicate_action?: 'skip' | 'update'  // User's choice for duplicates
}

/**
 * Request: Preview material import (validation only, no DB changes)
 */
export interface MaterialImportPreviewRequest {
  ido_name: string
  rows: InforRow[]
}

/**
 * Response: Preview material import with validation results
 */
export interface MaterialImportPreviewResponse {
  valid_count: number
  error_count: number
  duplicate_count: number
  rows: StagedMaterialRow[]
}

/**
 * Request: Execute material import (create/update records)
 */
export interface MaterialImportExecuteRequest {
  rows: Array<{
    code: string
    name: string
    shape: string
    diameter?: number | null
    width?: number | null
    thickness?: number | null
    wall_thickness?: number | null
    weight_per_meter?: number | null
    standard_length?: number | null
    norms?: string | null
    supplier_code?: string | null
    supplier?: string | null
    stock_available?: number | null
    material_group_id: number
    price_category_id: number
    duplicate_action?: 'skip' | 'update'
  }>
}

/**
 * Response: Execute material import with counts
 */
export interface MaterialImportExecuteResponse {
  success: boolean
  created_count: number
  updated_count: number
  skipped_count: number
  errors: string[]
}
