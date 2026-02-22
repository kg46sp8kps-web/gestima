import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useUiStore } from '@/stores/ui'
import * as layoutsApi from '@/api/layouts'
import type { TileNode, LeafNode, SplitNode, ModuleId, ContextGroup, LayoutPreset, DropZone, DragState } from '@/types/workspace'
import type { UserLayout } from '@/types/layout'

let _id = 0
function nid(): string { return 'n' + (++_id) }

function makeLeaf(module: ModuleId, ctx: ContextGroup = 'ca'): LeafNode {
  return { type: 'leaf', id: nid(), module, ctx }
}
function makeSplit(
  direction: 'horizontal' | 'vertical',
  ratio: number,
  a: TileNode,
  b: TileNode,
): SplitNode {
  return { type: 'split', id: nid(), direction, ratio, children: [a, b] }
}

const PRESETS: Record<LayoutPreset, () => TileNode> = {
  std: () => makeSplit('horizontal', 0.22,
    makeLeaf('parts-list', 'ca'),
    makeLeaf('work-detail', 'ca'),
  ),
  cmp: () => makeSplit('horizontal', 0.16,
    makeLeaf('parts-list', 'ca'),
    makeSplit('horizontal', 0.5,
      makeLeaf('work-detail', 'ca'),
      makeSplit('horizontal', 0.5,
        makeLeaf('work-detail', 'cb'),
        makeLeaf('parts-list', 'cb'),
      ),
    ),
  ),
  hor: () => makeSplit('horizontal', 0.22,
    makeLeaf('parts-list', 'ca'),
    makeSplit('vertical', 0.5,
      makeLeaf('work-detail', 'ca'),
      makeLeaf('work-ops', 'ca'),
    ),
  ),
  qd: () => makeSplit('horizontal', 0.18,
    makeLeaf('parts-list', 'ca'),
    makeSplit('horizontal', 0.5,
      makeSplit('vertical', 0.5,
        makeLeaf('work-detail', 'ca'),
        makeLeaf('work-ops', 'ca'),
      ),
      makeSplit('vertical', 0.5,
        makeLeaf('work-pricing', 'ca'),
        makeLeaf('work-drawing', 'ca'),
      ),
    ),
  ),
}

// Tree utilities
function findNode(
  tree: TileNode | null,
  id: string,
): { node: TileNode; parent: SplitNode | null; childIndex: 0 | 1 | null } | null {
  if (!tree) return null
  if (tree.id === id) return { node: tree, parent: null, childIndex: null }
  if (tree.type === 'split') {
    for (let i = 0; i < 2; i++) {
      const r = findNodeInSplit(tree, tree.children[i as 0 | 1], id, i as 0 | 1)
      if (r) return r
    }
  }
  return null
}

function findNodeInSplit(
  parent: SplitNode,
  tree: TileNode,
  id: string,
  childIndex: 0 | 1,
): { node: TileNode; parent: SplitNode | null; childIndex: 0 | 1 | null } | null {
  if (tree.id === id) return { node: tree, parent, childIndex }
  if (tree.type === 'split') {
    for (let i = 0; i < 2; i++) {
      const r = findNodeInSplit(tree, tree.children[i as 0 | 1], id, i as 0 | 1)
      if (r) return r
    }
  }
  return null
}

/** Returns the leaf at the specified absolute edge by always taking first/last child. */
function getEdgeLeaf(tree: TileNode, takeLast: boolean): LeafNode {
  if (tree.type === 'leaf') return tree
  return getEdgeLeaf(tree.children[takeLast ? 1 : 0], takeLast)
}

function removeLeaf(tree: TileNode, leafId: string): TileNode | null {
  if (tree.type === 'leaf') return tree.id === leafId ? null : tree
  const newA = removeLeaf(tree.children[0], leafId)
  const newB = removeLeaf(tree.children[1], leafId)
  if (newA === null) return newB
  if (newB === null) return newA
  return { ...tree, children: [newA, newB] }
}

function replaceNode(tree: TileNode, targetId: string, newNode: TileNode): TileNode {
  if (tree.id === targetId) return newNode
  if (tree.type === 'leaf') return tree
  return {
    ...tree,
    children: [
      replaceNode(tree.children[0], targetId, newNode),
      replaceNode(tree.children[1], targetId, newNode),
    ],
  }
}

function getLeaves(tree: TileNode): LeafNode[] {
  if (tree.type === 'leaf') return [tree]
  return [...getLeaves(tree.children[0]), ...getLeaves(tree.children[1])]
}

function updateRatio(tree: TileNode, splitId: string, ratio: number): TileNode {
  if (tree.type === 'leaf') return tree
  if (tree.id === splitId) return { ...tree, ratio }
  return {
    ...tree,
    children: [
      updateRatio(tree.children[0], splitId, ratio),
      updateRatio(tree.children[1], splitId, ratio),
    ],
  }
}

export const useWorkspaceStore = defineStore('workspace', () => {
  const tree = ref<TileNode>(PRESETS.std())
  const focusedLeafId = ref<string | null>(null)
  const dragState = ref<DragState | null>(null)

  // Layout management
  const savedLayouts = ref<UserLayout[]>([])
  const currentLayoutId = ref<number | null>(null)

  // Non-reactive set: tracks leaf IDs that have been mounted at least once.
  // Used by TilePanel to suppress the pnlIn animation on re-mounts (e.g. after tree restructure).
  const _seenLeafIds = new Set<string>()
  function markLeafSeen(id: string) { _seenLeafIds.add(id) }
  function isLeafSeen(id: string): boolean { return _seenLeafIds.has(id) }

  const leaves = computed(() => getLeaves(tree.value))
  const headerLayouts = computed(() => savedLayouts.value.filter(l => l.show_in_header))

  // ── Layout management actions ──────────────────────────────────────────────

  async function fetchLayouts() {
    const ui = useUiStore()
    try {
      const layouts = await layoutsApi.getAll()
      savedLayouts.value = layouts
      // Load default layout if currentLayoutId not yet set
      if (currentLayoutId.value === null) {
        const def = layouts.find(l => l.is_default) ?? layouts[0]
        if (def) {
          tree.value = def.tree_json
          currentLayoutId.value = def.id
        }
      }
    } catch {
      ui.showError('Nepodařilo se načíst layouty')
    }
  }

  function loadLayout(id: number) {
    const layout = savedLayouts.value.find(l => l.id === id)
    if (!layout) return
    tree.value = layout.tree_json
    currentLayoutId.value = id
    focusedLeafId.value = null
  }

  async function saveCurrentLayout() {
    if (currentLayoutId.value === null) return
    const ui = useUiStore()
    const layout = savedLayouts.value.find(l => l.id === currentLayoutId.value)
    if (!layout) return
    try {
      const updated = await layoutsApi.update(layout.id, {
        tree_json: tree.value,
        version: layout.version,
      })
      const idx = savedLayouts.value.findIndex(l => l.id === updated.id)
      if (idx !== -1) savedLayouts.value[idx] = updated
      ui.showSuccess('Layout uložen')
    } catch {
      ui.showError('Nepodařilo se uložit layout')
    }
  }

  async function createFromCurrent(name: string) {
    const ui = useUiStore()
    try {
      const created = await layoutsApi.create({ name, tree_json: tree.value })
      savedLayouts.value.push(created)
      currentLayoutId.value = created.id
      ui.showSuccess(`Layout "${name}" vytvořen`)
    } catch {
      ui.showError('Nepodařilo se vytvořit layout')
    }
  }

  async function createBlankLayout(name: string) {
    const ui = useUiStore()
    const blankTree: TileNode = makeLeaf('parts-list', 'ca')
    try {
      const created = await layoutsApi.create({ name, tree_json: blankTree })
      savedLayouts.value.push(created)
      ui.showSuccess(`Layout "${name}" vytvořen`)
    } catch {
      ui.showError('Nepodařilo se vytvořit layout')
    }
  }

  async function deleteLayout(id: number) {
    const ui = useUiStore()
    try {
      await layoutsApi.remove(id)
      savedLayouts.value = savedLayouts.value.filter(l => l.id !== id)
      if (currentLayoutId.value === id) currentLayoutId.value = null
      ui.showSuccess('Layout smazán')
    } catch {
      ui.showError('Nepodařilo se smazat layout')
    }
  }

  async function setDefaultLayout(id: number) {
    const ui = useUiStore()
    const layout = savedLayouts.value.find(l => l.id === id)
    if (!layout) return
    try {
      const updated = await layoutsApi.update(id, { is_default: true, version: layout.version })
      // Clear defaults on others, apply full server response to updated layout
      savedLayouts.value = savedLayouts.value.map(l =>
        l.id === id ? updated : { ...l, is_default: false },
      ) as typeof savedLayouts.value
    } catch {
      ui.showError('Nepodařilo se nastavit výchozí layout')
    }
  }

  async function toggleHeaderVisibility(id: number) {
    const ui = useUiStore()
    const layout = savedLayouts.value.find(l => l.id === id)
    if (!layout) return
    try {
      const updated = await layoutsApi.update(id, {
        show_in_header: !layout.show_in_header,
        version: layout.version,
      })
      const idx = savedLayouts.value.findIndex(l => l.id === id)
      if (idx !== -1) savedLayouts.value[idx] = updated
    } catch {
      ui.showError('Nepodařilo se změnit viditelnost layoutu')
    }
  }

  // ── Tree manipulation ──────────────────────────────────────────────────────

  function focusLeaf(id: string) {
    focusedLeafId.value = id
  }

  function closeLeaf(leafId: string) {
    const newTree = removeLeaf(tree.value, leafId)
    if (!newTree) {
      // Last panel — can't close
      return
    }
    tree.value = newTree
    if (focusedLeafId.value === leafId) {
      const remaining = getLeaves(newTree)
      focusedLeafId.value = remaining[0]?.id ?? null
    }
  }

  function changeModule(leafId: string, moduleId: ModuleId) {
    const result = findNode(tree.value, leafId)
    if (!result || result.node.type !== 'leaf') return
    tree.value = replaceNode(tree.value, leafId, { ...result.node, module: moduleId })
  }

  /** Split a leaf panel by dropping a module into a drop zone */
  function splitLeaf(
    targetLeafId: string,
    newModule: ModuleId,
    zone: DropZone,
    ctx: ContextGroup = 'ca',
  ) {
    const result = findNode(tree.value, targetLeafId)
    if (!result || result.node.type !== 'leaf') return

    const target = result.node

    if (zone === 'center') {
      // Replace module in same leaf
      tree.value = replaceNode(tree.value, targetLeafId, { ...target, module: newModule })
      return
    }

    const newLeaf = makeLeaf(newModule, ctx)
    const direction: 'horizontal' | 'vertical' =
      zone === 'left' || zone === 'right' ? 'horizontal' : 'vertical'
    const isFirst = zone === 'left' || zone === 'top'

    const split = makeSplit(
      direction,
      0.5,
      isFirst ? newLeaf : target,
      isFirst ? target : newLeaf,
    )
    tree.value = replaceNode(tree.value, targetLeafId, split)
    focusedLeafId.value = newLeaf.id
  }

  /** Move a panel (drag from one leaf, drop into another) */
  function moveLeaf(dragLeafId: string, targetLeafId: string, zone: DropZone) {
    if (dragLeafId === targetLeafId) return
    const dragResult = findNode(tree.value, dragLeafId)
    const targetResult = findNode(tree.value, targetLeafId)
    if (!dragResult || dragResult.node.type !== 'leaf') return
    if (!targetResult || targetResult.node.type !== 'leaf') return

    const dragLeaf = dragResult.node as LeafNode
    const targetLeaf = targetResult.node as LeafNode

    if (zone === 'center') {
      // Swap modules between the two leaves (positions stay, only modules exchange)
      let t = replaceNode(tree.value, dragLeafId, { ...dragLeaf, module: targetLeaf.module, ctx: targetLeaf.ctx })
      t = replaceNode(t, targetLeafId, { ...targetLeaf, module: dragLeaf.module, ctx: dragLeaf.ctx })
      tree.value = t
      return
    }

    // Edge zones — remove drag leaf, split target
    const treeWithoutDrag = removeLeaf(tree.value, dragLeafId)
    if (!treeWithoutDrag) return
    tree.value = treeWithoutDrag
    splitLeaf(targetLeafId, dragLeaf.module, zone, dragLeaf.ctx)
  }

  /** Add a panel docked to the absolute right or bottom edge of the workspace */
  function dockToEdge(moduleId: ModuleId, zone: 'right' | 'bottom', ctx: ContextGroup = 'ca') {
    const newLeaf = makeLeaf(moduleId, ctx)
    const direction = zone === 'right' ? 'horizontal' : 'vertical'
    const edgeLeaf = getEdgeLeaf(tree.value, true)
    tree.value = replaceNode(tree.value, edgeLeaf.id, makeSplit(direction, 0.5, edgeLeaf, newLeaf))
    focusedLeafId.value = newLeaf.id
  }

  /** Spawn a new module panel at any absolute workspace edge (used by global drop zones for tab spawns) */
  function spawnToEdge(moduleId: ModuleId, zone: 'left' | 'right' | 'top' | 'bottom', ctx: ContextGroup = 'ca') {
    const newLeaf = makeLeaf(moduleId, ctx)
    const direction = zone === 'left' || zone === 'right' ? 'horizontal' : 'vertical'
    const isFirst = zone === 'left' || zone === 'top'
    const edgeLeaf = getEdgeLeaf(tree.value, !isFirst)
    const split = isFirst
      ? makeSplit(direction, 0.4, newLeaf, edgeLeaf)
      : makeSplit(direction, 0.6, edgeLeaf, newLeaf)
    tree.value = replaceNode(tree.value, edgeLeaf.id, split)
    focusedLeafId.value = newLeaf.id
  }

  /** Move an existing leaf to an absolute workspace edge */
  function dockLeafToEdge(leafId: string, zone: 'left' | 'right' | 'top' | 'bottom') {
    const result = findNode(tree.value, leafId)
    if (!result || result.node.type !== 'leaf') return
    const leaf = result.node as LeafNode
    const treeWithout = removeLeaf(tree.value, leafId)
    if (!treeWithout) return // last panel — can't move
    const direction = zone === 'left' || zone === 'right' ? 'horizontal' : 'vertical'
    const isFirst = zone === 'left' || zone === 'top'
    const edgeLeaf = getEdgeLeaf(treeWithout, !isFirst)
    const split = isFirst
      ? makeSplit(direction, 0.4, leaf, edgeLeaf)
      : makeSplit(direction, 0.6, edgeLeaf, leaf)
    tree.value = replaceNode(treeWithout, edgeLeaf.id, split)
    focusedLeafId.value = leaf.id
  }

  function setSplitRatio(splitId: string, ratio: number) {
    tree.value = updateRatio(tree.value, splitId, ratio)
  }

  function startDrag(leafId: string | null, moduleId: ModuleId, sourceCtx?: ContextGroup) {
    dragState.value = { leafId, moduleId, sourceCtx }
  }

  function setLeafCtx(leafId: string, ctx: ContextGroup) {
    const result = findNode(tree.value, leafId)
    if (!result || result.node.type !== 'leaf') return
    tree.value = replaceNode(tree.value, leafId, { ...result.node, ctx })
  }

  function endDrag() {
    dragState.value = null
  }

  return {
    tree,
    focusedLeafId,
    dragState,
    leaves,
    // Layout management
    savedLayouts,
    currentLayoutId,
    headerLayouts,
    fetchLayouts,
    loadLayout,
    saveCurrentLayout,
    createFromCurrent,
    createBlankLayout,
    deleteLayout,
    setDefaultLayout,
    toggleHeaderVisibility,
    // Tree operations
    focusLeaf,
    closeLeaf,
    changeModule,
    splitLeaf,
    dockToEdge,
    spawnToEdge,
    dockLeafToEdge,
    moveLeaf,
    markLeafSeen,
    isLeafSeen,
    setSplitRatio,
    startDrag,
    endDrag,
    setLeafCtx,
  }
})
