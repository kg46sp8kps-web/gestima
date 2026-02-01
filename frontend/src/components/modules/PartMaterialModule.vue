<script setup lang="ts">
/**
 * Part Material Module - Split-pane coordinator
 *
 * LEFT: PartListPanel (when standalone) OR Linked badge (when linked)
 * RIGHT: MaterialHeader + MaterialDetailPanel
 */

import { ref, computed, watch, onMounted } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useWindowContextStore } from '@/stores/windowContext'
import { useMaterialsStore } from '@/stores/materials'
import type { LinkingGroup } from '@/stores/windows'
import type { Part } from '@/types/part'

import PartListPanel from './parts/PartListPanel.vue'
import MaterialHeader from './material/MaterialHeader.vue'
import MaterialDetailPanel from './material/MaterialDetailPanel.vue'

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
const materialsStore = useMaterialsStore()

// State
const selectedPart = ref<Part | null>(null)
const listPanelRef = ref<InstanceType<typeof PartListPanel> | null>(null)

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
const materialInputs = computed(() => materialsStore.getContext(props.linkingGroup).materialInputs)

// Handlers
function handleSelectPart(part: Part) {
  selectedPart.value = part

  // Update window context
  if (props.linkingGroup) {
    contextStore.setContext(props.linkingGroup, part.id, part.part_number, part.article_number)
  }
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
    <!-- LEFT PANEL: Only visible when standalone (not linked) -->
    <div v-if="!isLinked" class="left-panel">
      <PartListPanel
        ref="listPanelRef"
        :linkingGroup="linkingGroup"
        @select-part="handleSelectPart"
      />
    </div>

    <!-- RIGHT PANEL: Header + Detail (full width when linked) -->
    <div class="right-panel" :class="{ 'full-width': isLinked }">
      <MaterialHeader
        :part="selectedPart"
        :materialInputs="materialInputs"
      />
      <MaterialDetailPanel
        :partId="currentPartId"
        :linkingGroup="linkingGroup"
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

/* === RIGHT PANEL === */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.right-panel.full-width {
  width: 100%;
}
</style>
