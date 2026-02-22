export type CuttingMode = 'low' | 'mid' | 'high'

export interface Operation {
  id: number
  part_id: number
  seq: number
  name: string
  type: string
  icon: string
  work_center_id: number | null
  cutting_mode: CuttingMode
  setup_time_min: number
  operation_time_min: number
  setup_time_locked: boolean
  operation_time_locked: boolean
  ai_estimation_id: number | null
  manning_coefficient: number
  machine_utilization_coefficient: number
  is_coop: boolean
  coop_type: string | null
  coop_price: number
  coop_min_price: number
  coop_days: number
  version: number
  created_at: string
  updated_at: string
}

export interface OperationCreate {
  part_id: number
  seq?: number
  name?: string
  type?: string
  icon?: string
  work_center_id?: number
  cutting_mode?: CuttingMode
  setup_time_min?: number
  operation_time_min?: number
  manning_coefficient?: number
  machine_utilization_coefficient?: number
  is_coop?: boolean
  coop_type?: string
  coop_price?: number
  coop_min_price?: number
  coop_days?: number
}

export interface OperationUpdate {
  seq?: number
  name?: string
  type?: string
  icon?: string
  work_center_id?: number
  cutting_mode?: CuttingMode
  setup_time_min?: number
  operation_time_min?: number
  setup_time_locked?: boolean
  operation_time_locked?: boolean
  manning_coefficient?: number
  machine_utilization_coefficient?: number
  is_coop?: boolean
  coop_type?: string
  coop_price?: number
  coop_min_price?: number
  coop_days?: number
  version: number
}
