<script setup lang="ts">
/**
 * TimeVision - Drawing List Panel (LEFT)
 */
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useTimeVisionStore } from '@/stores/timeVision'
import { FileText, Loader, CheckCircle, Clock, Zap, RefreshCw, Filter, ChevronDown } from 'lucide-vue-next'

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
onBeforeUnmount(() => document.removeEventListener('click', handleClickOutside))

/** Extract a unique model key from ai_model string for filtering/grouping */
function getModelKey(aiProvider: string | null, aiModel: string | null): string {
  if (!aiProvider) return 'none'
  if (aiProvider === 'openai_ft') {
    const match = aiModel?.match(/gestima-(v\d+)/)
    return match ? `ft_${match[1]}` : 'ft'
  }
  return 'base'
}

/** Human-readable label for a model key */
function modelKeyLabel(key: string): string {
  if (key === 'base') return '4o'
  if (key.startsWith('ft_')) return `FT ${key.slice(3)}` // ft_v1 → FT v1
  if (key === 'ft') return 'FT'
  return key
}

const modelOptions = computed(() => {
  const keys = new Set<string>()
  for (const d of store.drawings) {
    if (d.ai_provider) keys.add(getModelKey(d.ai_provider, d.ai_model))
  }
  // Sort: base first, then FT versions ascending
  return [...keys].sort((a, b) => {
    if (a === 'base') return -1
    if (b === 'base') return 1
    return a.localeCompare(b)
  }).map(key => ({ value: key, label: modelKeyLabel(key) }))
})

/** Get drawing status key (maps null/pending/extracted → 'new') */
function drawingStatusKey(status: string | null): string {
  if (!status || status === 'pending' || status === 'extracted') return 'new'
  return status
}

const sortedDrawings = computed(() => {
  let filtered = store.drawings
  // Status filter (multi-select, empty = show all)
  if (activeStatuses.value.size > 0) {
    filtered = filtered.filter(d => activeStatuses.value.has(drawingStatusKey(d.status)))
  }
  // Model filter (multi-select, empty = show all)
  if (activeModels.value.size > 0) {
    filtered = filtered.filter(d => activeModels.value.has(getModelKey(d.ai_provider, d.ai_model)))
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

function getModelLabel(aiProvider: string | null, aiModel: string | null): string | null {
  if (!aiProvider) return null
  if (aiProvider === 'openai_ft') {
    // Extract version from model string like "ft:gpt-4o-...:gestima-v1:..."
    const match = aiModel?.match(/gestima-(v\d+)/)
    return match ? `FT ${match[1]}` : 'FT'
  }
  if (aiProvider === 'openai') return '4o'
  return aiProvider
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
          <RefreshCw :size="14" />
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
            <Filter :size="11" />
            <span class="dropdown-label">{{ statusSummary }}</span>
            <ChevronDown :size="11" class="dropdown-arrow" :class="{ open: openDropdown === 'status' }" />
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
            <ChevronDown :size="11" class="dropdown-arrow" :class="{ open: openDropdown === 'model' }" />
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
          <FileText :size="16" class="file-icon" />
          <div class="drawing-meta">
            <span class="filename">{{ drawing.filename }}</span>
            <span class="size">{{ formatSize(drawing.size_bytes) }}</span>
          </div>
        </div>

        <div class="drawing-actions">
          <span
            v-if="getModelLabel(drawing.ai_provider, drawing.ai_model)"
            class="model-badge"
            :class="{ 'model-ft': drawing.ai_provider === 'openai_ft' }"
            :title="drawing.ai_model ?? drawing.ai_provider ?? ''"
          >{{ getModelLabel(drawing.ai_provider, drawing.ai_model) }}</span>

          <span
            v-if="drawing.status"
            class="status-badge"
            :style="{ color: getStatusColor(drawing.status) }"
          >
            <CheckCircle v-if="drawing.status === 'verified'" :size="14" />
            <Clock v-else-if="drawing.status === 'estimated' || drawing.status === 'calibrated'" :size="14" />
            {{ getStatusLabel(drawing.status) }}
          </span>

          <button
            v-if="!store.openaiProcessing"
            class="btn-process"
            title="Zpracovat AI odhadem"
            @click.stop="emit('process', drawing.filename)"
          >
            <Zap :size="14" />
          </button>
          <Loader
            v-else
            :size="14"
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
  padding: 2px 8px;
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
  gap: 4px;
  padding: 3px 8px;
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
  top: calc(100% + 4px);
  left: 0;
  min-width: 140px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  z-index: 50;
  padding: 4px 0;
}
.dropdown-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 12px;
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
  font-size: 11px;
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
  font-size: 10px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: var(--radius-sm);
  background: var(--bg-subtle);
  color: var(--text-muted);
  letter-spacing: 0.02em;
}
.model-badge.model-ft {
  background: rgba(var(--color-primary-rgb, 220 38 38), 0.1);
  color: var(--color-primary);
}
.status-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  font-weight: 500;
}
.btn-process {
  display: flex;
  align-items: center;
  padding: 4px;
  border: none;
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: opacity 0.15s;
}
.btn-process:hover {
  opacity: 0.8;
}
.spinner {
  animation: spin 1s linear infinite;
  color: var(--color-primary);
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.empty-state {
  padding: var(--space-8);
  text-align: center;
  color: var(--text-muted);
}
</style>
