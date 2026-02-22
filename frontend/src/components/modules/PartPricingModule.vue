<script setup lang="ts">
/**
 * Part Pricing Module - Split-pane coordinator
 *
 * LEFT: PartListPanel (when standalone) OR Linked badge (when linked)
 * RIGHT: PricingHeader + PricingDetailPanel
 */

import { ref, computed, watch, onMounted } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useBatchesStore } from '@/stores/batches'
import { useWindowContextStore } from '@/stores/windowContext'
import { useResizablePanel } from '@/composables/useResizablePanel'
import type { LinkingGroup, WindowRole } from '@/stores/windows'
import type { Part } from '@/types/part'
import type { Batch, BatchSet } from '@/types/batch'

import PartListPanel from './parts/PartListPanel.vue'
import PricingHeader from './pricing/PricingHeader.vue'
import PricingDetailPanel from './pricing/PricingDetailPanel.vue'

interface Props {
  windowId?: string
  windowRole?: WindowRole
  inline?: boolean
  partId?: number | null
  partNumber?: string
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  windowRole: null,
  inline: false,
  partId: null,
  partNumber: undefined,
  linkingGroup: null
})

const partsStore = usePartsStore()
const batchesStore = useBatchesStore()
const contextStore = useWindowContextStore()

// State
const selectedPart = ref<Part | null>(null)
const listPanelRef = ref<InstanceType<typeof PartListPanel> | null>(null)
const batches = ref<Batch[]>([])

// Computed
const isLinked = computed(() => props.linkingGroup !== null)
const batchSets = computed(() => {
  const ctx = batchesStore.getContext(props.linkingGroup)
  return ctx.batchSets
})

// Resizable panel (only when NOT linked)
const { panelWidth, isDragging, startResize } = useResizablePanel({
  storageKey: 'partPricingPanelWidth',
  defaultWidth: 320,
  minWidth: 250,
  maxWidth: 1000
})

// Computed: Get partId from window context (direct property access for fine-grained reactivity)
const contextPartId = computed(() => {
  if (!props.linkingGroup) return null

  switch (props.linkingGroup) {
    case 'red': return contextStore.redContext.partId
    case 'blue': return contextStore.blueContext.partId
    case 'green': return contextStore.greenContext.partId
    case 'yellow': return contextStore.yellowContext.partId
    default: return null
  }
})

// Effective partId (context or props)
const effectivePartId = computed(() => contextPartId.value ?? props.partId)
const currentPartId = computed(() => selectedPart.value?.id || effectivePartId.value)

// Handlers
function handleSelectPart(part: Part) {
  selectedPart.value = part

  // Update window context
  if (props.linkingGroup) {
    contextStore.setContext(props.linkingGroup, part.id, part.part_number, part.article_number)
  }
}

function handleBatchesUpdated(updatedBatches: Batch[]) {
  batches.value = updatedBatches
}

// Load parts on mount
onMounted(async () => {
  // Only fetch if parts not loaded yet (prevents list refresh/scroll reset)
  if (partsStore.parts.length === 0) {
    await partsStore.fetchParts()
  }

  // If partNumber prop provided, select it
  if (props.partNumber) {
    const part = partsStore.parts.find(p => p.part_number === props.partNumber)
    if (part) {
      handleSelectPart(part)
      listPanelRef.value?.setSelection(part.id)
    }
  }

  // If partId prop provided (without partNumber), select by ID
  if (props.partId && !props.partNumber) {
    const part = partsStore.parts.find(p => p.id === props.partId)
    if (part) {
      selectedPart.value = part
    }
  }
})

// Watch linked context changes — only for child windows
watch(contextPartId, (newPartId) => {
  if (props.windowRole === 'master') return
  if (isLinked.value && newPartId) {
    const part = partsStore.parts.find(p => p.id === newPartId)
    if (part) {
      selectedPart.value = part
    }
  }
}, { immediate: true })

// Watch prop changes
watch(() => props.partNumber, (newPartNumber) => {
  if (newPartNumber) {
    const part = partsStore.parts.find(p => p.part_number === newPartNumber)
    if (part) {
      handleSelectPart(part)
      listPanelRef.value?.setSelection(part.id)
    }
  }
})
</script>

<template>
  <div class="split-layout">
    <!-- LEFT PANEL: Visible when standalone OR when this window is the linking master -->
    <div v-if="!linkingGroup || windowRole === 'master'" class="left-panel" :style="{ width: `${panelWidth}px` }">
      <PartListPanel
        ref="listPanelRef"
        :linkingGroup="linkingGroup"
        @select-part="handleSelectPart"
      />
    </div>

    <!-- RESIZE HANDLE: Only visible when left panel is shown -->
    <div
      v-if="!linkingGroup || windowRole === 'master'"
      class="resize-handle"
      :class="{ dragging: isDragging }"
      @mousedown="startResize"
    ></div>

    <!-- RIGHT PANEL: Header + Detail (full width when child) -->
    <div class="right-panel" :class="{ 'full-width': linkingGroup && windowRole !== 'master' }">
      <!-- CONTEXT INFO RIBBON (only for child windows) -->
      <div v-if="linkingGroup && windowRole !== 'master' && selectedPart" class="context-ribbon">
        <span class="context-label">Ceny</span>
        <span class="context-divider">|</span>
        <span class="context-value">{{ selectedPart.part_number }}</span>
        <span class="context-divider">|</span>
        <span class="context-value">{{ selectedPart.article_number || '-' }}</span>
        <span class="context-divider">|</span>
        <span class="context-value">{{ selectedPart.name || '-' }}</span>
      </div>

      <!-- PRICING HEADER (when standalone or master) -->
      <PricingHeader
        v-if="!linkingGroup || windowRole === 'master'"
        :part="selectedPart"
        :batchSets="batchSets"
      />

      <PricingDetailPanel
        :partId="currentPartId"
        :linkingGroup="linkingGroup"
        @batches-updated="handleBatchesUpdated"
      />
    </div>
  </div>
</template>

<style scoped>
/* === SPLIT LAYOUT === */
.split-layout {
  display: flex;
  gap: 0;
  height: 100%;
  overflow: hidden;
}

/* === LEFT PANEL === */
.left-panel {
  flex-shrink: 0;
  /* width set via :style binding */
  padding: var(--pad);
  height: 100%;
  overflow: hidden;
}

/* === RESIZE HANDLE === */
.resize-handle {
  width: 4px;
  background: var(--b2);
  cursor: col-resize;
  flex-shrink: 0;
  transition: background all 100ms var(--ease);
  position: relative;
}

.resize-handle:hover,
.resize-handle.dragging {
  background: var(--red);
}

/* Wider hit area for easier dragging */
.resize-handle::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: -4px;
  right: -4px;
  cursor: col-resize;
}

/* === RIGHT PANEL === */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  container-type: inline-size;
  container-name: right-panel;
}

.right-panel.full-width {
  width: 100%;
}

/* === CONTEXT INFO RIBBON === */
.context-ribbon {
  display: flex;
  align-items: center;
  gap: var(--pad);
  padding: var(--pad) 12px;
  background: var(--surface);
  border-bottom: 1px solid var(--b2);
  flex-shrink: 0;
}

.context-label {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--red);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.context-divider {
  color: var(--b2);
  font-weight: 300;
}

.context-value {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t1);
}
</style>
