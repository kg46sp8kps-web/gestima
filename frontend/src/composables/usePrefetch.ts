/**
 * usePrefetch — Background data prefetch after login
 *
 * Fire-and-forget: call prefetchAll() after successful login.
 * Each store checks its own loaded/referenceDataLoaded flag — no double-fetches.
 */

import { usePartsStore } from '@/stores/parts'
import { useQuotesStore } from '@/stores/quotes'
import { usePartnersStore } from '@/stores/partners'
import { useFilesStore } from '@/stores/files'
import { useMaterialsStore } from '@/stores/materials'

export function usePrefetch() {
  /**
   * Prefetch all major data sets in parallel (background, fire-and-forget).
   * Errors are silently ignored — the individual modules will retry on open.
   */
  async function prefetchAll(): Promise<void> {
    const partsStore = usePartsStore()
    const quotesStore = useQuotesStore()
    const partnersStore = usePartnersStore()
    const filesStore = useFilesStore()
    const materialsStore = useMaterialsStore()

    await Promise.allSettled([
      partsStore.hasParts ? Promise.resolve() : partsStore.fetchParts(),
      quotesStore.loaded ? Promise.resolve() : quotesStore.fetchQuotes(),
      partnersStore.loaded ? Promise.resolve() : partnersStore.fetchPartners(),
      filesStore.loaded ? Promise.resolve() : filesStore.fetchFiles(),
      materialsStore.loadReferenceData(),   // price categories + groups, built-in guard
      materialsStore.loadMaterialItems(),   // material items catalog, built-in guard
    ])
  }

  return { prefetchAll }
}
