<script setup lang="ts">
/**
 * Part Main Module - Split-pane layout coordinator
 *
 * LEFT: PartListPanel (always visible, sorted, filterable)
 * RIGHT: Empty / PartDetailPanel / PartCreateForm
 */

import { ref, watch, onMounted } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useWindowsStore } from '@/stores/windows'
import { useWindowContextStore } from '@/stores/windowContext'
import type { LinkingGroup } from '@/stores/windows'
import type { Part } from '@/types/part'

import PartListPanel from './parts/PartListPanel.vue'
import PartDetailPanel from './parts/PartDetailPanel.vue'
import PartCreateForm from './parts/PartCreateForm.vue'

interface Props {
  partNumber?: string
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  partNumber: undefined,
  linkingGroup: null
})

const emit = defineEmits<{
  'select-part': [partNumber: string]
}>()

const partsStore = usePartsStore()
const windowsStore = useWindowsStore()
const contextStore = useWindowContextStore()

// State
const selectedPart = ref<Part | null>(null)
const isCreating = ref(false)
const listPanelRef = ref<InstanceType<typeof PartListPanel> | null>(null)

// Handlers
function handleSelectPart(part: Part) {
  selectedPart.value = part
  isCreating.value = false

  // Update window context
  if (props.linkingGroup) {
    contextStore.setContext(props.linkingGroup, part.id, part.part_number)
  }

  emit('select-part', part.part_number)
}

function handleCreateNew() {
  isCreating.value = true
  selectedPart.value = null
  listPanelRef.value?.setSelection(null)
}

function handleCreated(part: Part) {
  isCreating.value = false
  selectedPart.value = part
  listPanelRef.value?.setSelection(part.id)

  if (props.linkingGroup) {
    contextStore.setContext(props.linkingGroup, part.id, part.part_number)
  }

  emit('select-part', part.part_number)
}

function handleCancelCreate() {
  isCreating.value = false
}

// Window actions
function openMaterialWindow() {
  if (!selectedPart.value || !props.linkingGroup) return
  windowsStore.openWindow('part-material', props.linkingGroup)
}

function openOperationsWindow() {
  if (!selectedPart.value || !props.linkingGroup) return
  windowsStore.openWindow('part-operations', props.linkingGroup)
}

function openPricingWindow() {
  if (!selectedPart.value || !props.linkingGroup) return
  windowsStore.openWindow('part-pricing', props.linkingGroup)
}

// Load parts on mount and auto-select if partNumber provided
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
})

// Watch prop changes (for external part selection)
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
    <!-- LEFT PANEL: Parts List -->
    <div class="left-panel">
      <PartListPanel
        ref="listPanelRef"
        :linkingGroup="linkingGroup"
        @select-part="handleSelectPart"
        @create-new="handleCreateNew"
      />
    </div>

    <!-- RIGHT PANEL: Detail / Create / Empty -->
    <div class="right-panel">
      <!-- Mode 1: EMPTY -->
      <div v-if="!selectedPart && !isCreating" class="empty">
        <div class="empty-icon">🔍</div>
        <p>Vyberte díl ze seznamu vlevo</p>
      </div>

      <!-- Mode 2: DETAIL -->
      <PartDetailPanel
        v-else-if="selectedPart && !isCreating"
        :part="selectedPart"
        :linkingGroup="linkingGroup"
        @open-material="openMaterialWindow"
        @open-operations="openOperationsWindow"
        @open-pricing="openPricingWindow"
      />

      <!-- Mode 3: CREATE -->
      <PartCreateForm
        v-else-if="isCreating"
        @created="handleCreated"
        @cancel="handleCancelCreate"
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
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}

/* Empty State */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-8);
  color: var(--text-secondary);
  text-align: center;
  height: 100%;
}

.empty .empty-icon {
  font-size: 3rem;
  margin-bottom: var(--space-2);
}

.empty p {
  font-size: var(--text-base);
}
</style>
