<script setup lang="ts">
/**
 * TimeVision - Actual Time Entry Form
 */
import { ref, computed, watch } from 'vue'
import { useTimeVisionStore } from '@/stores/timeVision'
import type { TimeVisionEstimation } from '@/types/time-vision'

interface Props {
  estimation: TimeVisionEstimation
}
const props = defineProps<Props>()
const store = useTimeVisionStore()

const complexity = ref<'simple' | 'medium' | 'complex' | null>(
  props.estimation.complexity as 'simple' | 'medium' | 'complex' | null
)
const partType = ref<'ROT' | 'PRI' | 'COMBINED' | null>(
  props.estimation.part_type as 'ROT' | 'PRI' | 'COMBINED' | null
)
const humanEstimate = ref<number | null>(props.estimation.human_estimate_min)
const actualTime = ref<number | null>(props.estimation.actual_time_min)
const notes = ref(props.estimation.actual_notes ?? '')
const saving = ref(false)

// Sync form values when estimation changes (switching drawings or after save)
// Watch both ID (drawing switch) and version (after save/calibrate)
watch(
  () => `${props.estimation.id}-${props.estimation.version}`,
  () => {
    complexity.value = props.estimation.complexity as 'simple' | 'medium' | 'complex' | null
    partType.value = props.estimation.part_type as 'ROT' | 'PRI' | 'COMBINED' | null
    humanEstimate.value = props.estimation.human_estimate_min
    actualTime.value = props.estimation.actual_time_min
    notes.value = props.estimation.actual_notes ?? ''
  },
  { immediate: true },
)

interface Deviation {
  ai_vs_actual?: { diff: string; pct: string }
  human_vs_actual?: { diff: string; pct: string }
  ai_vs_human?: { diff: string; pct: string }
}

const deviation = computed<Deviation>(() => {
  const result: Deviation = {}

  if (props.estimation.estimated_time_min && props.estimation.actual_time_min) {
    const diff = props.estimation.actual_time_min - props.estimation.estimated_time_min
    const pct = (diff / props.estimation.estimated_time_min) * 100
    result.ai_vs_actual = { diff: diff.toFixed(0), pct: pct.toFixed(0) }
  }

  if (props.estimation.human_estimate_min && props.estimation.actual_time_min) {
    const diff = props.estimation.actual_time_min - props.estimation.human_estimate_min
    const pct = (diff / props.estimation.human_estimate_min) * 100
    result.human_vs_actual = { diff: diff.toFixed(0), pct: pct.toFixed(0) }
  }

  if (props.estimation.estimated_time_min && props.estimation.human_estimate_min) {
    const diff = props.estimation.human_estimate_min - props.estimation.estimated_time_min
    const pct = (diff / props.estimation.estimated_time_min) * 100
    result.ai_vs_human = { diff: diff.toFixed(0), pct: pct.toFixed(0) }
  }

  return result
})

async function handleSave() {
  // Allow saving if ANY field changed, not just actual_time
  const hasChanges =
    (complexity.value && complexity.value !== props.estimation.complexity) ||
    (partType.value && partType.value !== props.estimation.part_type) ||
    (humanEstimate.value && humanEstimate.value > 0 && humanEstimate.value !== props.estimation.human_estimate_min) ||
    (actualTime.value && actualTime.value > 0 && actualTime.value !== props.estimation.actual_time_min) ||
    notes.value !== (props.estimation.actual_notes ?? '')

  if (!hasChanges) {
    return
  }

  saving.value = true
  try {
    const payload: {
      complexity?: 'simple' | 'medium' | 'complex'
      part_type?: 'ROT' | 'PRI' | 'COMBINED'
      human_estimate_min?: number
      actual_time_min?: number
      actual_notes?: string
      version: number
    } = {
      version: props.estimation.version,
    }

    if (complexity.value && complexity.value !== props.estimation.complexity) {
      payload.complexity = complexity.value
    }
    if (partType.value && partType.value !== props.estimation.part_type) {
      payload.part_type = partType.value
    }
    if (humanEstimate.value && humanEstimate.value > 0) {
      payload.human_estimate_min = humanEstimate.value
    }
    if (actualTime.value && actualTime.value > 0) {
      payload.actual_time_min = actualTime.value
    }
    if (notes.value) {
      payload.actual_notes = notes.value
    }

    await store.calibrateOpenAI(props.estimation.id, payload)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="actual-time-form">
    <h4>Kalibrace odhadu</h4>

    <div v-if="deviation.ai_vs_actual || deviation.human_vs_actual || deviation.ai_vs_human" class="deviation-grid">
      <div v-if="deviation.ai_vs_actual" class="deviation-item">
        <label>AI vs Skutečný</label>
        <span :class="Number(deviation.ai_vs_actual.diff) > 0 ? 'over' : 'under'">
          {{ Number(deviation.ai_vs_actual.diff) > 0 ? '+' : '' }}{{ deviation.ai_vs_actual.diff }} min ({{ Number(deviation.ai_vs_actual.pct) > 0 ? '+' : '' }}{{ deviation.ai_vs_actual.pct }}%)
        </span>
      </div>
      <div v-if="deviation.human_vs_actual" class="deviation-item">
        <label>Můj odhad vs Skutečný</label>
        <span :class="Number(deviation.human_vs_actual.diff) > 0 ? 'over' : 'under'">
          {{ Number(deviation.human_vs_actual.diff) > 0 ? '+' : '' }}{{ deviation.human_vs_actual.diff }} min ({{ Number(deviation.human_vs_actual.pct) > 0 ? '+' : '' }}{{ deviation.human_vs_actual.pct }}%)
        </span>
      </div>
      <div v-if="deviation.ai_vs_human" class="deviation-item">
        <label>Můj odhad vs AI</label>
        <span :class="Number(deviation.ai_vs_human.diff) > 0 ? 'over' : 'under'">
          {{ Number(deviation.ai_vs_human.diff) > 0 ? '+' : '' }}{{ deviation.ai_vs_human.diff }} min ({{ Number(deviation.ai_vs_human.pct) > 0 ? '+' : '' }}{{ deviation.ai_vs_human.pct }}%)
        </span>
      </div>
    </div>

    <div class="form-row">
      <label class="field-label">Typ dílu</label>
      <select v-model="partType" class="input-select">
        <option :value="null">-</option>
        <option value="ROT">ROT (Rotační)</option>
        <option value="PRI">PRI (Prizmatický)</option>
        <option value="COMBINED">COMBINED (Kombinovaný)</option>
      </select>
    </div>

    <div class="form-row">
      <label class="field-label">Složitost</label>
      <select v-model="complexity" class="input-select">
        <option :value="null">-</option>
        <option value="simple">Simple</option>
        <option value="medium">Medium</option>
        <option value="complex">Complex</option>
      </select>
    </div>

    <div class="form-row">
      <label class="field-label">Můj odhad</label>
      <div class="time-input-wrapper">
        <input
          v-model.number="humanEstimate"
          type="number"
          min="0.1"
          max="10000"
          step="0.1"
          placeholder="Váš odhad v minutách"
          class="input-time"
        />
        <span class="unit">min</span>
      </div>
    </div>

    <div class="form-row">
      <label class="field-label">Reálný čas</label>
      <div class="time-input-wrapper">
        <input
          v-model.number="actualTime"
          type="number"
          min="1"
          max="10000"
          step="1"
          placeholder="Čas v minutách"
          class="input-time"
        />
        <span class="unit">min</span>
      </div>
    </div>

    <textarea
      v-model="notes"
      placeholder="Poznámky (volitelné)"
      class="input-notes"
      rows="2"
    />
    <button
      class="btn-save"
      :disabled="saving"
      @click="handleSave"
    >
      {{ saving ? 'Ukládám...' : 'Uložit změny' }}
    </button>
  </div>
</template>

<style scoped>
.actual-time-form {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-default);
}
.actual-time-form h4 {
  font-size: var(--text-sm);
  text-transform: uppercase;
  color: var(--text-muted);
  margin: 0 0 var(--space-3) 0;
}
.deviation-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.deviation-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-0\.5);
}
.deviation-item label {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  text-transform: uppercase;
}
.deviation-item span {
  font-size: var(--text-sm);
  font-weight: 600;
}
.over { color: var(--color-danger); }
.under { color: var(--color-success); }
.form-row {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin-bottom: var(--space-3);
}
.field-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  text-transform: uppercase;
  font-weight: 500;
}
.input-select {
  padding: var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  background: var(--bg-input);
  color: var(--text-primary);
}
.time-input-wrapper {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.input-time {
  width: 120px;
  padding: var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  background: var(--bg-input);
  color: var(--text-primary);
}
.unit {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.input-notes {
  width: 100%;
  padding: var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  resize: vertical;
  background: var(--bg-input);
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}
.btn-save {
  padding: var(--space-2) var(--space-4);
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: var(--text-sm);
  font-weight: 500;
}
.btn-save:hover {
  background: var(--state-hover);
}
.btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
