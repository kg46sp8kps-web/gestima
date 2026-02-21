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
  [key: string]: string | number | boolean | null | undefined
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

/**
 * === INFOR JOBS IMPORT TYPES (ADR-045) ===
 * Types for importing Parts, Operations (routing), and ProductionRecords from Infor SLJobs/SLJobRoutes
 */

/**
 * Staged Part row (SLJobs → Part)
 */
export interface StagedPartRow {
  row_index: number
  infor_data: Record<string, unknown>
  mapped_data: {
    article_number: string
    name: string
    drawing_number?: string
    customer_revision?: string
  }
  validation: {
    is_valid: boolean
    is_duplicate: boolean
    errors: string[]
    warnings: string[]
  }
  duplicate_action?: 'skip' | 'update'
}

/**
 * Staged Routing row (SLJobs → Operation)
 */
export interface StagedRoutingRow {
  row_index: number
  infor_data: Record<string, unknown>
  mapped_data: {
    article_number: string
    part_id: number
    seq: number
    name: string
    setup_time_min: number
    sched_time_min: number | null
    operation_time_min: number
    manning_coefficient: number
    infor_wc_code: string | null
    work_center_id: number | null
  }
  validation: {
    is_valid: boolean
    is_duplicate: boolean
    errors: string[]
    warnings: string[]
    wc_warning?: string
  }
}

/**
 * Staged Production row (SLJobRoutes → ProductionRecord)
 */
export interface StagedProductionRow {
  row_index: number
  infor_data: Record<string, unknown>
  mapped_data: {
    article_number: string
    part_id: number | null
    infor_order_number: string
    operation_seq: number
    batch_quantity: number | null
    planned_time_min: number | null
    planned_labor_time_min: number | null
    planned_setup_min: number | null
    actual_time_min: number | null
    actual_labor_time_min: number | null
    actual_setup_min: number | null
    actual_run_machine_min: number | null
    actual_run_labor_min: number | null
    manning_coefficient: number | null
    actual_manning_coefficient: number | null
    infor_wc_code: string
    work_center_id: number | null
  }
  validation: {
    is_valid: boolean
    is_duplicate: boolean
    errors: string[]
    warnings: string[]
    wc_warning?: string
  }
}

/**
 * Staged Job Material row (SLJobmatls → MaterialInput)
 */
export interface StagedJobMaterialRow {
  row_index: number
  infor_data: Record<string, unknown>
  mapped_data: {
    article_number: string
    part_id: number | null
    material_item_code: string
    material_item_id: number | null
    operation_seq: number | null
    operation_id: number | null
    matl_qty: number | null
    unit: string | null
    quantity: number
    stock_shape: string | null
    stock_diameter: number | null
    stock_length: number | null
    stock_width: number | null
    stock_height: number | null
    stock_wall_thickness: number | null
    price_category_id: number | null
    price_category_name: string | null
    seq: number
  }
  validation: {
    is_valid: boolean
    is_duplicate: boolean
    errors: string[]
    warnings: string[]
  }
}

/**
 * Staged Document row (SLDocumentObjects_Exts → FileRecord + FileLink)
 */
export interface StagedDocumentRow {
  row_index: number
  document_name: string
  document_extension: string
  row_pointer: string
  sequence: string
  description: string | null
  matched_article_number: string | null
  matched_part_id: number | null
  matched_part_number: string | null
  is_valid: boolean
  is_duplicate: boolean
  errors: string[]
  warnings: string[]
  duplicate_action: 'skip' | 'update'
}

/**
 * Work Center mapping (Infor WC code → Gestima WC number)
 */
export interface WcMapping {
  [inforCode: string]: string
}

/**
 * Generic import execute response
 */
export interface ImportExecuteResponse {
  success: boolean
  created_count: number
  updated_count: number
  skipped_count: number
  errors: string[]
}
