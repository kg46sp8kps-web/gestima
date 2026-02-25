import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * Generic per-tile split layout mode with localStorage persistence.
 * Session state is keyed by leafId (ephemeral).
 * Default for each module is persisted in localStorage (stable across reloads).
 *
 * Usage:
 *   getMode(leafId, moduleId)  — reads session state, falls back to localStorage default
 *   toggle(leafId, moduleId)   — updates session state + writes new default to localStorage
 */
export const useSplitLayoutStore = defineStore('splitLayout', () => {
  const modes = ref<Record<string, 'vertical' | 'horizontal'>>({})

  function storageKey(moduleId: string) {
    return `gestima.split-layout.${moduleId}`
  }

  function loadDefault(moduleId: string): 'vertical' | 'horizontal' {
    const v = localStorage.getItem(storageKey(moduleId))
    return v === 'horizontal' ? 'horizontal' : 'vertical'
  }

  function getMode(leafId: string, moduleId?: string): 'vertical' | 'horizontal' {
    if (modes.value[leafId] !== undefined) return modes.value[leafId]
    // First access for this leafId — initialize from localStorage default
    const def = moduleId ? loadDefault(moduleId) : 'vertical'
    modes.value = { ...modes.value, [leafId]: def }
    return def
  }

  function toggle(leafId: string, moduleId?: string) {
    const current = getMode(leafId, moduleId)
    const next: 'vertical' | 'horizontal' = current === 'vertical' ? 'horizontal' : 'vertical'
    modes.value = { ...modes.value, [leafId]: next }
    // Persist new default for this module so next tile mount uses it
    if (moduleId) localStorage.setItem(storageKey(moduleId), next)
  }

  function cleanup(leafId: string) {
    const next = { ...modes.value }
    delete next[leafId]
    modes.value = next
  }

  return { getMode, toggle, cleanup }
})
