<script setup lang="ts">
/**
 * WorkspaceSwitcher — Horizontal tab strip for switching between workspaces
 * Compact text-only chips design
 */

import { useWorkspaceStore } from '@/stores/workspace'
import type { WorkspaceType } from '@/types/workspace'

const workspaceStore = useWorkspaceStore()

const workspaces: { key: WorkspaceType; label: string }[] = [
  { key: 'part', label: 'Díly' },
  { key: 'manufacturing', label: 'Výroba' },
  { key: 'quotes', label: 'Nabídky' },
  { key: 'partners', label: 'Partneři' },
  { key: 'materials', label: 'Materiály' },
  { key: 'files', label: 'Soubory' },
  { key: 'accounting', label: 'Účetnictví' },
  { key: 'timevision', label: 'TimeVision' },
  { key: 'admin', label: 'Správa' },
]

function switchTo(workspace: WorkspaceType) {
  workspaceStore.switchWorkspace(workspace)
}
</script>

<template>
  <nav class="workspace-switcher" role="tablist" data-testid="workspace-switcher">
    <button
      v-for="ws in workspaces"
      :key="ws.key"
      class="ws-chip"
      :class="{ active: workspaceStore.activeWorkspace === ws.key }"
      role="tab"
      :aria-selected="workspaceStore.activeWorkspace === ws.key"
      @click="switchTo(ws.key)"
      :data-testid="`ws-${ws.key}`"
    >{{ ws.label }}</button>
  </nav>
</template>

<style scoped>
.workspace-switcher {
  display: flex;
  gap: 1px;
  flex-shrink: 0;
}

.ws-chip {
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

.ws-chip:hover {
  color: var(--t3);
  background: rgba(255, 255, 255, 0.06);
}

.ws-chip.active {
  color: var(--t1);
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.10);
}
</style>
