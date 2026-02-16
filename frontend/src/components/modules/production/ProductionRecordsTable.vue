<script setup lang="ts">
/**
 * Production Records Table - Display production history records
 */
import { computed } from 'vue'
import { Trash2 } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import type { ProductionRecord } from '@/types/productionRecord'

interface Props {
  records: ProductionRecord[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'delete', id: number): void
}>()

const sortedRecords = computed(() => {
  return [...props.records].sort((a, b) => {
    const dateA = a.production_date ? new Date(a.production_date).getTime() : 0
    const dateB = b.production_date ? new Date(b.production_date).getTime() : 0
    return dateB - dateA
  })
})

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  const date = new Date(dateStr)
  return date.toLocaleDateString('cs-CZ')
}

function handleDelete(id: number) {
  emit('delete', id)
}
</script>

<template>
  <div class="records-table">
    <div class="table-header">
      <div class="col-date">Datum</div>
      <div class="col-order">Příkaz</div>
      <div class="col-batch">Dávka</div>
      <div class="col-op">OP</div>
      <div class="col-wc">Pracoviště</div>
      <div class="col-time">Plán</div>
      <div class="col-time">Skutečnost</div>
      <div class="col-action"></div>
    </div>
    <div class="table-body">
      <div v-for="record in sortedRecords" :key="record.id" class="table-row">
        <div class="col-date">{{ formatDate(record.production_date) }}</div>
        <div class="col-order">{{ record.infor_order_number ?? '—' }}</div>
        <div class="col-batch">{{ record.batch_quantity ?? '—' }}</div>
        <div class="col-op">{{ record.operation_seq ?? '—' }}</div>
        <div class="col-wc">{{ record.work_center_name ?? '—' }}</div>
        <div class="col-time">{{ record.planned_time_min?.toFixed(1) ?? '—' }}</div>
        <div class="col-time highlight">{{ record.actual_time_min?.toFixed(1) ?? '—' }}</div>
        <div class="col-action">
          <button
            class="btn-icon"
            title="Smazat"
            @click="handleDelete(record.id)"
          >
            <Trash2 :size="ICON_SIZE.SMALL" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.records-table { margin-bottom: var(--space-3); }
.table-header, .table-row {
  display: grid;
  grid-template-columns: 90px 100px 60px 40px 1fr 60px 80px 32px;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-xs);
}
.table-header {
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  border-bottom: 1px solid var(--border-default);
  padding-bottom: var(--space-2);
}
.table-row {
  border-bottom: 1px solid var(--border-default);
  color: var(--text-secondary);
}
.table-row:hover { background: var(--bg-raised); }
.col-time { font-family: 'Space Mono', monospace; text-align: right; }
.col-time.highlight { font-weight: 600; color: var(--text-primary); }
.col-action { text-align: right; }
.btn-icon {
  background: transparent;
  border: none;
  padding: var(--space-1);
  cursor: pointer;
  color: var(--text-tertiary);
  border-radius: var(--radius-sm);
}
.btn-icon:hover { color: var(--color-brand); background: rgba(153, 27, 27, 0.1); }
</style>
