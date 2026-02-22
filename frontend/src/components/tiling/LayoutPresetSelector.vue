<script setup lang="ts">
/**
 * LayoutPresetSelector — Layout preset buttons for Part workspace
 * Standard / Comparison / Horizontal / Complete
 * Compact text-only chips design
 */

import { useWorkspaceStore } from '@/stores/workspace'
import type { LayoutPreset } from '@/types/workspace'

const workspaceStore = useWorkspaceStore()

const presets: { key: LayoutPreset; label: string; shortcut: string }[] = [
  { key: 'standard', label: 'Standardní', shortcut: '⌘1' },
  { key: 'comparison', label: 'Porovnání', shortcut: '⌘2' },
  { key: 'horizontal', label: 'Horizontální', shortcut: '⌘3' },
  { key: 'complete', label: 'Kompletní', shortcut: '⌘4' },
]

function selectPreset(preset: LayoutPreset) {
  workspaceStore.setLayoutPreset(preset)
}
</script>

<template>
  <div class="preset-selector" data-testid="layout-preset-selector">
    <button
      v-for="p in presets"
      :key="p.key"
      class="preset-chip"
      :class="{ active: workspaceStore.layoutPreset === p.key }"
      @click="selectPreset(p.key)"
      :data-testid="`preset-${p.key}`"
    >{{ p.label }}</button>
  </div>
</template>

<style scoped>
.preset-selector {
  display: flex;
  gap: 1px;
  flex-shrink: 0;
}

.preset-chip {
  padding: 3px 9px;
  font-family: inherit;
  font-size: var(--fsl);
  font-weight: 500;
  color: var(--t3);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.12s cubic-bezier(0.4, 0, 0.2, 1);
  white-space: nowrap;
}

.preset-chip:hover {
  color: var(--t3);
  background: rgba(255, 255, 255, 0.06);
}

.preset-chip.active {
  color: var(--t1);
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.10);
}
</style>
