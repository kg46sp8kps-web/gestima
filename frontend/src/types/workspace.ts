export type CatalogItemType = 'part' | 'material' | 'vp'

export interface CatalogFocusItem {
  type: CatalogItemType
  number: string  // part_number nebo material_number
}

export type ModuleId =
  | 'parts-list'
  | 'work-ops'
  | 'work-pricing'
  | 'work-drawing'
  | 'work-docs'
  | 'time-vision'
  | 'batch-sets'
  | 'partners'
  | 'quotes'
  | 'orders-overview'
  | 'production'
  | 'files'
  | 'admin'
  | 'materials'
  | 'machine-plan-dnd'
  | 'production-planner'

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
  usesCtx?: boolean       // true = module reads focusedPart(ctx), shows ctx picker
  hasSplitLayout?: boolean // true = shows vertical/horizontal layout toggle in header
}

export const MODULE_REGISTRY: Record<ModuleId, ModuleDefinition> = {
  'parts-list':    { id: 'parts-list',    label: 'Položky',      usesCtx: true, hasSplitLayout: true },
  'work-ops':      { id: 'work-ops',      label: 'Technologie',  isSub: true, usesCtx: true },
  'work-pricing':  { id: 'work-pricing',  label: 'Kalkulace',    isSub: true, usesCtx: true },
  'work-drawing':  { id: 'work-drawing',  label: 'Výkres',       isSub: true, usesCtx: true },
  'work-docs':     { id: 'work-docs',     label: 'Dokumenty',    isSub: true, usesCtx: true },
  'time-vision':   { id: 'time-vision',   label: 'TimeVision',   shortcut: '⌘6' },
  'batch-sets':    { id: 'batch-sets',    label: 'Dávkové sady', shortcut: '⌘7' },
  'partners':      { id: 'partners',      label: 'Partneři',     shortcut: '⌘8' },
  'quotes':        { id: 'quotes',        label: 'Nabídky',      shortcut: '⌘9', hasSplitLayout: true },
  'orders-overview': { id: 'orders-overview', label: 'Přehled zakázek', usesCtx: true },
  'production':    { id: 'production',    label: 'Výroba',       shortcut: '⌘0' },
  'files':         { id: 'files',         label: 'Soubory' },
  'admin':         { id: 'admin',         label: 'Administrace' },
  'materials':     { id: 'materials',     label: 'Polotovary' },
  'machine-plan-dnd': { id: 'machine-plan-dnd', label: 'Plán stroje DnD', usesCtx: true, hasSplitLayout: true },
  'production-planner': { id: 'production-planner', label: 'Plánovač výroby' },
}

export type LayoutPreset = 'std' | 'cmp' | 'hor' | 'qd'

export type DropZone = 'top' | 'bottom' | 'left' | 'right' | 'center'

export interface DragState {
  leafId: string | null  // null = tab spawn (new leaf), string = existing leaf move
  moduleId: ModuleId
  sourceCtx?: ContextGroup  // ctx of the panel that initiated the drag
}
