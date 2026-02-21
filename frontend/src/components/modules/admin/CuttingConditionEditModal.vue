<script setup lang="ts">
import { ref, watch } from 'vue'
import type { PivotCell, PivotOperation, CuttingConditionUpdate } from '@/types/cutting-condition'

const props = defineProps<{
  visible: boolean
  cell: PivotCell | null
  operation: PivotOperation | null
  materialName: string
}>()

const emit = defineEmits<{
  close: []
  save: [data: CuttingConditionUpdate]
}>()

const formVc = ref<number | null>(null)
const formF = ref<number | null>(null)
const formAp = ref<number | null>(null)
const formNotes = ref<string>('')

watch(() => props.cell, (newCell) => {
  if (newCell) {
    formVc.value = newCell.Vc
    formF.value = newCell.f ?? newCell.fz
    formAp.value = newCell.Ap
    formNotes.value = newCell.notes ?? ''
  }
}, { immediate: true })

function handleSave() {
  if (!props.cell) return
  const data: CuttingConditionUpdate = {
    version: props.cell.version,
    notes: formNotes.value || null,
  }
  // Only include fields relevant to this operation
  if (props.operation?.fields.includes('Vc')) data.Vc = formVc.value
  if (props.operation?.fields.includes('f') || props.operation?.fields.includes('fz')) data.f = formF.value
  if (props.operation?.fields.includes('Ap')) data.Ap = formAp.value
  emit('save', data)
}
</script>

<template>
  <div v-if="visible" class="modal-overlay" @click.self="emit('close')">
    <div class="modal-card">
      <div class="modal-header">
        <h3>{{ materialName }} — {{ operation?.label }}</h3>
      </div>

      <div class="modal-body">
        <div v-if="operation?.fields.includes('Vc')" class="form-group">
          <label>Vc (m/min)</label>
          <input v-model.number="formVc" type="number" step="1" />
        </div>

        <div v-if="operation?.fields.includes('f') || operation?.fields.includes('fz')" class="form-group">
          <label>{{ operation?.operation_type === 'sawing' ? 'Posuv (mm/min)' : operation?.fields.includes('fz') ? 'fz (mm/zub)' : 'f (mm/ot)' }}</label>
          <input v-model.number="formF" type="number" :step="operation?.operation_type === 'sawing' ? 1 : 0.01" />
        </div>

        <div v-if="operation?.fields.includes('Ap')" class="form-group">
          <label>Ap (mm)</label>
          <input v-model.number="formAp" type="number" step="0.1" />
        </div>

        <div class="form-group">
          <label>Poznámky</label>
          <textarea v-model="formNotes" rows="3" placeholder="Volitelné poznámky..."></textarea>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn-secondary" @click="emit('close')">Zrušit</button>
        <button class="btn-primary" @click="handleSave">Uložit</button>
      </div>
    </div>
  </div>
</template>

<style scoped>

.modal-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  max-width: 400px;
  width: 90%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-default);
}

.modal-header h3 {
  margin: 0;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
}

.modal-body {
  padding: var(--space-4);
  overflow-y: auto;
  flex: 1;
}


.modal-footer {
  padding: var(--space-4);
  border-top: 1px solid var(--border-default);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
