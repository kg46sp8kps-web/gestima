<script setup lang="ts">
import { Package, CheckCircle2, AlertTriangle, XCircle } from 'lucide-vue-next'
import QuoteItemRow from './QuoteItemRow.vue'
import { ICON_SIZE } from '@/config/design'

interface BatchMatch {
  batch_id: number | null
  batch_quantity: number | null
  status: 'exact' | 'lower' | 'missing'
  unit_price: number
  line_total: number
  warnings: string[]
}

interface EditableItem {
  article_number: string
  drawing_number: string | null
  name: string
  quantity: number
  notes: string | null
  part_id: number | null
  part_exists: boolean
  batch_match: BatchMatch | null
  stepFile: File | null
  pdfFile: File | null
}

interface Props {
  items: EditableItem[]
}

interface Emits {
  (e: 'file-add', index: number, file: File, type: 'step' | 'pdf'): void
  (e: 'file-remove', index: number, type: 'step' | 'pdf'): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()
</script>

<template>
  <div class="items-section">
    <h2><Package :size="ICON_SIZE.STANDARD" style="display: inline; margin-right: 8px;" /> Položky nabídky</h2>
    <div class="items-table-wrapper">
      <table class="items-table">
        <thead>
          <tr>
            <th>Artikl / Part Number</th>
            <th>Drawing Number</th>
            <th>Název</th>
            <th>Množství</th>
            <th>Výkresy</th>
            <th>Dávka</th>
            <th>Cena/ks</th>
            <th>Celkem</th>
          </tr>
        </thead>
        <tbody>
          <QuoteItemRow
            v-for="(item, idx) in items"
            :key="idx"
            :item="item"
            :index="idx"
            @file-add="(index: number, file: File, type: 'step' | 'pdf') => emit('file-add', index, file, type)"
            @file-remove="(index: number, type: 'step' | 'pdf') => emit('file-remove', index, type)"
          />
        </tbody>
      </table>

      <div class="batch-legend">
        <h4>Legenda dávek:</h4>
        <div class="legend-items">
          <span><CheckCircle2 :size="ICON_SIZE.SMALL" class="status-success" /> <strong>Exact:</strong> Přesně stejná dávka (best price)</span>
          <span><AlertTriangle :size="ICON_SIZE.SMALL" class="status-warning" /> <strong>Lower:</strong> Nejbližší nižší (konzervativní cena)</span>
          <span><XCircle :size="ICON_SIZE.SMALL" class="status-danger" /> <strong>Missing:</strong> Chybí kalkulace (nutno doplnit později)</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.items-section {
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.items-section h2 {
  margin: 0 0 var(--space-4) 0;
  font-size: var(--text-lg);
  color: var(--text-primary);
}

.items-table-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.items-table {
  width: 100%;
  border-collapse: collapse;
}

.items-table th,
.items-table td {
  padding: var(--space-2);
  text-align: left;
  border-bottom: 1px solid var(--border-default);
}

.items-table th {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  background: var(--bg-raised);
}

.items-table td {
  font-size: var(--text-sm);
  color: var(--text-body);
  vertical-align: middle;
}

.batch-legend {
  padding: var(--space-3);
  background: var(--bg-raised);
  border-radius: var(--radius-sm);
}

.batch-legend h4 {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.legend-items {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-size: var(--text-sm);
}

.legend-items span {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.status-success {
  color: var(--color-success);
}

.status-warning {
  color: var(--palette-warning);
}

.status-danger {
  color: var(--color-danger);
}
</style>
