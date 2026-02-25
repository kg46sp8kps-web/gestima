import { usePartsStore } from '@/stores/parts'
import { useMaterialItemsStore } from '@/stores/materialItems'

export function usePrefetch() {
  const parts = usePartsStore()
  const materialItems = useMaterialItemsStore()

  /** Returns a Promise that resolves when all data is loaded */
  function prefetchAll(): Promise<void> {
    const tasks: Promise<unknown>[] = []
    if (!parts.loaded) tasks.push(parts.fetchParts())
    if (!materialItems.loaded) tasks.push(materialItems.fetchItems())
    return Promise.all(tasks).then(() => undefined)
  }

  return { prefetchAll }
}
