/**
 * GESTIMA - Operation TypeScript Types
 *
 * Based on app/models/operation.py
 */

// Cutting mode enum
export type CuttingMode = 'low' | 'mid' | 'high';

// Operation type enum (based on work center types)
export type OperationType =
  | 'turning'    // Soustružení
  | 'milling'    // Frézování
  | 'cutting'    // Řezání
  | 'grinding'   // Broušení
  | 'drilling'   // Vrtání
  | 'generic';   // Obecná operace

// Base operation interface
export interface Operation {
  id: number;
  part_id: number;
  seq: number;
  name: string;
  type: OperationType;
  icon: string;
  work_center_id: number | null;
  cutting_mode: CuttingMode;
  setup_time_min: number;
  operation_time_min: number;
  setup_time_locked: boolean;
  operation_time_locked: boolean;
  manning_coefficient: number;
  machine_utilization_coefficient: number;
  is_coop: boolean;
  coop_type: string | null;
  coop_price: number;
  coop_min_price: number;
  coop_days: number;
  version: number;
  created_at: string;
  updated_at: string;
}

// Create operation request
export interface OperationCreate {
  part_id: number;
  seq?: number;
  name?: string;
  type?: OperationType;
  icon?: string;
  work_center_id?: number | null;
  cutting_mode?: CuttingMode;
  setup_time_min?: number;
  operation_time_min?: number;
  is_coop?: boolean;
  coop_type?: string | null;
  coop_price?: number;
  coop_min_price?: number;
  coop_days?: number;
}

// Update operation request
export interface OperationUpdate {
  seq?: number;
  name?: string;
  type?: OperationType;
  icon?: string;
  work_center_id?: number | null;
  cutting_mode?: CuttingMode;
  setup_time_min?: number;
  operation_time_min?: number;
  setup_time_locked?: boolean;
  operation_time_locked?: boolean;
  manning_coefficient?: number;
  machine_utilization_coefficient?: number;
  is_coop?: boolean;
  coop_type?: string | null;
  coop_price?: number;
  coop_min_price?: number;
  coop_days?: number;
  version: number;  // Required for optimistic locking
}

// Change mode request
export interface ChangeModeRequest {
  cutting_mode: CuttingMode;
  version: number;
}

// Work center type enum (matches backend app/models/enums.py)
export type WorkCenterType =
  | 'CNC_LATHE'
  | 'CNC_MILL_3AX'
  | 'CNC_MILL_4AX'
  | 'CNC_MILL_5AX'
  | 'SAW'
  | 'DRILL'
  | 'QUALITY_CONTROL'
  | 'MANUAL_ASSEMBLY'
  | 'EXTERNAL';

// Work center (full definition)
export interface WorkCenter {
  id: number;
  work_center_number: string;
  name: string;
  work_center_type: WorkCenterType;
  subtype?: string | null;

  // Economics (4 separate rates)
  hourly_rate_amortization?: number | null;
  hourly_rate_labor?: number | null;
  hourly_rate_tools?: number | null;
  hourly_rate_overhead?: number | null;

  // Tech specs (optional)
  max_workpiece_diameter?: number | null;
  max_workpiece_length?: number | null;
  min_workpiece_diameter?: number | null;
  axes?: number | null;

  // Bar feeder / Saw specs
  max_bar_diameter?: number | null;
  max_cut_diameter?: number | null;
  bar_feed_max_length?: number | null;

  // Capabilities
  has_bar_feeder: boolean;
  has_sub_spindle: boolean;
  has_milling: boolean;
  max_milling_tools?: number | null;

  // Production suitability
  suitable_for_series: boolean;
  suitable_for_single: boolean;

  // Setup times
  setup_base_min: number;
  setup_per_tool_min: number;

  // Organization
  is_active: boolean;
  priority: number;
  notes?: string | null;

  // Versioning and audit
  version: number;
  created_at: string;
  updated_at: string;

  // Batch recalculation tracking
  last_rate_changed_at?: string | null;
  batches_recalculated_at?: string | null;

  // Computed fields (read-only from backend)
  hourly_rate_setup?: number | null;
  hourly_rate_operation?: number | null;
  hourly_rate_total?: number | null;
  needs_batch_recalculation?: boolean;
}

// Create work center request
export interface WorkCenterCreate {
  name: string;
  work_center_type: WorkCenterType;
  subtype?: string | null;

  hourly_rate_amortization?: number | null;
  hourly_rate_labor?: number | null;
  hourly_rate_tools?: number | null;
  hourly_rate_overhead?: number | null;

  max_workpiece_diameter?: number | null;
  max_workpiece_length?: number | null;
  min_workpiece_diameter?: number | null;
  axes?: number | null;

  max_bar_diameter?: number | null;
  max_cut_diameter?: number | null;
  bar_feed_max_length?: number | null;

  has_bar_feeder?: boolean;
  has_sub_spindle?: boolean;
  has_milling?: boolean;
  max_milling_tools?: number | null;

  suitable_for_series?: boolean;
  suitable_for_single?: boolean;

  setup_base_min?: number;
  setup_per_tool_min?: number;

  is_active?: boolean;
  priority?: number;
  notes?: string | null;

  work_center_number?: string | null;  // Optional - auto-generated if not provided
}

// Update work center request
export interface WorkCenterUpdate {
  name?: string;
  work_center_type?: WorkCenterType;
  subtype?: string | null;

  hourly_rate_amortization?: number | null;
  hourly_rate_labor?: number | null;
  hourly_rate_tools?: number | null;
  hourly_rate_overhead?: number | null;

  max_workpiece_diameter?: number | null;
  max_workpiece_length?: number | null;
  min_workpiece_diameter?: number | null;
  axes?: number | null;

  max_bar_diameter?: number | null;
  max_cut_diameter?: number | null;
  bar_feed_max_length?: number | null;

  has_bar_feeder?: boolean;
  has_sub_spindle?: boolean;
  has_milling?: boolean;
  max_milling_tools?: number | null;

  suitable_for_series?: boolean;
  suitable_for_single?: boolean;

  setup_base_min?: number;
  setup_per_tool_min?: number;

  is_active?: boolean;
  priority?: number;
  notes?: string | null;

  version: number;  // Required for optimistic locking
}

// Operation type mapping (for labels and icons)
export const OPERATION_TYPE_MAP: Record<string, { type: OperationType; icon: string; label: string }> = {
  lathe: { type: 'turning', icon: 'rotate-cw', label: 'Soustružení' },
  mill: { type: 'milling', icon: 'settings', label: 'Frézování' },
  saw: { type: 'cutting', icon: 'scissors', label: 'Řezání' },
  grinder: { type: 'grinding', icon: 'gem', label: 'Broušení' },
  drill: { type: 'drilling', icon: 'wrench', label: 'Vrtání' },
  generic: { type: 'generic', icon: 'wrench', label: 'Operace' }
};

// Cutting mode labels
export const CUTTING_MODE_LABELS: Record<CuttingMode, string> = {
  low: 'Dokončovací',
  mid: 'Střední',
  high: 'Hrubovací'
};
