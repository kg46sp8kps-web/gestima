/**
 * GESTIMA - Production Record TypeScript Types
 *
 * Based on app/models/production_record.py
 */

export interface ProductionRecord {
  id: number
  part_id: number
  infor_order_number: string | null
  batch_quantity: number | null
  operation_seq: number | null
  work_center_id: number | null
  work_center_name: string | null
  work_center_type: string | null
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
  production_date: string | null
  source: 'infor' | 'manual'
  notes: string | null
  version: number
  created_at: string
  updated_at: string
}

export interface ProductionRecordCreate {
  part_id: number
  infor_order_number?: string | null
  batch_quantity?: number | null
  operation_seq?: number | null
  work_center_id?: number | null
  planned_time_min?: number | null
  planned_labor_time_min?: number | null
  planned_setup_min?: number | null
  actual_time_min?: number | null
  actual_labor_time_min?: number | null
  actual_setup_min?: number | null
  actual_run_machine_min?: number | null
  actual_run_labor_min?: number | null
  manning_coefficient?: number | null
  actual_manning_coefficient?: number | null
  production_date?: string | null
  source?: string
  notes?: string | null
}

export interface ProductionRecordUpdate {
  infor_order_number?: string | null
  batch_quantity?: number | null
  operation_seq?: number | null
  work_center_id?: number | null
  planned_time_min?: number | null
  planned_labor_time_min?: number | null
  planned_setup_min?: number | null
  actual_time_min?: number | null
  actual_labor_time_min?: number | null
  actual_setup_min?: number | null
  actual_run_machine_min?: number | null
  actual_run_labor_min?: number | null
  manning_coefficient?: number | null
  actual_manning_coefficient?: number | null
  production_date?: string | null
  source?: string
  notes?: string | null
  version: number
}

export interface ProductionSummary {
  total_records: number
  total_batches: number
  avg_actual_time_min: number | null
  min_actual_time_min: number | null
  max_actual_time_min: number | null
  total_pieces_produced: number
}
