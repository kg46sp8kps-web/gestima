<script setup lang="ts">
/**
 * MaterialItemsListPanel - Virtualized material items list
 *
 * Identical pattern to PartListPanel:
 * - @tanstack/vue-virtual — only ~30 rows in DOM at any time
 * - 200 rows first load, batch 50 on scroll
 * - initialLoading spinner only on first open
 * - Store cache — instant re-open
 */
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import { useMaterialsStore } from '@/stores/materials'
import type { MaterialItem } from '@/types/material'
import { Plus, Upload } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import Spinner from '@/components/ui/Spinner.vue'

interface Props {
  selectedItem?: MaterialItem | null
}

const props = withDefaults(defineProps<Props>(), {
  selectedItem: null
})

const emit = defineEmits<{
  'select-item': [item: MaterialItem]
  'item-created': [item: MaterialItem]
}>()

const materialsStore = useMaterialsStore()

// Local UI state
const searchQuery = ref('')
const filterGroupId = ref<number | null>(null)
const filterShape = ref<string | null>(null)
const selectedItemNumber = ref<string | null>(null)
let searchTimer: ReturnType<typeof setTimeout> | null = null

// Row height — same as PartListPanel
const ROW_HEIGHT = 30

// Scroll container for virtualizer
const scrollContainerRef = ref<HTMLElement | null>(null)

// Client-side filtered list (search + group + shape)
const filteredItems = computed(() => {
  let result = materialsStore.materialItems

  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(item =>
      item.code.toLowerCase().includes(q) ||
      item.name.toLowerCase().includes(q) ||
      (item.supplier_code?.toLowerCase() || '').includes(q) ||
      (item.supplier?.toLowerCase() || '').includes(q)
    )
  }

  if (filterGroupId.value !== null) {
    result = result.filter(item => item.material_group_id === filterGroupId.value)
  }

  if (filterShape.value !== null) {
    result = result.filter(item => item.shape === filterShape.value)
  }

  return result
})

// Virtualizer — identical to PartListPanel
const virtualizer = useVirtualizer({
  get count() { return filteredItems.value.length },
  getScrollElement: () => scrollContainerRef.value,
  estimateSize: () => ROW_HEIGHT,
  overscan: 10
})

const virtualRows = computed(() => virtualizer.value.getVirtualItems())
const totalSize = computed(() => virtualizer.value.getTotalSize())

// Infinite scroll — fetch next batch when near bottom
function onScroll() {
  if (!scrollContainerRef.value || !materialsStore.hasMoreMaterialItems || materialsStore.loadingMoreMaterialItems) return
  // Only trigger when no client-side filter active (server data)
  if (searchQuery.value || filterGroupId.value !== null || filterShape.value !== null) return
  const el = scrollContainerRef.value
  const remaining = el.scrollHeight - el.scrollTop - el.clientHeight
  if (remaining < 300) {
    materialsStore.fetchMoreMaterialItems()
  }
}

// Spinner only on first load
const isLoading = computed(() => materialsStore.initialLoadingMaterialItems)

// Status label
const statusLabel = computed(() => {
  const loaded = materialsStore.materialItems.length
  const total = materialsStore.materialItemsTotal
  if (total === 0) return ''
  if (loaded >= total) return `(${total})`
  return `(${loaded}/${total})`
})

// Debounced search
watch(searchQuery, (val) => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    // client-side filter, no server call needed
  }, 150)
})

function handleRowClick(item: MaterialItem) {
  selectedItemNumber.value = item.material_number
  emit('select-item', item)
}

function handleCreate() {
  // TODO: open create modal
}

function handleImport() {
  // TODO: open import modal
}

onMounted(async () => {
  // Skip fetch if already loaded — instant re-open
  if (!materialsStore.hasMaterialItems) {
    await materialsStore.fetchMaterialItems()
  }
  // Load groups for filter dropdown (cached)
  materialsStore.loadReferenceData()
})

onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer)
  searchQuery.value = ''
  filterGroupId.value = null
  filterShape.value = null
})

defineExpose({
  setSelection(materialNumber: string | null) {
    selectedItemNumber.value = materialNumber
  }
})
</script>

<template>
  <div class="material-items-list-panel">
    <!-- Header -->
    <div class="list-header">
      <h3>Materiály <span class="count">{{ statusLabel }}</span></h3>
      <div class="header-actions">
        <button class="icon-btn icon-btn-sm" @click="handleImport" title="Import">
          <Upload :size="ICON_SIZE.STANDARD" />
        </button>
        <button class="icon-btn icon-btn-primary" @click="handleCreate" title="Nová položka">
          <Plus :size="ICON_SIZE.STANDARD" />
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters-row">
      <input
        v-model="searchQuery"
        v-select-on-focus
        type="text"
        placeholder="Hledat kód, název..."
        class="search-input"
      />
      <div class="select-wrap">
        <select v-model="filterGroupId" class="filter-select">
          <option :value="null">Vše skupiny</option>
          <option v-for="group in materialsStore.materialGroups" :key="group.id" :value="group.id">
            {{ group.name }}
          </option>
        </select>
        <span class="select-chevron">▼</span>
      </div>
      <div class="select-wrap">
        <select v-model="filterShape" class="filter-select">
          <option :value="null">Vše tvary</option>
          <option value="round_bar">Kruhová</option>
          <option value="square_bar">Čtvercová</option>
          <option value="flat_bar">Plochá</option>
          <option value="hexagonal_bar">Šestihranná</option>
          <option value="plate">Deska</option>
          <option value="tube">Trubka</option>
        </select>
        <span class="select-chevron">▼</span>
      </div>
    </div>

    <!-- Loading (first load only) -->
    <div v-if="isLoading" class="loading-container">
      <Spinner size="lg" />
    </div>

    <!-- Empty -->
    <div v-else-if="filteredItems.length === 0" class="empty-container">
      <p>Žádné materiálové položky</p>
    </div>

    <!-- Virtualized table -->
    <div
      v-else
      ref="scrollContainerRef"
      class="table-container"
      @scroll.passive="onScroll"
    >
      <!-- Sticky header -->
      <div class="vt-header">
        <div class="vt-th col-code">KÓD</div>
        <div class="vt-th col-name">Název</div>
        <div class="vt-th col-shape">Tvar</div>
        <div class="vt-th col-dim col-num">Rozměr</div>
        <div class="vt-th col-supplier">Dodavatel</div>
        <div class="vt-th col-stock col-num">Sklad kg</div>
      </div>

      <!-- Virtual scroll body -->
      <div class="vt-body" :style="{ height: `${totalSize}px` }">
        <div
          v-for="virtualRow in virtualRows"
          :key="filteredItems[virtualRow.index]?.material_number ?? virtualRow.index"
          class="vt-row"
          :class="{ selected: filteredItems[virtualRow.index]?.material_number === selectedItemNumber }"
          :style="{ height: `${virtualRow.size}px`, transform: `translateY(${virtualRow.start}px)` }"
          @click="filteredItems[virtualRow.index] && handleRowClick(filteredItems[virtualRow.index]!)"
        >
          <div class="vt-td col-code">
            <span class="code-mono">{{ filteredItems[virtualRow.index]?.code ?? '—' }}</span>
          </div>
          <div class="vt-td col-name">{{ filteredItems[virtualRow.index]?.name ?? '—' }}</div>
          <div class="vt-td col-shape">{{ filteredItems[virtualRow.index]?.shape ?? '—' }}</div>
          <div class="vt-td col-dim col-num">
            {{ filteredItems[virtualRow.index]?.diameter
              ? `⌀${filteredItems[virtualRow.index]!.diameter}`
              : filteredItems[virtualRow.index]?.width
                ? `${filteredItems[virtualRow.index]!.width}×${filteredItems[virtualRow.index]!.thickness ?? ''}`
                : '—' }}
          </div>
          <div class="vt-td col-supplier">{{ filteredItems[virtualRow.index]?.supplier ?? '—' }}</div>
          <div class="vt-td col-stock col-num">
            {{ filteredItems[virtualRow.index]?.stock_available != null
              ? filteredItems[virtualRow.index]!.stock_available
              : '—' }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.material-items-list-panel {
  display: flex;
  flex-direction: column;
  gap: var(--pad);
  height: 100%;
  overflow: hidden;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  flex-shrink: 0;
}

.list-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--t1);
}

.count {
  font-size: var(--fs);
  font-weight: 400;
  color: var(--t3);
  margin-left: 6px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filters-row {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.select-wrap {
  position: relative;
  flex: 0 0 auto;
}

.filter-select {
  padding-right: 24px;
  background-image: none;
}

.select-chevron {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  font-size: var(--fs);
  color: var(--t3);
  pointer-events: none;
}

.loading-container,

/* ── Virtualized table ── */
.table-container {
  flex: 1;
  overflow: auto;
  contain: strict;
}

.vt-header {
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--ground);
  border-bottom: 1px solid var(--b2);
}

.vt-th {
  padding: 3px 10px;
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1 1 0;
  min-width: 0;
}

.vt-body {
  position: relative;
  width: 100%;
}

.vt-row {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  display: flex;
  align-items: center;
  cursor: pointer;
  border-bottom: 1px solid var(--b1);
  transition: background-color 60ms ease;
}

.vt-row:hover  { background: var(--b1); }
.vt-row.selected { background: var(--b1); }

.vt-td {
  padding: 3px 10px;
  font-size: var(--fs);
  color: var(--t2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1 1 0;
  min-width: 0;
}

/* Column widths */
.col-code     { flex: 1.4 1 0; }
.col-name     { flex: 2.5 1 0; }
.col-shape    { flex: 1 1 0; }
.col-dim      { flex: 0.8 1 0; }
.col-supplier { flex: 1.2 1 0; }
.col-stock    { flex: 0.7 1 0; }

.col-num {
  font-family: var(--mono);
  text-align: right;
}

.code-mono {
  font-family: var(--mono);
  font-weight: 600;
  color: var(--t1);
}
</style>
