<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useBatchesStore } from '@/stores/batches'
import DataTable from '@/components/ui/DataTable.vue'
import type { Column } from '@/components/ui/DataTable.vue'

const router = useRouter()
const batchesStore = useBatchesStore()

const columns: Column[] = [
  { key: 'name', label: 'Název sady', sortable: true },
  { key: 'status', label: 'Stav', sortable: true, width: '120px' },
  { key: 'batch_count', label: 'Počet dávek', sortable: true, width: '120px' },
  { key: 'created_at', label: 'Vytvořeno', format: 'date', sortable: true, width: '150px' }
]

function handleRowClick(set: Record<string, unknown>) {
  router.push({ name: 'batch-set-detail', params: { setId: String(set.id) } })
}

onMounted(() => {
  batchesStore.loadBatchSets()
})
</script>

<template>
  <div class="batch-sets-list-view">
    <header class="page-header">
      <h1 class="page-title">Cenové sady</h1>
    </header>

    <div class="page-content">
      <DataTable
        :data="batchesStore.batchSets"
        :columns="columns"
        :loading="batchesStore.loading"
        :row-clickable="true"
        @row-click="handleRowClick"
      />
    </div>
  </div>
</template>

<style scoped>
.batch-sets-list-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-default);
}

.page-header {
  padding: var(--space-6);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
}

.page-title {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
}

.page-content {
  flex: 1;
  overflow: hidden;
  padding: var(--space-6);
}
</style>
