export type ModuleId =
  | 'parts-list'
  | 'work-detail'
  | 'work-ops'
  | 'work-pricing'
  | 'work-drawing'
  | 'work-materials'
  | 'time-vision'
  | 'batch-sets'
  | 'partners'
  | 'quotes'
  | 'production'
  | 'accounting'
  | 'files'
  | 'admin'

export type ContextGroup = 'ca' | 'cb' | 'cc' | 'cd'

export interface LeafNode {
  type: 'leaf'
  id: string
  module: ModuleId
  ctx: ContextGroup
}

export interface SplitNode {
  type: 'split'
  id: string
  direction: 'horizontal' | 'vertical'
  ratio: number  // 0–1, fraction of first child
  children: [TileNode, TileNode]
}

export type TileNode = LeafNode | SplitNode

export interface ModuleDefinition {
  id: ModuleId
  label: string
  shortcut?: string
  isSub?: boolean
}

export const MODULE_REGISTRY: Record<ModuleId, ModuleDefinition> = {
  'parts-list':    { id: 'parts-list',    label: 'Díly' },
  'work-detail':   { id: 'work-detail',   label: 'Detail dílu' },
  'work-ops':      { id: 'work-ops',      label: 'Operace',      isSub: true },
  'work-pricing':  { id: 'work-pricing',  label: 'Kalkulace',    isSub: true },
  'work-drawing':  { id: 'work-drawing',  label: 'Výkres',       isSub: true },
  'work-materials':{ id: 'work-materials',label: 'Materiály',    isSub: true },
  'time-vision':   { id: 'time-vision',   label: 'TimeVision',   shortcut: '⌘6' },
  'batch-sets':    { id: 'batch-sets',    label: 'Dávkové sady', shortcut: '⌘7' },
  'partners':      { id: 'partners',      label: 'Partneři',     shortcut: '⌘8' },
  'quotes':        { id: 'quotes',        label: 'Nabídky',      shortcut: '⌘9' },
  'production':    { id: 'production',    label: 'Výroba',       shortcut: '⌘0' },
  'accounting':    { id: 'accounting',    label: 'Účetnictví' },
  'files':         { id: 'files',         label: 'Soubory' },
  'admin':         { id: 'admin',         label: 'Administrace' },
}

export type LayoutPreset = 'std' | 'cmp' | 'hor' | 'qd'

export type DropZone = 'top' | 'bottom' | 'left' | 'right' | 'center'

export interface DragState {
  leafId: string | null  // null = tab spawn (new leaf), string = existing leaf move
  moduleId: ModuleId
  sourceCtx?: ContextGroup  // ctx of the panel that initiated the drag
}
