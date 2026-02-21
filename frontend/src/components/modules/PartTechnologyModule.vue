<script setup lang="ts">
/**
 * Part Technology Module - Split-pane coordinator
 *
 * Unified view: Material + Operations + Features in one module
 * REUSES OperationsRightPanel from PartOperationsModule (DRY principle)
 *
 * LEFT: PartListPanel (when standalone) OR Linked badge (when linked)
 * RIGHT: OperationsRightPanel (Material selector + Operations + Features)
 */

import { ref, computed, watch, onMounted } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useWindowsStore } from '@/stores/windows'
import { useWindowContextStore } from '@/stores/windowContext'
import { useResizablePanel } from '@/composables/useResizablePanel'
import { useLinkedWindowOpener } from '@/composables/useLinkedWindowOpener'
import type { LinkingGroup, WindowRole } from '@/stores/windows'
import type { Part } from '@/types/part'
import { ChevronRight, ChevronDown } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

import PartListPanel from './parts/PartListPanel.vue'
import OperationsRightPanel from './operations/OperationsRightPanel.vue'
import PartDetailPanel from './parts/PartDetailPanel.vue'

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
const windowsStore = useWindowsStore()
const contextStore = useWindowContextStore()

// State
const selectedPart = ref<Part | null>(null)
const listPanelRef = ref<InstanceType<typeof PartListPanel> | null>(null)
const rightPanelRef = ref<InstanceType<typeof OperationsRightPanel> | null>(null)
const ribbonExpanded = ref(false)

// Je právě otevřený nový (virtual) díl?
const isCreating = computed(() => selectedPart.value?.id === -1)

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

const isLinked = computed(() => props.linkingGroup !== null)
const currentPartId = computed(() => {
  if (isCreating.value) return null
  return selectedPart.value?.id || effectivePartId.value
})

// Resizable panel (only when NOT linked)
const { panelWidth, isDragging, startResize } = useResizablePanel({
  storageKey: 'partTechnologyPanelWidth',
  defaultWidth: 320,
  minWidth: 250,
  maxWidth: 1000
})

// Linked window opener
const { openLinked } = useLinkedWindowOpener({
  get windowId() { return props.windowId },
  get linkingGroup() { return props.linkingGroup ?? null },
  onGroupAssigned(group) {
    if (selectedPart.value?.id && selectedPart.value.id > 0) {
      contextStore.setContext(group, selectedPart.value.id, selectedPart.value.part_number, selectedPart.value.article_number)
    }
  }
})

// Create new part — virtual part pattern (PartDetailPanel detects id=-1 a otevře edit mód)
function handleCreateNew() {
  const virtualPart: Part = {
    id: -1,
    part_number: 'NOVÝ',
    article_number: '',
    name: '',
    drawing_path: null,
    drawing_number: null,
    customer_revision: null,
    revision: 'A',
    status: 'draft',
    source: 'manual',
    file_id: null,
    length: 0,
    notes: '',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    version: 0,
    created_by_name: null
  }
  selectedPart.value = virtualPart
  listPanelRef.value?.setSelection(-1)
}

// PartDetailPanel callbacks
async function handlePartCreated(createdPart: Part) {
  selectedPart.value = createdPart
  listPanelRef.value?.prependAndSelect(createdPart)
  if (props.linkingGroup) {
    contextStore.setContext(props.linkingGroup, createdPart.id, createdPart.part_number, createdPart.article_number)
  }
}

function handleCancelCreate() {
  selectedPart.value = null
  listPanelRef.value?.setSelection(null)
}

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

// Watch linked context changes — only for child windows (master drives the context, not follows it)
watch(contextPartId, (newPartId) => {
  if (props.windowRole === 'master') return
  ribbonExpanded.value = false
  if (isLinked.value && newPartId) {
    const part = partsStore.parts.find(p => p.id === newPartId)
    selectedPart.value = part ?? null
  } else if (isLinked.value) {
    selectedPart.value = null
  }
}, { immediate: true })

// Window actions (from PartListPanel icons)
function openPricingWindow() {
  if (!selectedPart.value) return
  openLinked('part-pricing', `Ceny - ${selectedPart.value.part_number}`)
}

function openDrawingWindow(drawingId?: number) {
  if (!selectedPart.value) return
  const title = drawingId
    ? `Drawing #${drawingId} - ${selectedPart.value.part_number}`
    : `Drawing - ${selectedPart.value.part_number}`
  if (drawingId) {
    windowsStore.openWindow('part-drawing', title, null)
  } else {
    openLinked('part-drawing', title)
  }
}

// Refresh part data after edit
async function handlePartRefresh() {
  await partsStore.fetchParts()
  if (selectedPart.value) {
    const fresh = partsStore.parts.find(p => p.id === selectedPart.value!.id)
    if (fresh) selectedPart.value = fresh
  }
}

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
    <!-- LEFT PANEL: Visible when standalone, master, or manually linked (no explicit child role) -->
    <div v-if="!linkingGroup || windowRole !== 'child'" class="left-panel" :style="{ width: `${panelWidth}px` }">
      <PartListPanel
        ref="listPanelRef"
        :linkingGroup="linkingGroup"
        :readonly="isCreating"
        @select-part="handleSelectPart"
        @create-new="handleCreateNew"
        @open-pricing="openPricingWindow"
        @open-drawing="openDrawingWindow()"
        @open-technology="() => {}"
      />
    </div>

    <!-- RESIZE HANDLE: Only visible when left panel is shown -->
    <div
      v-if="!linkingGroup || windowRole !== 'child'"
      class="resize-handle"
      :class="{ dragging: isDragging }"
      @mousedown="startResize"
    ></div>

    <!-- RIGHT PANEL: Reusable right panel component (full width when linked) -->
    <div class="right-panel" :class="{ 'full-width': linkingGroup && windowRole === 'child' }">

      <!-- CONTEXT INFO RIBBON — collapsible; nový díl (id=-1) se rovnou otevře v edit módu -->
      <div v-if="selectedPart" class="context-ribbon-wrap">
        <!-- Řádek s chevronem — pro nový díl text "Nový díl", jinak article + name -->
        <div class="context-ribbon" @click="!isCreating && (ribbonExpanded = !ribbonExpanded)">
          <component
            :is="(ribbonExpanded || isCreating) ? ChevronDown : ChevronRight"
            :size="ICON_SIZE.SMALL"
            class="ribbon-chevron"
          />
          <span class="ctx-article">{{ isCreating ? 'Nový díl' : (selectedPart.article_number || selectedPart.part_number) }}</span>
          <span v-if="!isCreating" class="ctx-name">{{ selectedPart.name || '-' }}</span>
        </div>
        <Transition name="slide">
          <div v-if="ribbonExpanded || isCreating" class="ribbon-detail-expand">
            <PartDetailPanel
              :part="selectedPart"
              :showActions="false"
              @created="handlePartCreated"
              @cancel-create="handleCancelCreate"
              @refresh="handlePartRefresh"
            />
          </div>
        </Transition>
      </div>

      <!-- REUSABLE RIGHT PANEL (Material + Operations + Features) — skrytý při vytváření -->
      <OperationsRightPanel
        v-if="selectedPart && !isCreating"
        ref="rightPanelRef"
        :part="selectedPart"
        :partId="currentPartId"
        :linkingGroup="linkingGroup"
        :showHeader="false"
        @refresh-part="handlePartRefresh"
        @open-material="() => {}"
        @open-pricing="openPricingWindow"
        @open-drawing="openDrawingWindow"
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
  padding: var(--space-3);
  height: 100%;
  overflow: hidden;
}

/* === RESIZE HANDLE === */
.resize-handle {
  width: 4px;
  background: var(--border-default);
  cursor: col-resize;
  flex-shrink: 0;
  transition: background var(--transition-fast);
  position: relative;
}

.resize-handle:hover,
.resize-handle.dragging {
  background: var(--color-primary);
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
.context-ribbon-wrap {
  flex-shrink: 0;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-surface);
}

.context-ribbon {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  user-select: none;
}

.context-ribbon:hover {
  background: var(--bg-raised);
}

.ribbon-chevron {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.ctx-article {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  letter-spacing: 0.02em;
  flex-shrink: 0;
}

.ctx-name {
  font-size: var(--text-xs);
  font-weight: var(--font-normal);
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.ribbon-detail-expand {
  border-top: 1px solid var(--border-default);
  max-height: 400px;
  overflow-y: auto;
}

/* Odstraň rámeček z PartDetailPanel uvnitř ribbonu */
.ribbon-detail-expand :deep(.info-ribbon) {
  border: none;
  border-radius: 0;
  margin-bottom: 0;
  box-shadow: none;
}

/* Slide transition */
.slide-enter-active,
.slide-leave-active {
  transition: max-height 0.25s ease, opacity 0.2s ease;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  max-height: 0;
  opacity: 0;
}

.slide-enter-to,
.slide-leave-from {
  max-height: 400px;
  opacity: 1;
}


</style>
