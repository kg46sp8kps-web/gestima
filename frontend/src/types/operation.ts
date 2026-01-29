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

// Work center (simplified for operations dropdown)
export interface WorkCenter {
  id: number;
  number: string;
  name: string;
  type: string;
  hourly_rate: number;
  is_active: boolean;
}

// Operation type mapping (for icons and labels)
export const OPERATION_TYPE_MAP: Record<string, { type: OperationType; icon: string; label: string }> = {
  lathe: { type: 'turning', icon: '🔄', label: 'Soustružení' },
  mill: { type: 'milling', icon: '⚙️', label: 'Frézování' },
  saw: { type: 'cutting', icon: '✂️', label: 'Řezání' },
  grinder: { type: 'grinding', icon: '💎', label: 'Broušení' },
  drill: { type: 'drilling', icon: '🔩', label: 'Vrtání' },
  generic: { type: 'generic', icon: '🔧', label: 'Operace' }
};

// Cutting mode labels
export const CUTTING_MODE_LABELS: Record<CuttingMode, string> = {
  low: 'Dokončovací',
  mid: 'Střední',
  high: 'Hrubovací'
};
