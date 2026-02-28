/** Production Planner — TypeScript typy */

export type PriorityTier = 'hot' | 'urgent' | 'frozen' | 'normal'

export interface PlannerOperation {
  oper_num: string
  wc: string | null
  status: 'done' | 'in_progress' | 'idle'
  start_date: string | null
  end_date: string | null
  setup_hrs: number | null
  run_hrs: number | null
  pcs_per_hour: number | null
  qty_complete: number | null
  qty_released: number | null
  // Scheduling fields (from backend forward-scheduler)
  sched_start: string | null
  sched_end: string | null
  duration_hrs: number | null
}

export interface PlannerVpRow {
  job: string
  suffix: string
  item: string | null
  description: string | null
  job_stat: string | null
  qty_released: number | null
  qty_complete: number | null
  qty_scrapped: number | null
  vp_due_date: string | null
  priority: number
  is_hot: boolean
  tier: PriorityTier
  ops_done: number
  ops_total: number
  co_num: string | null
  co_due_date: string | null
  customer_name: string | null
  is_delayed: boolean
  delay_days: number | null
  operations: PlannerOperation[]
}

export interface WcLaneOp {
  job: string
  suffix: string
  oper_num: string
  item: string | null
  description: string | null
  status: 'done' | 'in_progress' | 'idle'
  sched_start: string | null
  sched_end: string | null
  duration_hrs: number | null
  setup_hrs: number | null
  pcs_per_hour: number | null
  priority: number
  is_hot: boolean
  co_due_date: string | null
}

export interface WcLane {
  wc: string
  ops: WcLaneOp[]
}

export interface PlannerData {
  vps: PlannerVpRow[]
  wc_lanes: WcLane[]
  time_range: { min_date: string; max_date: string }
}
