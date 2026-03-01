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
