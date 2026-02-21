<script setup lang="ts">
/**
 * TimeVision - Drawing List Panel (LEFT)
 */
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useTimeVisionStore } from '@/stores/timeVision'
import { FileText, Loader, CheckCircle, Clock, Zap, RefreshCw, Filter, ChevronDown } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  selectedFilename: string | null
}
const props = defineProps<Props>()

const emit = defineEmits<{
  select: [filename: string]
  process: [filename: string]
  processAll: []
}>()

const store = useTimeVisionStore()

const activeStatuses = ref<Set<string>>(new Set())
const activeModels = ref<Set<string>>(new Set())
const openDropdown = ref<'status' | 'model' | null>(null)
const filterBarRef = ref<HTMLElement | null>(null)

const statusOptions = [
  { value: 'estimated', label: 'Odhadnuto' },
  { value: 'calibrated', label: 'Kalibrováno' },
  { value: 'verified', label: 'Ověřeno' },
  { value: 'new', label: 'Nový' },
]

function toggleStatus(value: string) {
  const s = activeStatuses.value
  if (s.has(value)) { s.delete(value) } else { s.add(value) }
  activeStatuses.value = new Set(s)
}

function toggleModel(value: string) {
  const s = activeModels.value
  if (s.has(value)) { s.delete(value) } else { s.add(value) }
  activeModels.value = new Set(s)
}

function toggleDropdown(which: 'status' | 'model') {
  openDropdown.value = openDropdown.value === which ? null : which
}

function handleClickOutside(e: MouseEvent) {
  if (openDropdown.value && filterBarRef.value && !filterBarRef.value.contains(e.target as Node)) {
    openDropdown.value = null
  }
}

const statusSummary = computed(() => {
  if (activeStatuses.value.size === 0) return 'Status'
  const labels = statusOptions.filter(o => activeStatuses.value.has(o.value)).map(o => o.label)
  return labels.join(', ')
})

const modelSummary = computed(() => {
  if (activeModels.value.size === 0) return 'Model'
  const labels = modelOptions.value.filter(o => activeModels.value.has(o.value)).map(o => o.label)
  return labels.join(', ')
})

const hasActiveFilters = computed(() => activeStatuses.value.size > 0 || activeModels.value.size > 0)

function clearFilters() {
  activeStatuses.value = new Set()
  activeModels.value = new Set()
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
  clearFilters()
  openDropdown.value = null
})

/** Model filter key based on which model versions a drawing has */
function getModelKeys(drawing: typeof store.drawings[0]): string[] {
  const keys: string[] = []
  if (drawing.v1) {
    if (drawing.v1.ai_provider === 'openai_ft') keys.push('ft_v1')
    else keys.push('v1')
  }
  if (drawing.v2) keys.push('v2')
  return keys
}

const modelOptions = computed(() => {
  const keys = new Set<string>()
  for (const d of store.drawings) {
    for (const k of getModelKeys(d)) keys.add(k)
  }
  return [...keys].sort().map(key => ({
    value: key,
    label: key === 'ft_v1' ? 'FT v1' : key === 'v1' ? 'V1 base' : 'V2 features',
  }))
})

/** Get drawing status key (maps null/pending/extracted → 'new') */
function drawingStatusKey(status: string | null): string {
  if (!status || status === 'pending' || status === 'extracted') return 'new'
  return status
}

const sortedDrawings = computed(() => {
  let filtered = store.drawings
  // Status filter (multi-select, empty = show all) — match if ANY model has the status
  if (activeStatuses.value.size > 0) {
    filtered = filtered.filter(d => {
      const statuses = [d.v1?.status, d.v2?.status, d.status].filter((s): s is string => !!s).map(drawingStatusKey)
      return statuses.some(s => activeStatuses.value.has(s))
    })
  }
  // Model filter (multi-select, empty = show all)
  if (activeModels.value.size > 0) {
    filtered = filtered.filter(d => getModelKeys(d).some(k => activeModels.value.has(k)))
  }
  return [...filtered].sort((a, b) => a.filename.localeCompare(b.filename))
})

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function getStatusColor(status: string | null): string {
  switch (status) {
    case 'estimated': return 'var(--color-warning)'
    case 'calibrated': return 'var(--color-info)'
    case 'verified': return 'var(--color-success)'
    case 'extracted': return 'var(--color-info)'
    default: return 'var(--text-muted)'
  }
}

function getStatusLabel(status: string | null): string {
  switch (status) {
    case 'estimated': return 'Odhadnuto'
    case 'calibrated': return 'Kalibrováno'
    case 'verified': return 'Ověřeno'
    case 'extracted': return 'Extrahováno'
    case 'pending': return 'Čeká'
    default: return 'Nový'
  }
}

</script>

<template>
  <div class="drawing-list-panel">
    <div class="panel-header">
      <div class="header-top">
        <div class="header-left">
          <h3>Výkresy</h3>
          <span class="count">{{ sortedDrawings.length }}/{{ store.drawings.length }}</span>
        </div>
        <button
          class="btn-process-all"
          :disabled="store.openaiProcessing || store.drawings.length === 0"
          @click="emit('processAll')"
          title="Odhadnout nové výkresy (bez OpenAI odhadu)"
        >
          <RefreshCw :size="ICON_SIZE.SMALL" />
        </button>
      </div>
      <div ref="filterBarRef" class="filter-bar">
        <!-- Status dropdown -->
        <div class="dropdown-wrapper">
          <button
            class="dropdown-trigger"
            :class="{ active: activeStatuses.size > 0 }"
            @click.stop="toggleDropdown('status')"
          >
            <Filter :size="ICON_SIZE.SMALL" />
            <span class="dropdown-label">{{ statusSummary }}</span>
            <ChevronDown :size="ICON_SIZE.SMALL" class="dropdown-arrow" :class="{ open: openDropdown === 'status' }" />
          </button>
          <div v-if="openDropdown === 'status'" class="dropdown-panel" @click.stop>
            <label
              v-for="opt in statusOptions"
              :key="opt.value"
              class="dropdown-option"
            >
              <input
                type="checkbox"
                :checked="activeStatuses.has(opt.value)"
                @change="toggleStatus(opt.value)"
              />
              <span>{{ opt.label }}</span>
            </label>
          </div>
        </div>

        <!-- Model dropdown -->
        <div v-if="modelOptions.length > 0" class="dropdown-wrapper">
          <button
            class="dropdown-trigger"
            :class="{ active: activeModels.size > 0 }"
            @click.stop="toggleDropdown('model')"
          >
            <span class="dropdown-label">{{ modelSummary }}</span>
            <ChevronDown :size="ICON_SIZE.SMALL" class="dropdown-arrow" :class="{ open: openDropdown === 'model' }" />
          </button>
          <div v-if="openDropdown === 'model'" class="dropdown-panel" @click.stop>
            <label
              v-for="opt in modelOptions"
              :key="opt.value"
              class="dropdown-option"
            >
              <input
                type="checkbox"
                :checked="activeModels.has(opt.value)"
                @change="toggleModel(opt.value)"
              />
              <span>{{ opt.label }}</span>
            </label>
          </div>
        </div>

        <!-- Clear all -->
        <button
          v-if="hasActiveFilters"
          class="btn-clear-filters"
          @click="clearFilters"
          title="Zrušit filtry"
        >✕</button>
      </div>
    </div>

    <div class="drawing-list">
      <div
        v-for="drawing in sortedDrawings"
        :key="drawing.filename"
        class="drawing-item"
        :class="{ selected: drawing.filename === selectedFilename }"
        @click="emit('select', drawing.filename)"
      >
        <div class="drawing-info">
          <FileText :size="ICON_SIZE.STANDARD" class="file-icon" />
          <div class="drawing-meta">
            <span class="filename">{{ drawing.filename }}</span>
            <span class="size">{{ formatSize(drawing.size_bytes) }}</span>
          </div>
        </div>

        <div class="drawing-actions">
          <!-- V1 badge -->
          <span
            v-if="drawing.v1"
            class="model-badge"
            :class="{ 'model-ft': drawing.v1.ai_provider === 'openai_ft' }"
            :title="'V1: ' + getStatusLabel(drawing.v1.status)"
          >FT v1</span>

          <!-- V1 status -->
          <span
            v-if="drawing.v1?.status"
            class="status-badge"
            :style="{ color: getStatusColor(drawing.v1.status) }"
          >{{ getStatusLabel(drawing.v1.status) }}</span>

          <!-- V2 badge -->
          <span
            v-if="drawing.v2"
            class="model-badge model-v2"
            :title="'V2: ' + getStatusLabel(drawing.v2.status)"
          >FT v2</span>

          <button
            v-if="!store.openaiProcessing"
            class="btn-process"
            title="Zpracovat AI odhadem"
            @click.stop="emit('process', drawing.filename)"
          >
            <Zap :size="ICON_SIZE.SMALL" />
          </button>
          <Loader
            v-else
            :size="ICON_SIZE.SMALL"
            class="spinner"
          />
        </div>
      </div>

      <div v-if="store.drawings.length === 0" class="empty-state">
        <p>Žádné výkresy v uploads/drawings</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.drawing-list-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.panel-header {
  display: flex;
  flex-direction: column;
  padding: var(--space-3) var(--space-4) var(--space-2);
  border-bottom: 1px solid var(--border-default);
  gap: var(--space-2);
}
.header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.panel-header h3 {
  font-size: var(--text-base);
  font-weight: 600;
  margin: 0;
}
.count {
  font-size: var(--text-xs);
  color: var(--text-muted);
  background: var(--bg-subtle);
  padding: var(--space-0\.5) var(--space-3);
  border-radius: var(--radius-sm);
}
.filter-bar {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}
.dropdown-wrapper {
  position: relative;
}
.dropdown-trigger {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-0\.5) var(--space-3);
  font-size: var(--text-xs);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
  max-width: 160px;
}
.dropdown-trigger:hover {
  border-color: var(--text-secondary);
  color: var(--text-primary);
}
.dropdown-trigger.active {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.dropdown-label {
  overflow: hidden;
  text-overflow: ellipsis;
}
.dropdown-arrow {
  flex-shrink: 0;
  transition: transform 0.15s;
}
.dropdown-arrow.open {
  transform: rotate(180deg);
}
.dropdown-panel {
  position: absolute;
  top: calc(100% + var(--space-1));
  left: 0;
  min-width: 140px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  z-index: 50;
  padding: var(--space-1) 0;
}
.dropdown-option {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-1) var(--space-4);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: background 0.1s;
  color: var(--text-primary);
}
.dropdown-option:hover {
  background: var(--state-hover);
}
.dropdown-option input[type="checkbox"] {
  width: 14px;
  height: 14px;
  accent-color: var(--color-primary);
  cursor: pointer;
  margin: 0;
}
.btn-clear-filters {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: var(--text-xs);
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}
.btn-clear-filters:hover {
  background: var(--state-hover);
  color: var(--color-danger);
}
.btn-process-all {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--border-default);
  background: transparent;
  color: var(--text-primary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: var(--text-xs);
}
.btn-process-all:hover:not(:disabled) {
  background: var(--state-hover);
}
.btn-process-all:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.drawing-list {
  flex: 1;
  overflow-y: auto;
}
.drawing-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-4);
  cursor: pointer;
  border-bottom: 1px solid var(--border-subtle);
  transition: background 0.1s;
}
.drawing-item:hover {
  background: var(--state-hover);
}
.drawing-item.selected {
  background: var(--state-selected);
  border-left: 3px solid var(--color-primary);
}
.drawing-info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}
.file-icon {
  flex-shrink: 0;
  color: var(--text-muted);
}
.drawing-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.filename {
  font-size: var(--text-sm);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.size {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
.drawing-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}
.model-badge {
  font-size: var(--text-2xs);
  font-weight: 600;
  padding: var(--space-px) var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--bg-subtle);
  color: var(--text-muted);
  letter-spacing: 0.02em;
}
.model-badge.model-ft {
  background: rgba(var(--color-primary-rgb, 220 38 38), 0.1);
  color: var(--color-primary);
}
.model-badge.model-v2 {
  background: var(--bg-subtle);
  color: var(--text-secondary);
}
.status-badge {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  font-weight: 500;
}
.btn-process {
  display: flex;
  align-items: center;
  padding: var(--space-1);
  border: 1px solid var(--border-default);
  background: transparent;
  color: var(--text-primary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s;
}
.btn-process:hover {
  background: var(--brand-subtle, rgba(153, 27, 27, 0.1));
  border-color: var(--color-brand, #991b1b);
  color: var(--color-brand, #991b1b);
}
</style>
