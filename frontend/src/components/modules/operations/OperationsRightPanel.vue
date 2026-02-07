<script setup lang="ts">
/**
 * Operations Right Panel Component (BUILDING BLOCK - L-039)
 * Reusable right panel for PartOperations + PartTechnology modules
 *
 * Contains:
 * - MaterialInputSelector (dropdown + add button)
 * - OperationsHeader (when standalone)
 * - OperationsDetailPanel (operations table)
 * - OperationDetailPanel (feature detail split)
 */

import { ref, computed } from 'vue'
import type { LinkingGroup } from '@/stores/windows'
import type { Part } from '@/types/part'
import type { Operation } from '@/types/operation'

import OperationsHeader from './OperationsHeader.vue'
import OperationsDetailPanel from './OperationsDetailPanel.vue'
import MaterialInputSelectorV2 from './MaterialInputSelectorV2.vue'

interface Props {
  part: Part | null
  partId: number | null
  linkingGroup?: LinkingGroup
  showHeader?: boolean  // Show OperationsHeader (true for standalone, false for linked)
}

const props = withDefaults(defineProps<Props>(), {
  linkingGroup: null,
  showHeader: true
})

// State
const detailPanelRef = ref<InstanceType<typeof OperationsDetailPanel> | null>(null)

// Computed
const operationsCount = computed(() => detailPanelRef.value?.operationsCount || 0)

// Handle select operation
function handleSelectOperation(op: Operation | null) {
  // Feature detail panel removed - placeholder
}

// Expose operationsCount for parent
defineExpose({
  operationsCount: computed(() => operationsCount.value)
})
</script>

<template>
  <div class="operations-right-panel">
    <!-- OPERATIONS HEADER (when standalone) -->
    <OperationsHeader
      v-if="showHeader"
      :part="part"
      :operationsCount="operationsCount"
    />

    <!-- MATERIAL INPUT SELECTOR V2 (parser + dropdown) -->
    <MaterialInputSelectorV2
      :partId="partId"
      :linkingGroup="linkingGroup"
    />

    <!-- OPERATIONS DETAIL PANEL -->
    <div class="operations-split">
      <div class="operations-main">
        <OperationsDetailPanel
          ref="detailPanelRef"
          :partId="partId"
          :linkingGroup="linkingGroup"
          @select-operation="handleSelectOperation"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* === PANEL LAYOUT === */
.operations-right-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* === OPERATIONS SPLIT (Operations | Features) === */
.operations-split {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.operations-main {
  flex: 1;
  overflow: hidden;
}

.feature-panel {
  flex-shrink: 0;
  border-left: 1px solid var(--border-default);
  overflow: hidden;
}

.feature-resize-handle {
  width: 4px;
  background: var(--border-default);
  cursor: col-resize;
  flex-shrink: 0;
  transition: background var(--transition-fast);
}

.feature-resize-handle:hover {
  background: var(--color-primary);
}
</style>
