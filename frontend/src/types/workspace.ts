/**
 * Workspace Types — Tiling Layout System
 *
 * Replaces the floating window types from stores/windows.ts
 * windowContext.ts imports LinkingGroup from here
 */

/** Color-based context linking between tiles */
export type LinkingGroup = 'red' | 'blue' | 'green' | 'yellow' | null

/** Available workspace types */
export type WorkspaceType =
  | 'part'
  | 'quotes'
  | 'partners'
  | 'admin'
  | 'timevision'
  | 'accounting'
  | 'manufacturing'
  | 'materials'
  | 'files'

/** Layout presets for the Part workspace */
export type LayoutPreset = 'standard' | 'comparison' | 'horizontal' | 'complete'

/** Active tab in Part detail panel */
export type PartDetailTab = 'operations' | 'material' | 'pricing' | 'drawing' | 'production' | 'ai'

/** Saved workspace layout */
export interface SavedWorkspaceView {
  id: string
  name: string
  workspace: WorkspaceType
  layoutPreset: LayoutPreset
  listPanelWidth: number
  favorite: boolean
  createdAt: string
  updatedAt: string
}

/** Available tile module identifiers */
export type TileModuleId =
  | 'operations'
  | 'pricing'
  | 'material'
  | 'drawing'
  | 'production'
  | 'ai'
  | 'parts-list'

/** Module definition for the registry */
export interface TileModuleDefinition {
  id: TileModuleId
  label: string
  icon: string
  component: () => Promise<unknown>
  needsPart: boolean
}

/** State of a single panel in the tiling workspace */
export interface PanelState {
  id: string
  modules: TileModuleId[]
  activeModule: TileModuleId
  partId: number | null
  partNumber: string | null
  articleNumber: string | null
  linkingGroup: LinkingGroup
}

/** Configuration for a layout preset */
export interface PresetConfig {
  panelCount: number
  gridTemplateColumns: string
  gridTemplateRows: string
  panelDefaults: Array<{
    modules: TileModuleId[]
    activeModule: TileModuleId
    linkingGroup: LinkingGroup
    gridArea?: string
  }>
}
