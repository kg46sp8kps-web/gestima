<script setup lang="ts">
/**
 * Production Record Form - Inline form for adding production records
 */
import { ref } from 'vue'
import { Plus } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface NewRecord {
  production_date: string
  batch_quantity: number | null
  operation_seq: number | null
  planned_time_min: number | null
  actual_time_min: number | null
  infor_order_number: string
  notes: string
}

const emit = defineEmits<{
  (e: 'submit', record: NewRecord): void
  (e: 'cancel'): void
}>()

const newRecord = ref<NewRecord>({
  production_date: new Date().toISOString().split('T')[0] as string,
  batch_quantity: null,
  operation_seq: null,
  planned_time_min: null,
  actual_time_min: null,
  infor_order_number: '',
  notes: ''
})

function handleSubmit() {
  emit('submit', { ...newRecord.value })
}

function handleCancel() {
  emit('cancel')
}
</script>

<template>
  <div class="add-form">
    <div class="form-row">
      <div class="form-field">
        <label>Datum</label>
        <input v-model="newRecord.production_date" type="date" class="input-sm" />
      </div>
      <div class="form-field">
        <label>Příkaz</label>
        <input v-model="newRecord.infor_order_number" type="text" class="input-sm" placeholder="Číslo příkazu" />
      </div>
    </div>
    <div class="form-row">
      <div class="form-field">
        <label>Dávka (ks)</label>
        <input v-model.number="newRecord.batch_quantity" type="number" class="input-sm" placeholder="Počet ks" />
      </div>
      <div class="form-field">
        <label>OP</label>
        <input v-model.number="newRecord.operation_seq" type="number" class="input-sm" placeholder="Seq" />
      </div>
    </div>
    <div class="form-row">
      <div class="form-field">
        <label>Plán (min)</label>
        <input v-model.number="newRecord.planned_time_min" type="number" step="0.1" class="input-sm" />
      </div>
      <div class="form-field">
        <label>Skutečnost (min)</label>
        <input v-model.number="newRecord.actual_time_min" type="number" step="0.1" class="input-sm" />
      </div>
    </div>
    <div class="form-row">
      <div class="form-field full-width">
        <label>Poznámka</label>
        <input v-model="newRecord.notes" type="text" class="input-sm" placeholder="Volitelná poznámka" />
      </div>
    </div>
    <div class="form-actions">
      <button class="btn-secondary" @click="handleCancel">Zrušit</button>
      <button class="btn-primary" :disabled="!newRecord.actual_time_min" @click="handleSubmit">
        <Plus :size="ICON_SIZE.SMALL" />
        Přidat
      </button>
    </div>
  </div>
</template>

<style scoped>
.add-form {
  padding: var(--pad);
  background: var(--raised);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  margin-bottom: var(--pad);
}
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-bottom: 6px;
}
.form-field { display: flex; flex-direction: column; gap: 4px; }
.form-field.full-width { grid-column: span 2; }
.form-field label {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t3);
}
.input-sm {
  padding: 4px 6px;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  font-size: var(--fs);
  color: var(--t1);
  font-family: var(--font);
}
.input-sm:focus {
  outline: none;
  border-color: var(--b3);
  box-shadow: 0 0 0 2px var(--b2);
}
.form-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
  margin-top: var(--pad);
}
</style>
