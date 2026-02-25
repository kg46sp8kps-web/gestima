export type CatalogItemType = 'part' | 'material'

export interface CatalogFocusItem {
  type: CatalogItemType
  number: string  // part_number nebo material_number
}

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
  | 'files'
  | 'admin'
  | 'materials'
  | 'work-3d'

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
  usesCtx?: boolean  // true = module reads focusedPart(ctx), shows ctx picker
}

export const MODULE_REGISTRY: Record<ModuleId, ModuleDefinition> = {
  'parts-list':    { id: 'parts-list',    label: 'Položky',      usesCtx: true },
  'work-detail':   { id: 'work-detail',   label: 'Detail položky', usesCtx: true },
  'work-ops':      { id: 'work-ops',      label: 'Operace',      isSub: true, usesCtx: true },
  'work-pricing':  { id: 'work-pricing',  label: 'Kalkulace',    isSub: true, usesCtx: true },
  'work-drawing':  { id: 'work-drawing',  label: 'Výkres',       isSub: true, usesCtx: true },
  'work-materials':{ id: 'work-materials',label: 'Materiály',    isSub: true, usesCtx: true },
  'time-vision':   { id: 'time-vision',   label: 'TimeVision',   shortcut: '⌘6', usesCtx: true },
  'batch-sets':    { id: 'batch-sets',    label: 'Dávkové sady', shortcut: '⌘7' },
  'partners':      { id: 'partners',      label: 'Partneři',     shortcut: '⌘8' },
  'quotes':        { id: 'quotes',        label: 'Nabídky',      shortcut: '⌘9' },
  'production':    { id: 'production',    label: 'Výroba',       shortcut: '⌘0' },
  'files':         { id: 'files',         label: 'Soubory' },
  'admin':         { id: 'admin',         label: 'Administrace' },
  'materials':     { id: 'materials',     label: 'Polotovary' },
  'work-3d':       { id: 'work-3d',       label: '3D Model',     isSub: true, usesCtx: true },
}

export type LayoutPreset = 'std' | 'cmp' | 'hor' | 'qd'

export type DropZone = 'top' | 'bottom' | 'left' | 'right' | 'center'

export interface DragState {
  leafId: string | null  // null = tab spawn (new leaf), string = existing leaf move
  moduleId: ModuleId
  sourceCtx?: ContextGroup  // ctx of the panel that initiated the drag
}
