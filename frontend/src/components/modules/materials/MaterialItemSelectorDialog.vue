<script setup lang="ts">
/**
 * Material Item Selector Dialog
 *
 * Allows selecting material item from catalog for use in PartMaterialModule.
 * Quick selector with search and filters.
 */

import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { X, Search, Package } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import type { MaterialItem, MaterialGroup, StockShape } from '@/types/material'
import { getMaterialItems, getMaterialGroups } from '@/api/materials'

interface Props {
  visible?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  visible: false
})

const emit = defineEmits<{
  'update:visible': [value: boolean]
  select: [item: MaterialItem]
  close: []
}>()

// State
const items = ref<MaterialItem[]>([])
const groups = ref<MaterialGroup[]>([])
const loading = ref(false)
const searchQuery = ref('')
const filterGroupId = ref<number | null>(null)
const filterShape = ref<StockShape | null>(null)

// Computed
const filteredItems = computed(() => {
  let result = items.value

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(item =>
      item.code.toLowerCase().includes(query) ||
      item.name.toLowerCase().includes(query) ||
      (item.supplier_code?.toLowerCase() || '').includes(query)
    )
  }

  if (filterGroupId.value) {
    result = result.filter(item => item.material_group_id === filterGroupId.value)
  }

  if (filterShape.value) {
    result = result.filter(item => item.shape === filterShape.value)
  }

  return result.slice(0, 50) // Limit to 50 items for performance
})

// Methods
async function loadData() {
  loading.value = true
  try {
    const [itemsData, groupsData] = await Promise.all([
      getMaterialItems(),
      getMaterialGroups()
    ])
    items.value = itemsData
    groups.value = groupsData
  } catch (error) {
    console.error('Failed to load data:', error)
  } finally {
    loading.value = false
  }
}

function handleSelect(item: MaterialItem) {
  emit('select', item)
  handleClose()
}

function handleClose() {
  emit('update:visible', false)
  emit('close')
}

// Keyboard handler
const handleKeydown = (e: KeyboardEvent) => {
  if (!props.visible) return
  if (e.key === 'Escape') {
    handleClose()
  }
}

// Lifecycle
onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  if (props.visible) {
    loadData()
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

// Watch for visibility changes to load data
watch(() => props.visible, (visible) => {
  if (visible) {
    loadData()
  }
})
</script>

<template>
  <div v-if="visible" class="dialog-overlay" @click="handleClose">
    <div class="dialog-content" @click.stop>
      <!-- Header -->
      <div class="dialog-header">
        <h2 class="dialog-title">Vybrat z katalogu</h2>
        <button class="close-btn" @click="handleClose">
          <X :size="ICON_SIZE.STANDARD" />
        </button>
      </div>

      <!-- Search & Filters -->
      <div class="dialog-filters">
        <div class="search-box">
          <Search :size="ICON_SIZE.SMALL" class="search-icon" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Hledat kód, název, supplier code..."
            class="search-input"
            autofocus
          />
        </div>

        <div class="filters-row">
          <select v-model="filterGroupId" class="filter-select">
            <option :value="null">Všechny skupiny</option>
            <option v-for="group in groups" :key="group.id" :value="group.id">
              {{ group.name }}
            </option>
          </select>

          <select v-model="filterShape" class="filter-select">
            <option :value="null">Všechny tvary</option>
            <option value="round_bar">Kruhová tyč</option>
            <option value="square_bar">Čtvercová tyč</option>
            <option value="flat_bar">Plochá tyč</option>
            <option value="hexagonal_bar">Šestihranná tyč</option>
            <option value="plate">Deska/Plech</option>
            <option value="tube">Trubka</option>
          </select>
        </div>
      </div>

      <!-- Items List -->
      <div class="dialog-body">
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>Načítám katalog...</p>
        </div>

        <div v-else-if="filteredItems.length === 0" class="empty-state">
          <Package :size="ICON_SIZE.HERO" />
          <p>Žádné položky nenalezeny</p>
        </div>

        <div v-else class="items-grid">
          <button
            v-for="item in filteredItems"
            :key="item.material_number"
            class="item-card"
            @click="handleSelect(item)"
          >
            <div class="item-code">{{ item.code }}</div>
            <div class="item-name">{{ item.name }}</div>
            <div class="item-meta">
              <span class="meta-tag">{{ item.shape }}</span>
              <span v-if="item.supplier" class="meta-supplier">{{ item.supplier }}</span>
            </div>
          </button>
        </div>
      </div>

      <!-- Footer -->
      <div class="dialog-footer">
        <button class="icon-btn icon-btn-cancel" @click="handleClose" title="Zavrit (Escape)">
          <X :size="ICON_SIZE.STANDARD" />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* === OVERLAY === */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog-content {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

/* === HEADER === */
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-default);
}

.dialog-title {
  font-size: var(--text-lg);
  font-weight: 600;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-secondary);
  padding: var(--space-1);
  border-radius: var(--radius-sm);
  transition: all 0.15s;
}

.close-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

/* === FILTERS === */
.dialog-filters {
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.search-box {
  position: relative;
}

.search-icon {
  position: absolute;
  left: var(--space-3);
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-secondary);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: var(--space-2) var(--space-3) var(--space-2) var(--space-9);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}

.search-input:focus {
  outline: none;
  border-color: var(--border-focus);
}

.filters-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
}

.filter-select {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}

/* === BODY === */
.dialog-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
}

.items-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: var(--space-3);
}

.item-card {
  padding: var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
}

.item-card:hover {
  border-color: var(--primary-500);
  background: var(--primary-50);
  transform: translateY(-2px);
}

.item-code {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-1);
}

.item-name {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-2);
}

.item-meta {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.meta-tag {
  font-size: var(--text-xs);
  padding: var(--space-0\.5) var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
}

.meta-supplier {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

/* === STATES === */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-8);
  color: var(--text-secondary);
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-default);
  border-top-color: var(--primary-500);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* === FOOTER === */
.dialog-footer {
  padding: var(--space-4);
  border-top: 1px solid var(--border-default);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

/* === ICON BUTTONS === */
.icon-btn {
  width: 40px;
  height: 40px;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  transition: all 0.15s;
}

.icon-btn:hover {
  background: var(--bg-hover);
}

.icon-btn:focus-visible {
  outline: 2px solid var(--state-focus-border);
  outline-offset: 2px;
}

.icon-btn-cancel {
  color: var(--text-secondary);
}

.icon-btn-cancel:hover {
  background: rgba(148, 163, 184, 0.1);
}
</style>
