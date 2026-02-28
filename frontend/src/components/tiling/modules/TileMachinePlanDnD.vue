<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import draggable from 'vuedraggable'
import { useSplitLayoutStore } from '@/stores/splitLayout'
import { useSplitResize } from '@/composables/useSplitResize'
import { useMachinePlanDndStore } from '@/stores/machinePlanDnd'
import { useCatalogStore } from '@/stores/catalog'
import { useWorkshopStore } from '@/stores/workshop'
import { useUiStore } from '@/stores/ui'
import { getMachinePlan } from '@/api/workshop'
import { ICON_SIZE_SM } from '@/config/design'
import WorkshopOperationPanel from '@/components/modules/workshop/WorkshopOperationPanel.vue'
import MachinePlanDndRow from '@/components/modules/workshop/MachinePlanDndRow.vue'
import Spinner from '@/components/ui/Spinner.vue'
import type { MachinePlanItem } from '@/types/workshop'
import type { ContextGroup } from '@/types/workspace'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()

const store = useMachinePlanDndStore()
const catalog = useCatalogStore()
const workshopStore = useWorkshopStore()
const ui = useUiStore()
const splitLayout = useSplitLayoutStore()

// ─── Cross-tile linking (VP focus) ──────────────────────────────────
const focusedVp = computed(() => {
  const item = catalog.getFocusedItem(props.ctx)
  if (item?.type === 'vp') return item.number
  return null
})

const layoutMode = computed(() => splitLayout.getMode(props.leafId, 'machine-plan-dnd'))
onUnmounted(() => splitLayout.cleanup(props.leafId))

// Resize
const containerRef = ref<HTMLElement | null>(null)
const { splitPct, isDragging: isResizing, startResize } = useSplitResize(layoutMode, containerRef, 50)

// WC options — načteno z Infor machine plan
const wcOptions = ref<string[]>([])
const loadingWcList = ref(false)

async function loadWcOptions() {
  loadingWcList.value = true
  try {
    const items = await getMachinePlan({ limit: 500 })
    const wcs = new Set<string>()
    for (const item of items) {
      if (item.Wc) wcs.add(item.Wc)
    }
    wcOptions.value = Array.from(wcs).sort()
  } catch {
    // silently fail — WC list is not critical
  } finally {
    loadingWcList.value = false
  }
}

// WC selection
function onWcChange(wc: string) {
  if (wc) {
    store.fetchPlan(wc)
  }
}

// DnD end handler — mark moved item as frozen
function onDragEnd(evt: { oldIndex?: number; newIndex?: number }) {
  const newOrder = [...store.plannedItems]
  store.reorder(newOrder)

  // Detect moved item and mark as frozen
  const idx = evt.newIndex
  if (idx != null && idx >= 0 && idx < newOrder.length) {
    const moved = newOrder[idx]!
    store.markFrozen(moved)
  }
}

function onSelect(item: MachinePlanItem) {
  store.selectItem(item)
  catalog.focusItem({ type: 'vp', number: item.Job }, props.ctx)
}

function onCycleTier(item: MachinePlanItem) {
  store.cycleTier(item).then(() => {
    const tier = item.Tier ?? 'normal'
    catalog.notifyTierChange(item.Job, item.Suffix ?? '0', tier)
  })
}

function isActive(item: MachinePlanItem): boolean {
  if (store.selectedItem) {
    return (
      store.selectedItem.Job === item.Job &&
      store.selectedItem.Suffix === item.Suffix &&
      store.selectedItem.OperNum === item.OperNum
    )
  }
  return focusedVp.value === item.Job
}

function refresh() {
  if (store.selectedWc) {
    store.fetchPlan(store.selectedWc)
  }
}

// Watch external VP focus from other tiles → auto-select matching item
watch(focusedVp, (job) => {
  if (!job) return
  // Don't override if we already have this job selected
  if (store.selectedItem?.Job === job) return
  const all = [...store.plannedItems, ...store.unassignedItems]
  const match = all.find((i) => i.Job === job)
  if (match) {
    store.selectItem(match)
  }
})

// Watch cross-tile tier changes from other tiles
watch(() => catalog.lastTierChange, (change) => {
  if (!change) return
  const all = [...store.plannedItems, ...store.unassignedItems]
  for (const item of all) {
    if (item.Job === change.job) {
      item.Tier = change.tier
      item.IsHot = change.tier === 'hot'
      item.Priority = change.tier === 'hot' ? 5 : change.tier === 'urgent' ? 20 : 100
    }
  }
})

onMounted(() => {
  loadWcOptions()
})
</script>

<template>
  <div ref="containerRef" class="mpd-root" :class="layoutMode">
    <!-- List panel -->
    <div
      class="mpd-list-wrap"
      :style="store.selectedItem
        ? layoutMode === 'vertical'
          ? { width: `${splitPct}%` }
          : { height: `${splitPct}%` }
        : {}"
    >
      <!-- Toolbar -->
      <div class="mpd-toolbar">
        <select
          :value="store.selectedWc"
          class="mpd-select"
          @change="onWcChange(($event.target as HTMLSelectElement).value)"
        >
          <option value="" disabled>Pracoviště…</option>
          <option v-for="wc in wcOptions" :key="wc" :value="wc">{{ wc }}</option>
        </select>
        <button class="mpd-btn-refresh" title="Obnovit" @click="refresh">
          <RefreshCw :size="ICON_SIZE_SM" />
        </button>
      </div>

      <!-- Loading -->
      <div v-if="store.loading || loadingWcList" class="mpd-loading">
        <Spinner size="sm" />
      </div>

      <!-- No WC selected -->
      <div v-else-if="!store.selectedWc" class="mpd-empty">
        Vyberte pracoviště
      </div>

      <div v-else class="mpd-list-scroll">
        <!-- Fronta práce (Released) -->
        <div class="mpd-section">
          <div class="mpd-section__header mpd-section__header--planned">
            Fronta ({{ store.plannedItems.length }})
          </div>
          <draggable
            :list="store.plannedItems"
            item-key="Job+Suffix+OperNum"
            handle=".drag-handle"
            ghost-class="mpd-ghost"
            drag-class="mpd-drag"
            @end="onDragEnd"
          >
            <template #item="{ element }">
              <MachinePlanDndRow
                :item="element"
                :active="isActive(element)"
                mode="planned"
                @select="onSelect"
                @cycle-tier="onCycleTier"
              />
            </template>
          </draggable>
          <div v-if="!store.plannedItems.length" class="mpd-section__empty">
            Žádné released operace
          </div>
        </div>

        <!-- Zásobník (F/S/W) -->
        <div v-if="store.unassignedItems.length" class="mpd-section">
          <div class="mpd-section__header mpd-section__header--unassigned">
            Zásobník ({{ store.unassignedItems.length }})
          </div>
          <MachinePlanDndRow
            v-for="item in store.unassignedItems"
            :key="`${item.Job}-${item.Suffix}-${item.OperNum}-ua`"
            :item="item"
            :active="isActive(item)"
            mode="unassigned"
            @select="onSelect"
            @cycle-tier="onCycleTier"
          />
        </div>

        <!-- Empty state -->
        <div v-if="!store.plannedItems.length && !store.unassignedItems.length" class="mpd-empty">
          Žádné operace pro toto pracoviště
        </div>
      </div>
    </div>

    <!-- Resize handle -->
    <div
      v-if="store.selectedItem"
      :class="['resize-handle', layoutMode, { dragging: isResizing }]"
      @mousedown.prevent="startResize"
    />

    <!-- Detail panel -->
    <div v-if="store.selectedItem" class="mpd-detail-wrap">
      <WorkshopOperationPanel />
    </div>

    <!-- Placeholder when nothing selected -->
    <div v-if="!store.selectedItem && !store.loading && store.selectedWc" class="mpd-detail-placeholder">
      <span>Vyberte operaci ze seznamu</span>
    </div>
  </div>
</template>

<style scoped>
.mpd-root {
  display: flex;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  position: relative;
}
.mpd-root.vertical   { flex-direction: row; }
.mpd-root.horizontal { flex-direction: column; }

.mpd-list-wrap {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  flex: 1;
}
.mpd-list-wrap[style] { flex: none; }

.mpd-detail-wrap {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.mpd-root.vertical   .mpd-detail-wrap { border-left: 1px solid var(--b1); }
.mpd-root.horizontal .mpd-detail-wrap { border-top: 1px solid var(--b1); }

.mpd-detail-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--t4);
  font-size: var(--fsm);
}

/* Resize handle */
.resize-handle {
  flex-shrink: 0;
  background: transparent;
  transition: background 120ms var(--ease);
}
.resize-handle.vertical   { width: 5px; cursor: col-resize; }
.resize-handle.horizontal { height: 5px; cursor: row-resize; }
.resize-handle:hover,
.resize-handle.dragging { background: var(--b2); }

/* Toolbar */
.mpd-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}

.mpd-select {
  flex: 1;
  min-width: 100px;
  padding: 4px 6px;
  font-size: var(--fsm);
  background: var(--surface);
  color: var(--t1);
  border: 1px solid var(--b1);
  border-radius: var(--r-sm);
  outline: none;
}
.mpd-select:focus { border-color: var(--b2); }

.mpd-btn-refresh {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  background: transparent;
  border: 1px solid var(--b1);
  border-radius: var(--r-sm);
  color: var(--t3);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}
.mpd-btn-refresh:hover {
  color: var(--t1);
  border-color: var(--b2);
}

/* Loading */
.mpd-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  flex: 1;
}

/* List scroll area */
.mpd-list-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

/* Section headers */
.mpd-section {
  margin-bottom: 2px;
}
.mpd-section__header {
  position: sticky;
  top: 0;
  z-index: 2;
  padding: 4px 8px;
  font-size: var(--fsm);
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  background: var(--surface);
}
.mpd-section__header--planned {
  color: var(--green, #4caf50);
  border-bottom: 1px solid color-mix(in srgb, var(--green, #4caf50) 30%, transparent);
}
.mpd-section__header--unassigned {
  color: var(--t3);
  border-bottom: 1px solid var(--b1);
}
.mpd-section__empty {
  padding: 12px 8px;
  color: var(--t4);
  font-size: var(--fsm);
  text-align: center;
  font-style: italic;
}

/* DnD ghost/drag states */
.mpd-ghost {
  opacity: 0.4;
  background: color-mix(in srgb, var(--green, #4caf50) 10%, transparent);
}
.mpd-drag {
  opacity: 0.9;
  background: var(--surface);
  box-shadow: 0 4px 16px rgba(0,0,0,0.3);
}

/* Empty state */
.mpd-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  color: var(--t4);
  font-size: var(--fsm);
  flex: 1;
}
</style>
