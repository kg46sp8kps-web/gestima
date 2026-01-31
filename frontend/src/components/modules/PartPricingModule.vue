<script setup lang="ts">
/**
 * Part Pricing Module - Split-pane coordinator
 *
 * LEFT: PartListPanel (when standalone) OR Linked badge (when linked)
 * RIGHT: PricingHeader + PricingDetailPanel
 */

import { ref, computed, watch, onMounted } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useWindowContextStore } from '@/stores/windowContext'
import type { LinkingGroup } from '@/stores/windows'
import type { Part } from '@/types/part'
import type { Batch } from '@/types/batch'
import { Link } from 'lucide-vue-next'

import PartListPanel from './parts/PartListPanel.vue'
import PricingHeader from './pricing/PricingHeader.vue'
import PricingDetailPanel from './pricing/PricingDetailPanel.vue'

interface Props {
  inline?: boolean
  partId: number | null
  partNumber: string
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  inline: false,
  linkingGroup: null
})

const partsStore = usePartsStore()
const contextStore = useWindowContextStore()

// State
const selectedPart = ref<Part | null>(null)
const listPanelRef = ref<InstanceType<typeof PartListPanel> | null>(null)
const batches = ref<Batch[]>([])

// Computed
const isLinked = computed(() => props.linkingGroup !== null)

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
    contextStore.setContext(props.linkingGroup, part.id, part.part_number)
  }
}

function handleBatchesUpdated(updatedBatches: Batch[]) {
  batches.value = updatedBatches
}

// Load parts on mount
onMounted(async () => {
  await partsStore.fetchParts()

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

// Watch linked context changes (watch contextPartId computed for reactivity)
watch(contextPartId, (newPartId) => {
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
    <!-- LEFT PANEL: Collapsed badge when linked, full list when standalone -->
    <div v-if="!isLinked" class="left-panel">
      <PartListPanel
        ref="listPanelRef"
        :linkingGroup="linkingGroup"
        @select-part="handleSelectPart"
      />
    </div>
    <div v-else class="left-panel-linked">
      <div class="linked-badge">
        <span class="link-icon">
          <Link :size="20" />
        </span>
        <div class="badge-content">
          <span class="badge-label">Linked to</span>
          <span class="badge-value">{{ selectedPart?.part_number || '-' }}</span>
        </div>
      </div>
    </div>

    <!-- RIGHT PANEL: Header + Detail -->
    <div class="right-panel">
      <PricingHeader
        :part="selectedPart"
        :batches="batches"
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
  width: 320px;
  min-width: 320px;
  padding: var(--space-3);
  height: 100%;
  border-right: 1px solid var(--border-default);
}

/* === LEFT PANEL LINKED (collapsed badge) === */
.left-panel-linked {
  width: 80px;
  min-width: 80px;
  padding: var(--space-3);
  height: 100%;
  border-right: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.linked-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-lg);
  text-align: center;
}

.link-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.badge-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.badge-label {
  font-size: var(--text-xs);
  opacity: 0.8;
}

.badge-value {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

/* === RIGHT PANEL === */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
</style>
