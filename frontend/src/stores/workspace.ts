/**
 * GESTIMA - Workspace Store (Placeholder)
 *
 * Manages workspace context state.
 * This is a placeholder for the full workspace implementation.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface WorkspaceContext {
  partId: number | null
  partNumber: string | null
}

export const useWorkspaceStore = defineStore('workspace', () => {
  // State
  const context = ref<WorkspaceContext>({
    partId: null,
    partNumber: null
  })

  // Getters
  const hasSelectedPart = computed(() => context.value.partId !== null)

  // Actions
  function setPartContext(partId: number | null, partNumber: string | null = null) {
    context.value.partId = partId
    context.value.partNumber = partNumber
  }

  function clearContext() {
    context.value.partId = null
    context.value.partNumber = null
  }

  return {
    context,
    hasSelectedPart,
    setPartContext,
    clearContext
  }
})
