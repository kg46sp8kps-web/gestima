<script setup lang="ts">
import { CheckCircle2, AlertTriangle, XCircle, X } from 'lucide-vue-next'
import Input from '@/components/ui/Input.vue'
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
  item: EditableItem
  index: number
}

interface Emits {
  (e: 'file-add', index: number, file: File, type: 'step' | 'pdf'): void
  (e: 'file-remove', index: number, type: 'step' | 'pdf'): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

function handleItemFile(index: number, event: Event, fileType: 'step' | 'pdf') {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  emit('file-add', index, file, fileType)
}

function getBatchStatusIcon(status: string) {
  switch (status) {
    case 'exact': return CheckCircle2
    case 'lower': return AlertTriangle
    case 'missing': return XCircle
    default: return XCircle
  }
}

function getBatchStatusColor(status: string) {
  switch (status) {
    case 'exact': return 'success'
    case 'lower': return 'warning'
    case 'missing': return 'danger'
    default: return 'info'
  }
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('cs-CZ', { style: 'currency', currency: 'CZK' }).format(value)
}
</script>

<template>
  <tr class="item-row">
    <td @click.stop>
      <Input v-model="item.article_number" placeholder="Artikl / Part Number" mono class="table-input" />
      <span v-if="!item.part_exists" class="item-badge">Nový</span>
    </td>
    <td @click.stop>
      <Input :model-value="item.drawing_number || ''" @update:model-value="item.drawing_number = String($event)" placeholder="Drawing Number" mono class="table-input" />
    </td>
    <td @click.stop>
      <Input v-model="item.name" placeholder="Název dílu" class="table-input" />
    </td>
    <td class="text-right" @click.stop>
      <div class="quantity-field">
        <Input v-model.number="item.quantity" type="number" mono class="table-input quantity-input" />
        <span class="quantity-unit">ks</span>
      </div>
    </td>
    <td class="col-drawings" @click.stop>
      <div class="item-drawings">
        <label class="file-btn" :class="{ 'has-file': item.stepFile }">
          <span v-if="!item.stepFile">STEP</span>
          <span v-else class="file-name">{{ item.stepFile.name.substring(0, 8) }}...</span>
          <input type="file" accept=".step,.stp" class="hidden-input" @change="(e) => handleItemFile(index, e, 'step')" />
        </label>
        <button v-if="item.stepFile" class="remove-file-btn" @click="emit('file-remove', index, 'step')" title="Odstranit STEP">
          <X :size="12" />
        </button>

        <label class="file-btn" :class="{ 'has-file': item.pdfFile }">
          <span v-if="!item.pdfFile">PDF</span>
          <span v-else class="file-name">{{ item.pdfFile.name.substring(0, 8) }}...</span>
          <input type="file" accept=".pdf" class="hidden-input" @change="(e) => handleItemFile(index, e, 'pdf')" />
        </label>
        <button v-if="item.pdfFile" class="remove-file-btn" @click="emit('file-remove', index, 'pdf')" title="Odstranit PDF">
          <X :size="12" />
        </button>
      </div>
    </td>
    <td>
      <div v-if="item.batch_match" class="batch-status">
        <component :is="getBatchStatusIcon(item.batch_match.status)" :size="ICON_SIZE.SMALL" :class="`status-${getBatchStatusColor(item.batch_match.status)}`" />
        <span class="batch-text">
          {{ item.batch_match.status === 'exact' ? 'Přesná' : '' }}
          {{ item.batch_match.status === 'lower' ? 'Nižší' : '' }}
          {{ item.batch_match.status === 'missing' ? 'Chybí' : '' }}
          <span v-if="item.batch_match.batch_quantity">({{ item.batch_match.batch_quantity }} ks)</span>
        </span>
      </div>
      <div v-else class="batch-status">
        <XCircle :size="ICON_SIZE.SMALL" class="status-danger" />
        <span class="batch-text">Chybí</span>
      </div>
    </td>
    <td class="text-right">{{ item.batch_match ? formatCurrency(item.batch_match.unit_price) : '-' }}</td>
    <td class="text-right"><strong>{{ item.batch_match ? formatCurrency(item.batch_match.line_total) : '-' }}</strong></td>
  </tr>
</template>

<style scoped>
.item-row {
  transition: background var(--transition-fast);
}

.item-row:hover {
  background: var(--state-hover);
}

.text-right {
  text-align: right;
}

.table-input {
  font-size: var(--text-sm);
}

.table-input :deep(.input) {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-sm);
  min-height: 32px;
}

.quantity-field {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  justify-content: flex-end;
}

.quantity-input {
  max-width: 80px;
}

.quantity-input :deep(.input) {
  text-align: right;
}

.quantity-unit {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

.item-badge {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  margin-left: var(--space-1);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  background: var(--palette-warning-faint);
  color: var(--palette-warning);
}

.batch-status {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.batch-text {
  font-size: var(--text-sm);
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

.col-drawings {
  width: 180px;
  min-width: 180px;
}

.item-drawings {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  flex-wrap: wrap;
}

.file-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 50px;
  padding: var(--space-1) var(--space-2);
  background: var(--bg-muted);
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  transition: var(--transition-fast);
  white-space: nowrap;
}

.file-btn:hover {
  border-color: var(--palette-primary);
  color: var(--palette-primary);
  background: var(--state-hover);
}

.file-btn.has-file {
  background: rgba(34, 197, 94, 0.1);
  border-color: var(--color-success);
  border-style: solid;
  color: var(--color-success);
}

.file-name {
  font-size: var(--text-xs);
  max-width: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hidden-input {
  display: none;
}

.remove-file-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  background: var(--color-danger);
  border: none;
  border-radius: 50%;
  cursor: pointer;
  color: white;
  transition: var(--transition-fast);
}

.remove-file-btn:hover {
  background: var(--palette-danger-hover);
}
</style>
