export interface WorkCenter {
  id: number
  work_center_number: string
  name: string
  work_center_type: string
  subtype: string | null
  hourly_rate_amortization: number | null
  hourly_rate_labor: number | null
  hourly_rate_tools: number | null
  hourly_rate_overhead: number | null
  hourly_rate_setup: number | null
  hourly_rate_operation: number | null
  hourly_rate_total: number | null
  max_workpiece_diameter: number | null
  max_workpiece_length: number | null
  axes: number | null
  has_bar_feeder: boolean
  has_sub_spindle: boolean
  has_milling: boolean
  is_active: boolean
  priority: number
  version: number
}

export interface WorkCenterUpdate {
  name?: string
  work_center_type?: string
  hourly_rate_amortization?: number | null
  hourly_rate_labor?: number | null
  hourly_rate_tools?: number | null
  hourly_rate_overhead?: number | null
  max_workpiece_diameter?: number | null
  axes?: number | null
  is_active?: boolean
  version: number
}
