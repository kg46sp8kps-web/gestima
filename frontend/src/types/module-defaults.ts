/**
 * Module Defaults Types
 * For persisting window size and layout settings per module type
 */

export interface ModuleDefaults {
  id?: number
  module_type: string
  default_width: number
  default_height: number
  settings: ModuleDefaultsSettings
  created_at?: string
  updated_at?: string
}

export interface ModuleDefaultsSettings {
  splitPositions?: Record<string, number>
  columnWidths?: Record<string, number>
}

export interface ModuleDefaultsCreate {
  module_type: string
  default_width: number
  default_height: number
  settings: ModuleDefaultsSettings
}

export interface ModuleDefaultsUpdate {
  default_width?: number
  default_height?: number
  settings?: ModuleDefaultsSettings
}
