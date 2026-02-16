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
  planned_time_min: number | null
  actual_time_min: number | null
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
  actual_time_min?: number | null
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
  actual_time_min?: number | null
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
