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
    case 'estimated': return 'var(--warn)'
    case 'calibrated': return 'var(--t3)'
    case 'verified': return 'var(--ok)'
    case 'extracted': return 'var(--t3)'
    default: return 'var(--t3)'
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
  padding: var(--pad) 12px 6px;
  border-bottom: 1px solid var(--b2);
  gap: 6px;
}
.header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}
.panel-header h3 {
  font-size: var(--fs);
  font-weight: 600;
  margin: 0;
}
.count {
  font-size: var(--fs);
  color: var(--t3);
  background: var(--ground);
  padding: 2px var(--pad);
  border-radius: var(--rs);
}
.filter-bar {
  display: flex;
  gap: 6px;
  align-items: center;
}
.dropdown-wrapper {
  position: relative;
}
.dropdown-trigger {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px var(--pad);
  font-size: var(--fs);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  background: var(--surface);
  color: var(--t3);
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
  max-width: 160px;
}
.dropdown-trigger:hover {
  border-color: var(--t3);
  color: var(--t1);
}
.dropdown-trigger.active {
  border-color: var(--red);
  color: var(--red);
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
  top: calc(100% + 4px);
  left: 0;
  min-width: 140px;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  z-index: 50;
  padding: 4px 0;
}
.dropdown-option {
  display: flex;
  align-items: center;
  gap: var(--pad);
  padding: 4px 12px;
  font-size: var(--fs);
  cursor: pointer;
  transition: background 0.1s;
  color: var(--t1);
}
.dropdown-option:hover {
  background: var(--b1);
}
.dropdown-option input[type="checkbox"] {
  width: 14px;
  height: 14px;
  accent-color: var(--red);
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
  color: var(--t3);
  cursor: pointer;
  font-size: var(--fs);
  border-radius: var(--rs);
  transition: all 0.15s;
}
.btn-clear-filters:hover {
  background: var(--b1);
  color: var(--err);
}
.btn-process-all {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;
  border: 1px solid var(--b2);
  background: transparent;
  color: var(--t1);
  border-radius: var(--rs);
  cursor: pointer;
  font-size: var(--fs);
}
.btn-process-all:hover:not(:disabled) {
  background: var(--b1);
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
  padding: 6px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--b1);
  transition: background 0.1s;
}
.drawing-item:hover {
  background: var(--b1);
}
.drawing-item.selected {
  background: var(--b1);
  border-left: 3px solid var(--b3);
}
.drawing-info {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.file-icon {
  flex-shrink: 0;
  color: var(--t3);
}
.drawing-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.filename {
  font-size: var(--fs);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.size {
  font-size: var(--fs);
  color: var(--t3);
}
.drawing-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.model-badge {
  font-size: var(--fs);
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--rs);
  background: var(--ground);
  color: var(--t3);
  letter-spacing: 0.02em;
}
.model-badge.model-ft {
  background: var(--red-10);
  color: var(--red);
}
.model-badge.model-v2 {
  background: var(--ground);
  color: var(--t3);
}
.status-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs);
  font-weight: 500;
}
.btn-process {
  display: flex;
  align-items: center;
  padding: 4px;
  border: 1px solid var(--b2);
  background: transparent;
  color: var(--t1);
  border-radius: var(--rs);
  cursor: pointer;
  transition: all 0.15s;
}
.btn-process:hover {
  background: var(--red-10);
  border-color: var(--red);
  color: var(--red);
}
</style>
