/**
 * useLinkedWindowOpener
 *
 * Ensures linked windows always open in the same linking group.
 * If the master window has no group yet, auto-assigns a free color,
 * syncs the master into it, then re-publishes the current context
 * so the new child window receives the selected part immediately.
 */

import { useWindowsStore } from '@/stores/windows'
import { useWindowContextStore } from '@/stores/windowContext'
import type { WindowModule, LinkingGroup } from '@/stores/windows'

interface Options {
  windowId: string | undefined
  linkingGroup: LinkingGroup
  /** Called with the resolved group after assignment — use to re-publish context */
  onGroupAssigned?: (group: LinkingGroup) => void
}

export function useLinkedWindowOpener(options: Options) {
  const windowsStore = useWindowsStore()
  const contextStore = useWindowContextStore()

  function openLinked(module: WindowModule, title: string) {
    if (options.linkingGroup) {
      // Master is already linked — open child in same group with child role
      windowsStore.openWindow(module, title, options.linkingGroup, 'child')
      options.onGroupAssigned?.(options.linkingGroup)
    } else {
      // Master is standalone — auto-assign a free color, promote master, open child
      const group = windowsStore.findAvailableLinkingGroup()
      if (options.windowId) {
        windowsStore.setWindowLinkingGroup(options.windowId, group)
        windowsStore.setWindowRole(options.windowId, 'master')
      }
      windowsStore.openWindow(module, title, group, 'child')
      options.onGroupAssigned?.(group)
    }
  }

  return { openLinked }
}
