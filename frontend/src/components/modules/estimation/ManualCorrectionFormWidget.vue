<template>
  <section class="correction-form">
    <h4 class="section-title">✏️ Opravit data</h4>

    <!-- PART TYPE -->
    <div class="form-group">
      <label class="form-label">Typ dílu</label>
      <div class="radio-group">
        <label class="radio-option">
          <input v-model="formData.partType" type="radio" value="ROT" />
          <span class="radio-label">
            <span class="radio-emoji">🔄</span>
            <span class="radio-text">Soustružení (ROT)</span>
          </span>
        </label>
        <label class="radio-option">
          <input v-model="formData.partType" type="radio" value="PRI" />
          <span class="radio-label">
            <span class="radio-emoji">📦</span>
            <span class="radio-text">Frézování (PRI)</span>
          </span>
        </label>
      </div>
    </div>

    <!-- STOCK TYPE -->
    <div class="form-group">
      <label class="form-label">Polotovar</label>
      <select v-model="formData.stockType" class="form-select">
        <option value="cylinder">Tyč kruhová</option>
        <option value="box">Hraněný polotovar</option>
        <option value="tube">Trubka</option>
      </select>
    </div>

    <!-- STOCK DIMENSIONS (conditional) -->
    <div v-if="formData.stockType === 'cylinder' || formData.stockType === 'tube'" class="form-group">
      <label class="form-label">Rozměry polotovaru (tyč/trubka)</label>
      <div class="input-row">
        <input
          v-model.number="formData.stockDiameter"
          type="number"
          class="form-input"
          placeholder="Průměr"
          step="0.5"
          min="0.1"
        />
        <span class="input-unit">mm Ø</span>
        <input
          v-model.number="formData.stockLength"
          type="number"
          class="form-input"
          placeholder="Délka"
          step="0.5"
          min="0.1"
        />
        <span class="input-unit">mm</span>
      </div>
    </div>

    <div v-else class="form-group">
      <label class="form-label">Rozměry polotovaru (hraněný)</label>
      <div class="input-row">
        <input
          v-model.number="formData.bboxX"
          type="number"
          class="form-input"
          placeholder="X"
          step="0.5"
          min="0.1"
        />
        <span class="input-unit">×</span>
        <input
          v-model.number="formData.bboxY"
          type="number"
          class="form-input"
          placeholder="Y"
          step="0.5"
          min="0.1"
        />
        <span class="input-unit">×</span>
        <input
          v-model.number="formData.bboxZ"
          type="number"
          class="form-input"
          placeholder="Z"
          step="0.5"
          min="0.1"
        />
        <span class="input-unit">mm</span>
      </div>
    </div>

    <!-- MATERIAL -->
    <div class="form-group">
      <label class="form-label">Materiál</label>
      <select v-model="formData.materialCode" class="form-select">
        <option value="20910000">Ocel automatová (S235)</option>
        <option value="20910001">Ocel konstrukční (11 523)</option>
        <option value="20910002">Ocel legovaná (16MnCr5)</option>
        <option value="20910003">Ocel nástrojová (19 552)</option>
        <option value="20910004">Nerez (1.4301)</option>
        <option value="20910005">Hliník (AlMgSi1)</option>
        <option value="20910006">Měď (Cu-ETP)</option>
        <option value="20910007">Mosaz (CuZn37)</option>
        <option value="20910008">Plasty (PA6)</option>
      </select>
    </div>

    <!-- TIME ESTIMATES -->
    <div class="form-group time-section">
      <h5 class="subsection-title">💰 Strojní časy</h5>
      <div class="time-inputs">
        <div class="time-input-group">
          <label class="time-label">Hrubování</label>
          <div class="time-input-row">
            <input
              v-model.number="formData.roughingTime"
              type="number"
              class="form-input time-input"
              placeholder="0.0"
              step="0.5"
              min="0"
            />
            <span class="input-unit">min</span>
          </div>
        </div>
        <div class="time-input-group">
          <label class="time-label">Dokončení</label>
          <div class="time-input-row">
            <input
              v-model.number="formData.finishingTime"
              type="number"
              class="form-input time-input"
              placeholder="0.0"
              step="0.5"
              min="0"
            />
            <span class="input-unit">min</span>
          </div>
        </div>
        <div class="time-input-group">
          <label class="time-label">Setup</label>
          <div class="time-input-row">
            <input
              v-model.number="formData.setupTime"
              type="number"
              class="form-input time-input"
              placeholder="0.0"
              step="0.5"
              min="0"
            />
            <span class="input-unit">min</span>
          </div>
        </div>
      </div>
      <div class="total-time">
        <span class="total-label">CELKEM:</span>
        <span class="total-value">{{ totalTime.toFixed(1) }} min</span>
      </div>
    </div>

    <!-- NOTES -->
    <div class="form-group">
      <label class="form-label">Poznámka</label>
      <textarea
        v-model="formData.notes"
        class="form-textarea"
        placeholder="Důvod úpravy, dodatečné operace, poznámky..."
        rows="3"
      ></textarea>
    </div>

    <!-- ACTIONS -->
    <div class="form-actions">
      <button class="btn btn-primary" :disabled="!canSubmit" @click="handleSubmit">
        💾 Uložit
      </button>
      <button class="btn btn-secondary" @click="handleNext">⏭️ Další díl</button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { EstimationRecord } from '@/types/estimation'

interface Props {
  record: EstimationRecord
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'submit', data: CorrectionFormData): void
  (e: 'next'): void
}>()

export interface CorrectionFormData {
  partType: 'ROT' | 'PRI'
  stockType: 'cylinder' | 'box' | 'tube'
  stockDiameter: number | null
  stockLength: number | null
  bboxX: number | null
  bboxY: number | null
  bboxZ: number | null
  materialCode: string
  roughingTime: number | null
  finishingTime: number | null
  setupTime: number | null
  notes: string
}

const formData = ref<CorrectionFormData>({
  partType: props.record.part_type as 'ROT' | 'PRI',
  stockType: props.record.rotational_score > 0.6 ? 'cylinder' : 'box',
  stockDiameter: props.record.part_type === 'ROT' ? Math.max(props.record.bbox_x_mm, props.record.bbox_y_mm) : null,
  stockLength: props.record.bbox_z_mm,
  bboxX: props.record.bbox_x_mm,
  bboxY: props.record.bbox_y_mm,
  bboxZ: props.record.bbox_z_mm,
  materialCode: props.record.corrected_material_code || props.record.material_group_code,
  roughingTime: null,
  finishingTime: null,
  setupTime: null,
  notes: props.record.correction_notes || ''
})

const totalTime = computed(() => {
  const rough = formData.value.roughingTime || 0
  const finish = formData.value.finishingTime || 0
  const setup = formData.value.setupTime || 0
  return rough + finish + setup
})

const canSubmit = computed(() => {
  return totalTime.value > 0 && formData.value.materialCode.length > 0
})

function handleSubmit() {
  if (canSubmit.value) {
    emit('submit', formData.value)
  }
}

function handleNext() {
  emit('next')
}

// Reset form when record changes
watch(
  () => props.record.id,
  () => {
    formData.value = {
      partType: props.record.part_type as 'ROT' | 'PRI',
      stockType: props.record.rotational_score > 0.6 ? 'cylinder' : 'box',
      stockDiameter:
        props.record.part_type === 'ROT' ? Math.max(props.record.bbox_x_mm, props.record.bbox_y_mm) : null,
      stockLength: props.record.bbox_z_mm,
      bboxX: props.record.bbox_x_mm,
      bboxY: props.record.bbox_y_mm,
      bboxZ: props.record.bbox_z_mm,
      materialCode: props.record.corrected_material_code || props.record.material_group_code,
      roughingTime: null,
      finishingTime: null,
      setupTime: null,
      notes: props.record.correction_notes || ''
    }
  }
)
</script>

<style scoped>
.correction-form {
  margin-bottom: var(--space-5);
  padding: var(--space-4);
  background: var(--bg-base);
  border: 2px solid var(--border-default);
  border-radius: var(--radius-lg);
}

.section-title {
  margin: 0 0 var(--space-4) 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.form-group {
  margin-bottom: var(--space-4);
}

.form-label {
  display: block;
  margin-bottom: var(--space-2);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.radio-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
}

.radio-option {
  display: flex;
  align-items: center;
  padding: var(--space-3);
  background: var(--bg-surface);
  border: 2px solid var(--border-default);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.radio-option:hover {
  border-color: var(--color-primary);
  background: var(--bg-hover);
}

.radio-option input[type='radio'] {
  margin-right: var(--space-2);
}

.radio-option input[type='radio']:checked + .radio-label {
  color: var(--color-primary);
  font-weight: 600;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.radio-emoji {
  font-size: var(--text-xl);
}

.radio-text {
  font-size: var(--text-sm);
}

.form-select {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-sm);
  cursor: pointer;
}

.form-select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--bg-accent);
}

.input-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.form-input {
  flex: 1;
  padding: var(--space-2) var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: var(--font-mono);
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--bg-accent);
}

.input-unit {
  font-size: var(--text-xs);
  color: var(--text-muted);
  white-space: nowrap;
}

.time-section {
  padding: var(--space-3);
  background: var(--bg-surface);
  border-radius: var(--radius-md);
}

.subsection-title {
  margin: 0 0 var(--space-3) 0;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
}

.time-inputs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.time-input-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.time-label {
  font-size: var(--text-xs);
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
}

.time-input-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.time-input {
  flex: 1;
  min-width: 0;
}

.total-time {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3);
  background: var(--bg-base);
  border: 2px solid var(--color-primary);
  border-radius: var(--radius-md);
}

.total-label {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.total-value {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-primary);
  font-family: var(--font-mono);
}

.form-textarea {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-family: inherit;
  resize: vertical;
}

.form-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--bg-accent);
}

.form-actions {
  display: flex;
  gap: var(--space-3);
}

.btn {
  flex: 1;
  padding: var(--space-3) var(--space-4);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast);
}

.btn-primary {
  background: var(--color-success);
  color: var(--text-inverse);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-success-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-surface);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

.btn-secondary:hover {
  background: var(--bg-hover);
  border-color: var(--color-primary);
}
</style>
