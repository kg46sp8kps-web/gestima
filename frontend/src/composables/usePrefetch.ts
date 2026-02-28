import { usePartsStore } from '@/stores/parts'
import { useMaterialItemsStore } from '@/stores/materialItems'
import { useWorkspaceStore } from '@/stores/workspace'
import { useWorkCentersStore } from '@/stores/workCenters'
import { usePartnersStore } from '@/stores/partners'
import { useQuotesListStore } from '@/stores/quotesList'
import type { ModuleId } from '@/types/workspace'

// Modules that have data to prefetch — called only if module is in current layout
const MODULE_PREFETCHERS: Partial<Record<ModuleId, () => Promise<void>>> = {
  'work-ops': () => useWorkCentersStore().fetchIfNeeded(),
  'partners': () => usePartnersStore().fetchIfNeeded(),
  'quotes':   () => useQuotesListStore().fetchIfNeeded(),
}

// JS chunk loaders — preloaded to eliminate Suspense fallback spinners
const MODULE_LOADERS: Partial<Record<ModuleId, () => Promise<unknown>>> = {
  'parts-list':     () => import('@/components/tiling/modules/TileCatalog.vue'),
  'work-ops':       () => import('@/components/tiling/modules/TileWorkOps.vue'),
  'work-pricing':   () => import('@/components/tiling/modules/TileWorkPricing.vue'),
  'work-drawing':   () => import('@/components/tiling/modules/TileWorkDrawing.vue'),
  'work-docs':      () => import('@/components/tiling/modules/TileWorkDocs.vue'),
  'partners':       () => import('@/components/tiling/modules/TilePartners.vue'),
  'quotes':         () => import('@/components/tiling/modules/TileQuotes.vue'),
  'orders-overview': () => import('@/components/tiling/modules/TileOrdersOverview.vue'),
  'time-vision':    () => import('@/components/tiling/modules/TileTimeVision.vue'),
  'batch-sets':     () => import('@/components/tiling/modules/TileBatchSets.vue'),
  'production':     () => import('@/components/tiling/modules/TileProduction.vue'),
  'files':          () => import('@/components/tiling/modules/TileFiles.vue'),
  'admin':          () => import('@/components/tiling/modules/TileAdmin.vue'),
  'materials':      () => import('@/components/tiling/modules/TileMaterials.vue'),
}

export function usePrefetch() {
  const parts = usePartsStore()
  const materialItems = useMaterialItemsStore()
  const workspace = useWorkspaceStore()

  /** Returns a Promise that resolves when all data and JS chunks are ready */
  async function prefetchAll(): Promise<void> {
    // 1. Layout first (sequential) — needed to determine which modules are visible
    if (!workspace.savedLayouts.length) await workspace.fetchLayouts()

    const moduleIds = new Set(workspace.leaves.map(l => l.module))
    const tasks: Promise<unknown>[] = []

    // 2. Base data (always prefetched regardless of layout)
    if (!parts.loaded) tasks.push(parts.fetchParts())
    if (!materialItems.loaded) tasks.push(materialItems.fetchItems())

    // 3. Module-specific data — only for modules visible in current layout
    for (const moduleId of moduleIds) {
      const prefetcher = MODULE_PREFETCHERS[moduleId]
      if (prefetcher) tasks.push(prefetcher())
    }

    // 4. JS chunks for visible modules — eliminates Suspense fallback spinners
    for (const moduleId of moduleIds) {
      const loader = MODULE_LOADERS[moduleId]
      if (loader) tasks.push(loader())
    }

    await Promise.all(tasks)
  }

  return { prefetchAll }
}
