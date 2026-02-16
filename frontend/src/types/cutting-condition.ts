/**
 * Cutting Conditions types for pivot table
 */

export interface PivotOperation {
  operation_type: string
  operation: string
  label: string
  fields: string[]  // ["Vc", "f", "Ap"] or ["Vc", "fz", "Ap"] or ["Vc"]
}

export interface PivotCell {
  id: number
  Vc: number | null
  f: number | null
  fz: number | null
  Ap: number | null
  notes: string | null
  version: number
}

export interface PivotResponse {
  mode: string
  materials: string[]
  material_names: Record<string, string>
  operations: PivotOperation[]
  cells: Record<string, Record<string, PivotCell>>
}

export interface CuttingConditionUpdate {
  Vc?: number | null
  f?: number | null
  Ap?: number | null
  notes?: string | null
  version: number
}

export interface CuttingConditionResponse {
  id: number
  material_group: string
  material_name: string | null
  operation_type: string
  operation: string
  mode: string
  Vc: number
  f: number
  Ap: number
  notes: string | null
  version: number
  created_at: string
  updated_at: string
}
