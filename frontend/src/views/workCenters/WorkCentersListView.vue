<script setup lang="ts">
/**
 * Work Centers List View
 * Seznam všech pracovišť s filtrováním a vyhledáváním
 */

import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOperationsStore } from '@/stores/operations'
import { useUiStore } from '@/stores/ui'
import DataTable from '@/components/ui/DataTable.vue'
import type { Column } from '@/components/ui/DataTable.vue'

const router = useRouter()
const operationsStore = useOperationsStore()
const uiStore = useUiStore()

// State
const searchQuery = ref('')
const typeFilter = ref<string | null>(null)
const includeInactive = ref(false)

// Computed
const loading = computed(() => operationsStore.loading)
const workCenters = computed(() => operationsStore.workCenters)

// DataTable columns
const columns: Column[] = [
  { key: 'work_center_number', label: 'Číslo', sortable: true, width: '120px' },
  { key: 'name', label: 'Název', sortable: true },
  { key: 'work_center_type', label: 'Typ', sortable: true, width: '150px' },
  { key: 'hourly_rate_total', label: 'Hodinová sazba', format: 'currency', width: '150px' },
  { key: 'is_active', label: 'Aktivní', format: 'boolean', width: '100px' }
]

// Methods
async function loadWorkCenters() {
  await operationsStore.loadWorkCenters()
}

function handleRowClick(wc: Record<string, unknown>) {
  router.push({
    name: 'work-center-edit',
    params: { workCenterNumber: String(wc.work_center_number) }
  })
}

function handleCreate() {
  router.push({ name: 'work-center-create' })
}

onMounted(() => {
  loadWorkCenters()
})
</script>

<template>
  <div class="work-centers-list-view">
    <!-- Page header -->
    <header class="page-header">
      <div class="header-content">
        <h1 class="page-title">Pracoviště</h1>
        <p class="page-subtitle">Správa pracovišť a jejich sazeb</p>
      </div>

      <div class="header-actions">
        <button class="btn btn-primary" @click="handleCreate">
          + Nové pracoviště
        </button>
      </div>
    </header>

    <!-- Filters -->
    <div class="page-filters">
      <input
        v-model="searchQuery"
        type="text"
        class="search-input"
        placeholder="Hledat podle čísla nebo názvu..."
      />

      <label class="checkbox-label">
        <input v-model="includeInactive" type="checkbox" />
        Zobrazit neaktivní
      </label>
    </div>

    <!-- Content -->
    <div class="page-content">
      <DataTable
        :data="workCenters"
        :columns="columns"
        :loading="loading"
        :row-clickable="true"
        empty-text="Žádná pracoviště k zobrazení"
        @row-click="handleRowClick"
      />
    </div>
  </div>
</template>

<style scoped>
.work-centers-list-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-default);
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: var(--space-6);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
}

.header-content {
  flex: 1;
}

.page-title {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.page-subtitle {
  margin: var(--space-1) 0 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.header-actions {
  display: flex;
  gap: var(--space-3);
}

.page-filters {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-6);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
}

.search-input {
  flex: 1;
  max-width: 400px;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-input);
  color: var(--text-primary);
}

.search-input:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-primary);
  cursor: pointer;
}

.page-content {
  flex: 1;
  overflow: hidden;
  padding: var(--space-6);
}

</style>
