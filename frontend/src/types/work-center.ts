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
  min_workpiece_diameter: number | null
  axes: number | null
  max_bar_diameter: number | null
  max_cut_diameter: number | null
  bar_feed_max_length: number | null
  max_milling_tools: number | null
  has_bar_feeder: boolean
  has_sub_spindle: boolean
  has_milling: boolean
  suitable_for_series: boolean
  suitable_for_single: boolean
  setup_base_min: number
  setup_per_tool_min: number
  is_active: boolean
  priority: number
  notes: string | null
  last_rate_changed_at: string | null
  batches_recalculated_at: string | null
  needs_batch_recalculation: boolean
  version: number
  created_at: string
  updated_at: string
}

export interface WorkCenterCreate {
  name: string
  work_center_type: string
  subtype?: string | null
  hourly_rate_amortization?: number | null
  hourly_rate_labor?: number | null
  hourly_rate_tools?: number | null
  hourly_rate_overhead?: number | null
  max_workpiece_diameter?: number | null
  max_workpiece_length?: number | null
  min_workpiece_diameter?: number | null
  axes?: number | null
  max_bar_diameter?: number | null
  max_cut_diameter?: number | null
  bar_feed_max_length?: number | null
  max_milling_tools?: number | null
  has_bar_feeder?: boolean
  has_sub_spindle?: boolean
  has_milling?: boolean
  suitable_for_series?: boolean
  suitable_for_single?: boolean
  setup_base_min?: number
  setup_per_tool_min?: number
  is_active?: boolean
  priority?: number
  notes?: string | null
}

export interface WorkCenterUpdate {
  name?: string
  work_center_type?: string
  subtype?: string | null
  hourly_rate_amortization?: number | null
  hourly_rate_labor?: number | null
  hourly_rate_tools?: number | null
  hourly_rate_overhead?: number | null
  max_workpiece_diameter?: number | null
  max_workpiece_length?: number | null
  min_workpiece_diameter?: number | null
  axes?: number | null
  max_bar_diameter?: number | null
  max_cut_diameter?: number | null
  bar_feed_max_length?: number | null
  max_milling_tools?: number | null
  has_bar_feeder?: boolean
  has_sub_spindle?: boolean
  has_milling?: boolean
  suitable_for_series?: boolean
  suitable_for_single?: boolean
  setup_base_min?: number
  setup_per_tool_min?: number
  is_active?: boolean
  priority?: number
  notes?: string | null
  version: number
}
