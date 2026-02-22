<script setup lang="ts">
/**
 * TimeVision Time Panel (FT v1) - Right panel for time estimation model
 * Shows OpenAI estimation results + calibration form.
 */
import { computed } from 'vue'
import { useTimeVisionStore } from '@/stores/timeVision'
import TimeVisionOperationBreakdown from './TimeVisionOperationBreakdown.vue'
import TimeVisionActualTimeForm from './TimeVisionActualTimeForm.vue'
import { Loader, Sparkles, Download, Cpu } from 'lucide-vue-next'
import { exportTrainingDataUrl } from '@/api/time-vision'
import { ICON_SIZE } from '@/config/design'

interface Props {
  filename: string | null
}
const props = defineProps<Props>()
const store = useTimeVisionStore()

const modelLabel = computed(() => {
  if (!store.modelInfo) return 'OpenAI'
  if (store.modelInfo.is_fine_tuned) {
    const parts = store.modelInfo.model.split(':')
    const suffix = parts.length >= 4 ? parts[3] : 'fine-tuned'
    return `Fine-tuned (${suffix})`
  }
  return 'GPT-4o base'
})

const estimation = computed(() => store.openaiEstimation)

const progressPercent = computed(() => {
  if (!store.openaiProcessingStep) return 0
  return Math.round((store.openaiProcessingStep.step / store.openaiProcessingStep.total) * 100)
})

async function runEstimation() {
  if (!props.filename) return
  const drawing = store.drawings.find(d => d.filename === props.filename)
  await store.processFileOpenAI(props.filename, drawing?.file_id ?? null)
}

function downloadTrainingData() {
  const token = localStorage.getItem('gestima_token')
  const url = exportTrainingDataUrl()
  window.open(`${url}${token ? `?token=${token}` : ''}`, '_blank')
}
</script>

<template>
  <div class="time-panel">
    <div class="panel-header">
      <h3>FT v1 — AI odhad času</h3>
      <div v-if="store.modelInfo" class="model-badge" :class="{ 'is-ft': store.modelInfo.is_fine_tuned }">
        <Cpu :size="ICON_SIZE.SMALL" />
        <span>{{ modelLabel }}</span>
      </div>
    </div>

    <div v-if="store.openaiProcessing" class="progress-section">
      <div class="progress-header">
        <Loader :size="ICON_SIZE.SMALL" class="spinner" />
        <span class="progress-label">{{ store.openaiProcessingStep?.label ?? 'Připravuji...' }}</span>
        <span class="progress-pct">{{ progressPercent }}%</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: progressPercent + '%' }" />
      </div>
    </div>

    <div v-if="store.openaiError" class="error-bar">{{ store.openaiError }}</div>

    <div v-if="!estimation && !store.openaiProcessing" class="empty-state">
      <Sparkles :size="ICON_SIZE.XLARGE" class="empty-icon" />
      <p>AI odhad ještě nebyl proveden.</p>
      <button class="btn-primary" :disabled="!filename" @click="runEstimation">
        <Sparkles :size="ICON_SIZE.SMALL" />
        Odhadnout
      </button>
    </div>

    <div v-if="estimation" :key="estimation.id" class="estimation-result">
      <div class="provider-badge">
        <Sparkles :size="ICON_SIZE.SMALL" />
        <span>{{ estimation.ai_provider === 'openai_ft' ? 'Fine-tuned' : 'GPT-4o' }}</span>
      </div>

      <div class="summary-grid">
        <div class="summary-item">
          <label>Typ</label>
          <span>{{ estimation.part_type ?? '—' }}</span>
        </div>
        <div class="summary-item">
          <label>Komplexita</label>
          <span>{{ estimation.complexity ?? '—' }}</span>
        </div>
        <div class="summary-item">
          <label>Materiál</label>
          <span>{{ estimation.material_detected ?? '—' }}</span>
        </div>
        <div class="summary-item highlight">
          <label>AI čas</label>
          <span class="time-value">{{ estimation.estimated_time_min?.toFixed(1) ?? '—' }} min</span>
        </div>
        <div class="summary-item">
          <label>Confidence</label>
          <span :class="'confidence-' + estimation.confidence">{{ estimation.confidence ?? '—' }}</span>
        </div>
      </div>

      <div v-if="estimation.estimation_reasoning" class="reasoning-section">
        <label>Reasoning</label>
        <p class="reasoning-text">{{ estimation.estimation_reasoning }}</p>
      </div>

      <TimeVisionOperationBreakdown :estimation="estimation" />

      <div class="calibration-section">
        <h4>Kalibrace a časy</h4>
        <TimeVisionActualTimeForm :estimation="estimation" />
      </div>

      <div class="actions">
        <button class="btn-secondary" :disabled="store.openaiProcessing" @click="runEstimation">
          <Sparkles :size="ICON_SIZE.SMALL" />
          Přeodhadnout
        </button>
        <button class="btn-secondary" @click="downloadTrainingData">
          <Download :size="ICON_SIZE.SMALL" />
          Export dat
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.time-panel { padding: var(--pad); }
.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--pad);
}
.panel-header h3 {
  font-size: var(--fs); font-weight: 600; margin: 0; color: var(--t1);
}
.model-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 6px; background: var(--ground);
  color: var(--t3); border-radius: var(--rs);
  font-size: var(--fs); font-weight: 500;
}
.model-badge.is-ft { background: var(--red-10); color: var(--red); font-weight: 600; }
.provider-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 6px; background: rgba(52,211,153,0.1);
  color: var(--red); border-radius: var(--rs);
  font-size: var(--fs); font-weight: 600; margin-bottom: var(--pad);
}
.empty-icon { color: var(--red); opacity: 0.5; }
.summary-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: var(--pad); margin-bottom: 12px;
}
.summary-item { display: flex; flex-direction: column; gap: 2px; }
.summary-item label {
  font-size: var(--fs); color: var(--t3); text-transform: uppercase;
}
.summary-item span { font-size: var(--fs); font-weight: 500; }
.summary-item.highlight { grid-column: span 2; }
.time-value { font-size: 16px; font-weight: 700; color: var(--red); }
.confidence-high { color: var(--ok); }
.confidence-medium { color: var(--warn); }
.confidence-low { color: var(--err); }
.reasoning-section { margin-bottom: 12px; }
.reasoning-section label {
  font-size: var(--fs); color: var(--t3);
  text-transform: uppercase; display: block; margin-bottom: 4px;
}
.reasoning-text {
  font-size: var(--fs); color: var(--t3);
  line-height: 1.5; background: var(--ground);
  padding: 6px; border-radius: var(--rs); white-space: pre-wrap;
}
.calibration-section {
  margin: 12px 0; padding-top: 12px;
  border-top: 1px solid var(--b2);
}
.calibration-section h4 {
  font-size: var(--fs); font-weight: 600;
  margin-bottom: 6px; color: var(--t1);
}
.actions {
  display: flex; gap: 6px;
  margin-top: 12px; padding-top: var(--pad);
  border-top: 1px solid var(--b2);
}
.progress-section {
  padding: var(--pad); background: var(--surface);
  border-radius: var(--r); margin-bottom: 12px;
}
.progress-header {
  display: flex; align-items: center; gap: 6px; margin-bottom: 6px;
}
.progress-label { flex: 1; font-size: var(--fs); font-weight: 500; }
.progress-pct { font-size: var(--fs); color: var(--t3); }
.progress-track {
  height: 4px; background: var(--ground);
  border-radius: var(--rs); overflow: hidden;
}
.progress-fill {
  height: 100%; background: var(--red);
  border-radius: var(--rs); transition: width 0.4s ease;
}
.error-bar {
  padding: 6px var(--pad);
  background: rgba(248,113,113,0.15); color: var(--err);
  font-size: var(--fs); border-radius: var(--rs);
  margin-bottom: var(--pad);
}
</style>
