export interface CuttingConditionCell {
  id: number
  Vc: number | null
  f: number | null
  Ap: number | null
  notes: string | null
  version: number
}

export interface CuttingConditionUpdate {
  Vc?: number | null
  f?: number | null
  Ap?: number | null
  notes?: string | null
  version: number
}

export interface CuttingConditionOperation {
  operation_type: string
  operation: string
  label: string
  fields: string[]
}

export interface CuttingConditionPivotResponse {
  mode: string
  materials: string[]
  material_names: Record<string, string>
  operations: CuttingConditionOperation[]
  cells: Record<string, Record<string, CuttingConditionCell>>
}
