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
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--b2);
}
.actual-time-form h4 {
  font-size: var(--fs);
  text-transform: uppercase;
  color: var(--t3);
  margin: 0 0 var(--pad) 0;
}
.deviation-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: var(--pad);
}
.deviation-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.deviation-item label {
  font-size: var(--fs);
  color: var(--t3);
  text-transform: uppercase;
}
.deviation-item span {
  font-size: var(--fs);
  font-weight: 600;
}
.over { color: var(--err); }
.under { color: var(--ok); }
.form-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: var(--pad);
}
.field-label {
  font-size: var(--fs);
  color: var(--t3);
  text-transform: uppercase;
  font-weight: 500;
}
.input-select {
  padding: 6px;
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  font-size: var(--fs);
  background: var(--ground);
  color: var(--t1);
}
.time-input-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
}
.input-time {
  width: 120px;
  padding: 6px;
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  font-size: var(--fs);
  background: var(--ground);
  color: var(--t1);
}
.unit {
  color: var(--t3);
  font-size: var(--fs);
}
.input-notes {
  width: 100%;
  padding: 6px;
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  font-size: var(--fs);
  resize: vertical;
  background: var(--ground);
  color: var(--t1);
  margin-bottom: 6px;
}
.btn-save {
  padding: 6px 12px;
  background: transparent;
  color: var(--t1);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  cursor: pointer;
  font-size: var(--fs);
  font-weight: 500;
}
.btn-save:hover {
  background: var(--b1);
}
.btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
