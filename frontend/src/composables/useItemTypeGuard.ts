import { useCatalogStore } from '@/stores/catalog'
import type { ContextGroup, CatalogItemType } from '@/types/workspace'

export function useItemTypeGuard(supported: CatalogItemType[]) {
  const catalog = useCatalogStore()

  function isSupported(ctx: ContextGroup): boolean {
    const item = catalog.getFocusedItem(ctx)
    if (!item) return true  // nic fokusnuté → zobraz normální empty state
    return supported.includes(item.type)
  }

  function focusedTypeName(ctx: ContextGroup): string {
    const item = catalog.getFocusedItem(ctx)
    if (!item) return ''
    return item.type === 'material' ? 'Polotovar' : 'Díl'
  }

  return { isSupported, focusedTypeName }
}
