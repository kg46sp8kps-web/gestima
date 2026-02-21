<script setup lang="ts">
/**
 * PartListPanel - Virtualized parts list (18k+ rows)
 *
 * Uses @tanstack/vue-virtual for DOM virtualization — only ~30 rows in DOM at any time.
 * Server-side filtering (status + search), infinite scroll for data loading.
 */
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import { usePartsStore } from '@/stores/parts'
import type { Part } from '@/types/part'
import type { LinkingGroup } from '@/stores/windows'
import type { Column } from '@/components/ui/DataTable.vue'
import { Plus, Filter } from 'lucide-vue-next'
import { PricingIcon, DrawingIcon } from '@/config/icons'
import { Layers } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import Spinner from '@/components/ui/Spinner.vue'
import ColumnChooser from '@/components/ui/ColumnChooser.vue'
import { formatNumber, formatDate } from '@/utils/formatters'
import { partStatusLabel, partStatusDotClass, partSourceLabel, partSourceDotClass } from '@/utils/partStatus'

interface Props {
  linkingGroup?: LinkingGroup
  /** When true, list rows are not clickable (e.g. while create form is open) */
  readonly?: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'select-part': [part: Part]
  'create-new': []
  'open-pricing': []
  'open-drawing': []
  'open-technology': []
}>()

const partsStore = usePartsStore()
const searchInput = ref('')
const statusFilter = ref<string>('all')
const drawingFilterActive = ref(false)
const selectedPartId = ref<number | null>(null)

// Debounce timer for search
let searchTimer: ReturnType<typeof setTimeout> | null = null

// Row height matches design-system.css --density-row-height (compact=30px)
const ROW_HEIGHT = 30

// Column definitions (server handles sort order — article_number ASC)
const defaultColumns: Column[] = [
  { key: 'article_number', label: 'ARTIKL', visible: true, format: 'text' },
  { key: 'name', label: 'Název', visible: true, format: 'text' },
  { key: 'revision', label: 'Revize', visible: true, format: 'text' },
  { key: 'customer_revision', label: 'Zák. revize', visible: true, format: 'text' },
  { key: 'drawing_number', label: 'Číslo výkresu', visible: false, format: 'text' },
  { key: 'source', label: 'Zdroj', visible: true, format: 'text' },
  { key: 'status', label: 'Status', visible: true, format: 'text' },
  { key: 'created_at', label: 'Vytvořeno', visible: true, format: 'date' }
]
const columns = ref<Column[]>(defaultColumns)
const visibleColumns = computed(() => columns.value.filter(c => c.visible !== false))

// Scroll container ref for virtualizer
const scrollContainerRef = ref<HTMLElement | null>(null)

// Virtual row count = loaded parts
const rowCount = computed(() => partsStore.parts.length)

// Virtualizer — only renders visible rows + overscan
const virtualizer = useVirtualizer({
  get count() { return rowCount.value },
  getScrollElement: () => scrollContainerRef.value,
  estimateSize: () => ROW_HEIGHT,
  overscan: 10
})

const virtualRows = computed(() => virtualizer.value.getVirtualItems())
const totalSize = computed(() => virtualizer.value.getTotalSize())

// Fetch more when scrolling near bottom
function onScroll() {
  if (!scrollContainerRef.value || !partsStore.hasMore || partsStore.loadingMore) return
  const el = scrollContainerRef.value
  const remaining = el.scrollHeight - el.scrollTop - el.clientHeight
  if (remaining < 300) {
    partsStore.fetchMore()
  }
}

// Only show spinner on first load (empty list)
const isLoading = computed(() => partsStore.initialLoading)

// Status label showing loaded/total count
const statusLabel = computed(() => {
  const loaded = partsStore.parts.length
  const total = partsStore.total
  if (total === 0) return ''
  if (loaded >= total) return `(${total})`
  return `(${loaded}/${total})`
})

// Server-side status filter
watch(statusFilter, (newStatus) => {
  const serverStatus = newStatus === 'all' ? undefined : newStatus
  partsStore.setStatusFilter(serverStatus)
  partsStore.fetchParts()
})

// Server-side search with debounce
watch(searchInput, (newVal) => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    partsStore.setSearchQuery(newVal)
    partsStore.fetchParts()
  }, 300)
})

function handleRowClick(part: Part) {
  if (props.readonly) return
  selectedPartId.value = part.id
  emit('select-part', part)
}

function handleCreate() {
  emit('create-new')
}

function toggleDrawingFilter() {
  drawingFilterActive.value = !drawingFilterActive.value
  partsStore.setDrawingFilter(drawingFilterActive.value)
  partsStore.fetchParts()
}

function handleColumnsUpdate(updatedColumns: Column[]) {
  columns.value = updatedColumns

  const visibility = updatedColumns.reduce((acc, col) => {
    acc[col.key] = col.visible ?? true
    return acc
  }, {} as Record<string, boolean>)

  const order = updatedColumns.map(col => col.key)

  localStorage.setItem('partListColumns', JSON.stringify(visibility))
  localStorage.setItem('partListColumns_order', JSON.stringify(order))
}

function getCellValue(part: Part, key: string): unknown {
  return (part as unknown as Record<string, unknown>)[key]
}

// Status badge helpers (Gestima badge-dot pattern from template.html)
// Status/source helpers — importováno z @/utils/partStatus (single source of truth)
const statusDotClass = partStatusDotClass
const statusLabel_map = partStatusLabel
const sourceDotClass = partSourceDotClass
const sourceLabel = partSourceLabel

onMounted(async () => {
  // Skip fetch if data already loaded — reopening window is instant
  if (!partsStore.hasParts) {
    await partsStore.fetchParts()
  }
})

onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer)
  // Reset all filters on close so next open starts clean
  searchInput.value = ''
  statusFilter.value = 'all'
  drawingFilterActive.value = false
  partsStore.setSearchQuery('')
  partsStore.setStatusFilter(undefined)
  partsStore.setDrawingFilter(false)
})

// Expose methods for parent
defineExpose({
  setSelection(partId: number | null) {
    selectedPartId.value = partId
  },
  async prependAndSelect(part: import('@/types/part').Part) {
    // Store already did unshift — just select and scroll to top
    selectedPartId.value = part.id
    // nextTick ensures virtualizer processed the new row before scrolling
    await nextTick()
    requestAnimationFrame(() => {
      scrollContainerRef.value?.scrollTo({ top: 0, behavior: 'instant' })
    })
  }
})
</script>

<template>
  <div class="part-list-panel">
    <!-- Header -->
    <div class="list-header">
      <h3>Díly <span class="parts-count">{{ statusLabel }}</span></h3>
      <div class="header-actions">
        <button
          class="icon-btn"
          :class="{ disabled: !selectedPartId }"
          :disabled="!selectedPartId"
          title="Ceny"
          @click="emit('open-pricing')"
        >
          <PricingIcon :size="ICON_SIZE.STANDARD" />
        </button>
        <button
          class="icon-btn"
          :class="{ disabled: !selectedPartId }"
          :disabled="!selectedPartId"
          title="Výkres"
          @click="emit('open-drawing')"
        >
          <DrawingIcon :size="ICON_SIZE.STANDARD" />
        </button>
        <button
          class="icon-btn"
          :class="{ disabled: !selectedPartId }"
          :disabled="!selectedPartId"
          title="Technologie"
          @click="emit('open-technology')"
        >
          <Layers :size="ICON_SIZE.STANDARD" />
        </button>
        <button
          class="icon-btn"
          :class="{ active: drawingFilterActive }"
          title="Pouze díly s výkresem"
          @click="toggleDrawingFilter"
        >
          <Filter :size="ICON_SIZE.STANDARD" />
        </button>
        <ColumnChooser
          :columns="columns"
          storageKey="partListColumns"
          @update:columns="handleColumnsUpdate"
        />
        <button @click="handleCreate" class="icon-btn icon-btn-primary" title="Vytvořit nový díl">
          <Plus :size="ICON_SIZE.STANDARD" />
        </button>
      </div>
    </div>

    <!-- Filters Row -->
    <div class="filters-row">
      <div class="select-wrap">
        <select v-model="statusFilter" class="status-filter">
          <option value="all">Vše</option>
          <option value="draft">Rozpracovaný</option>
          <option value="active">Aktivní</option>
          <option value="quote">Nabídka</option>
          <option value="archived">Archivovaný</option>
        </select>
        <span class="select-chevron">▼</span>
      </div>

      <input
        v-model="searchInput"
        v-select-on-focus
        type="text"
        placeholder="Hledat artikl, název..."
        class="search-input"
      />
    </div>

    <!-- Loading state (first load only) -->
    <div v-if="isLoading" class="loading-container">
      <Spinner size="lg" />
    </div>

    <!-- Empty state -->
    <div v-else-if="partsStore.parts.length === 0" class="empty-container">
      <p>Žádné díly</p>
    </div>

    <!-- Virtualized table -->
    <div
      v-else
      ref="scrollContainerRef"
      class="table-container"
      :class="{ 'table-readonly': readonly }"
      @scroll.passive="onScroll"
    >
      <!-- Sticky header row (flex-based, matches column widths) -->
      <div class="vt-header">
        <div
          v-for="col in visibleColumns"
          :key="col.key"
          class="vt-th"
          :class="[`col-${col.key}`, { 'col-num': col.format === 'number' }]"
        >
          {{ col.label }}
        </div>
      </div>

      <!-- Virtual scroll body -->
      <div
        class="vt-body"
        :style="{ height: `${totalSize}px` }"
      >
        <div
          v-for="virtualRow in virtualRows"
          :key="partsStore.parts[virtualRow.index]?.id ?? virtualRow.index"
          class="vt-row"
          :class="{ selected: partsStore.parts[virtualRow.index]?.id === selectedPartId }"
          :style="{
            height: `${virtualRow.size}px`,
            transform: `translateY(${virtualRow.start}px)`
          }"
          @click="partsStore.parts[virtualRow.index] && handleRowClick(partsStore.parts[virtualRow.index]!)"
        >
          <div
            v-for="col in visibleColumns"
            :key="col.key"
            class="vt-td"
            :class="[`col-${col.key}`, { 'col-num': col.format === 'number' }]"
          >
            <!-- article_number: mono font, bold -->
            <template v-if="col.key === 'article_number'">
              <span class="article-number">{{ getCellValue(partsStore.parts[virtualRow.index]!, col.key) || '—' }}</span>
            </template>
            <!-- status: dot + text -->
            <template v-else-if="col.key === 'status'">
              <span v-if="getCellValue(partsStore.parts[virtualRow.index]!, col.key)" class="dot-value">
                <span class="dot" :class="statusDotClass(String(getCellValue(partsStore.parts[virtualRow.index]!, col.key)))"></span>
                {{ statusLabel_map(String(getCellValue(partsStore.parts[virtualRow.index]!, col.key))) }}
              </span>
              <span v-else>—</span>
            </template>
            <!-- source: dot + text -->
            <template v-else-if="col.key === 'source'">
              <span v-if="getCellValue(partsStore.parts[virtualRow.index]!, col.key)" class="dot-value">
                <span class="dot" :class="sourceDotClass(String(getCellValue(partsStore.parts[virtualRow.index]!, col.key)))"></span>
                {{ sourceLabel(String(getCellValue(partsStore.parts[virtualRow.index]!, col.key))) }}
              </span>
              <span v-else>—</span>
            </template>
            <!-- number format -->
            <template v-else-if="col.format === 'number'">
              {{ formatNumber(getCellValue(partsStore.parts[virtualRow.index]!, col.key)) }}
            </template>
            <!-- date format -->
            <template v-else-if="col.format === 'date'">
              {{ formatDate(getCellValue(partsStore.parts[virtualRow.index]!, col.key)) }}
            </template>
            <!-- default text -->
            <template v-else>
              {{ getCellValue(partsStore.parts[virtualRow.index]!, col.key) ?? '—' }}
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.part-list-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  height: 100%;
  overflow: hidden;
  container-type: inline-size;
  container-name: part-list-container;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  flex-shrink: 0;
}

.list-header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.parts-count {
  font-size: var(--text-sm);
  font-weight: var(--font-normal);
  color: var(--text-tertiary);
  margin-left: var(--space-2);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

/* Filters — height/padding/font from design-system.css globals */
.filters-row {
  display: flex;
  gap: var(--space-2);
  flex-shrink: 0;
}

/* Select wrapper — arrow via overlay span, not background-image */
.select-wrap {
  position: relative;
  flex: 0 0 auto;
  width: 130px;
}

.status-filter,
.status-filter:focus {
  width: 100%;
  background-image: none;
  padding-right: 28px;
}

.select-chevron {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  font-size: var(--text-sm);
  color: var(--text-muted);
  pointer-events: none;
}

/* Loading & empty states */
.loading-container,

/* ── Virtualized table ── */
.table-container {
  flex: 1;
  overflow: auto;
  contain: strict;
}

.table-container.table-readonly .vt-row {
  cursor: default;
}

/* Sticky header row */
.vt-header {
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--bg-subtle);
  border-bottom: 1px solid var(--border-default);
}

.vt-th {
  padding: var(--cell-py, var(--space-3)) var(--cell-px, var(--space-4));
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  user-select: none;
  flex: 1 1 0;
  min-width: 0;
}

/* Virtual scroll body — relative container for absolute rows */
.vt-body {
  position: relative;
  width: 100%;
}

/* Each row — absolute positioned by virtualizer, flex layout for cells */
.vt-row {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  display: flex;
  align-items: center;
  cursor: pointer;
  border-bottom: 1px solid var(--border-subtle);
  transition: background-color 60ms ease;
}

.vt-row:hover {
  background: var(--hover);
}

.vt-row.selected {
  background: var(--selected);
}

/* Cell — matches template.html .data-table td */
.vt-td {
  padding: var(--cell-py, var(--space-3)) var(--cell-px, var(--space-4));
  font-size: var(--text-sm);
  color: var(--text-body);
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1 1 0;
  min-width: 0;
}

/* ── Column-specific widths ── */
.col-article_number { flex: 2 1 0; }
.col-name           { flex: 2.5 1 0; }
.col-revision       { flex: 0.6 1 0; }
.col-customer_revision { flex: 0.8 1 0; }
.col-drawing_number { flex: 1.2 1 0; }
.col-source         { flex: 0.7 1 0; }
.col-status         { flex: 1 1 0; }
.col-created_at     { flex: 1 1 0; }

/* Numeric columns — mono font, right-aligned (matches template.html .col-num) */
.col-num {
  font-family: var(--font-mono);
  text-align: right;
}

/* ── Cell content styles ── */

/* Article number: bold, mono */
.article-number {
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

/* Dot + text (inline, same font as cell) */
.dot-value {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* ── Container Queries - progressive column hiding ──
 * Strategy: aggressively hide columns so visible ones show FULL content.
 * Math: article needs ~140px, name needs ~200px, status needs ~100px.
 */

/* 700px: hide low-value columns */
@container part-list-container (max-width: 700px) {
  .col-notes,
  .col-created_at {
    display: none;
  }
}

/* 550px: keep article + name + drawing + status (4 cols, flex 5.6)
 * → article≈137px, name≈196px, drawing≈118px, status≈98px */
@container part-list-container (max-width: 550px) {
  .col-source,
  .col-length,
  .col-customer_revision,
  .col-revision {
    display: none;
  }
}

/* 450px: keep article + name + status (3 cols, flex 4.4)
 * → article≈143px, name≈204px, status≈102px */
@container part-list-container (max-width: 450px) {
  .col-drawing_number {
    display: none;
  }
}

/* 350px: article + name only (2 cols, flex 4.5)
 * → at 350px: article≈156px, name≈194px — full content */
@container part-list-container (max-width: 350px) {
  .col-status {
    display: none;
  }

  .list-header h3 {
    font-size: var(--text-sm);
  }

  .header-actions {
    gap: var(--space-1);
  }
}

@container part-list-container (max-width: 280px) {
  .list-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
