/**
 * Window Context Store - Cross-window context linking by color groups
 * Enables multiple parallel work contexts (e.g., red = Part A, blue = Part B)
 *
 * IMPORTANT: Each color has its own separate ref to prevent cross-triggering of watchers
 */

import { defineStore } from 'pinia'
import { ref, type Ref } from 'vue'
import type { LinkingGroup } from './windows'

export interface PartContext {
  partId: number | null
  partNumber: string | null
  articleNumber: string | null
}

export const useWindowContextStore = defineStore('windowContext', () => {
  // State - separate refs for each color group to prevent cross-triggering
  const redContext = ref<PartContext>({ partId: null, partNumber: null, articleNumber: null })
  const blueContext = ref<PartContext>({ partId: null, partNumber: null, articleNumber: null })
  const greenContext = ref<PartContext>({ partId: null, partNumber: null, articleNumber: null })
  const yellowContext = ref<PartContext>({ partId: null, partNumber: null, articleNumber: null })

  // Get the ref for a specific color group
  function getContextRef(group: LinkingGroup): Ref<PartContext> {
    switch (group) {
      case 'red': return redContext
      case 'blue': return blueContext
      case 'green': return greenContext
      case 'yellow': return yellowContext
      default: return ref({ partId: null, partNumber: null, articleNumber: null })
    }
  }

  // Actions
  function setContext(group: LinkingGroup, partId: number, partNumber: string, articleNumber?: string | null) {
    if (!group) return // Unlinked windows don't update context

    const contextRef = getContextRef(group)
    contextRef.value.partId = partId
    contextRef.value.partNumber = partNumber
    contextRef.value.articleNumber = articleNumber ?? null
  }

  function clearContext(group: LinkingGroup) {
    if (!group) return

    const contextRef = getContextRef(group)
    contextRef.value.partId = null
    contextRef.value.partNumber = null
    contextRef.value.articleNumber = null
  }

  function getContext(group: LinkingGroup): PartContext {
    if (!group) return { partId: null, partNumber: null, articleNumber: null }

    const contextRef = getContextRef(group)
    return contextRef.value
  }

  return {
    // Export individual refs for fine-grained reactivity
    redContext,
    blueContext,
    greenContext,
    yellowContext,
    // Export helper function
    getContextRef,
    // Actions
    setContext,
    clearContext,
    getContext
  }
})
