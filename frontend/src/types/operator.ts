/** Operator Terminal types */

export interface ActiveJob {
  job: string
  suffix: string
  oper_num: string
  wc: string | null
  item: string | null
  trans_type: string
  started_at: string
  description: string | null
  der_job_item: string | null
  job_stat: string | null
  qty_released: number | null
  qty_complete: number | null
  op_datum_st: string | null
  op_datum_sp: string | null
}

export interface OperatorStats {
  today_hours: number
  today_pieces: number
  today_scrap: number
  week_hours: number
  week_pieces: number
  today_norm_pct: number | null
  week_norm_pct: number | null
  month_norm_pct: number | null
}

export interface OperatorWorkcenter {
  wc: string
  oper_count: number
}

export type OperatorAlertSeverity = 'error' | 'warning' | 'info'

export interface TransactionAlert {
  id: number
  job: string
  suffix: string
  oper_num: string
  wc: string | null
  trans_type: string
  status: string
  severity: OperatorAlertSeverity
  error_msg: string | null
  created_at: string | null
  updated_at: string | null
  started_at: string | null
  finished_at: string | null
  retry_allowed: boolean
  blocks_running: boolean
}

export type NormPeriod = 'day' | 'week' | 'month'

export interface NormSummary {
  run_fulfillment_pct: number | null
  setup_fulfillment_pct: number | null
  overall_fulfillment_pct: number | null
  total_actual_run_min: number
  total_planned_run_min: number
  total_actual_setup_min: number
  total_planned_setup_min: number
  total_qty: number
  total_scrap: number
  operation_count: number
}

export interface NormDetailRow {
  trans_date: string | null
  job: string
  suffix: string
  oper_num: string | null
  wc: string | null
  trans_type: string | null
  der_job_item: string | null
  job_description: string | null
  qty_complete: number
  qty_scrapped: number
  actual_run_min: number
  actual_setup_min: number
  planned_min_per_piece: number | null
  planned_setup_min: number | null
  planned_run_min: number | null
  run_fulfillment_pct: number | null
  setup_fulfillment_pct: number | null
  overall_fulfillment_pct: number | null
}
