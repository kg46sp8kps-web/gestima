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
.time-panel { padding: var(--space-3); }
.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: var(--space-3);
}
.panel-header h3 {
  font-size: var(--text-sm); font-weight: 600; margin: 0; color: var(--text-primary);
}
.model-badge {
  display: inline-flex; align-items: center; gap: var(--space-1);
  padding: var(--space-0\.5) var(--space-2); background: var(--bg-subtle);
  color: var(--text-muted); border-radius: var(--radius-sm);
  font-size: var(--text-xs); font-weight: 500;
}
.model-badge.is-ft { background: rgba(var(--color-primary-rgb, 220 38 38), 0.1); color: var(--color-primary); font-weight: 600; }
.provider-badge {
  display: inline-flex; align-items: center; gap: var(--space-1);
  padding: var(--space-0\.5) var(--space-2); background: rgba(16, 163, 127, 0.1);
  color: var(--color-primary); border-radius: var(--radius-sm);
  font-size: var(--text-xs); font-weight: 600; margin-bottom: var(--space-3);
}
.empty-state {
  display: flex; flex-direction: column; align-items: center;
  gap: var(--space-3); padding: var(--space-8);
  text-align: center; color: var(--text-muted);
}
.empty-icon { color: var(--color-primary); opacity: 0.5; }
.btn-primary {
  display: inline-flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-4); background: transparent;
  color: var(--text-primary); border: 1px solid var(--border-default); border-radius: var(--radius-md);
  font-size: var(--text-sm); font-weight: 500; cursor: pointer;
}
.btn-primary:hover { background: var(--brand-subtle, rgba(153, 27, 27, 0.1)); border-color: var(--color-brand, #991b1b); color: var(--color-brand, #991b1b); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary {
  display: inline-flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-3); background: var(--bg-surface);
  border: 1px solid var(--border-default); border-radius: var(--radius-md);
  font-size: var(--text-xs); cursor: pointer; color: var(--text-secondary);
}
.btn-secondary:hover { border-color: var(--color-primary); color: var(--text-primary); }
.summary-grid {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: var(--space-3); margin-bottom: var(--space-4);
}
.summary-item { display: flex; flex-direction: column; gap: var(--space-0\.5); }
.summary-item label {
  font-size: var(--text-xs); color: var(--text-muted); text-transform: uppercase;
}
.summary-item span { font-size: var(--text-sm); font-weight: 500; }
.summary-item.highlight { grid-column: span 2; }
.time-value { font-size: var(--text-2xl); font-weight: 700; color: var(--color-primary); }
.confidence-high { color: var(--color-success); }
.confidence-medium { color: var(--color-warning); }
.confidence-low { color: var(--color-danger); }
.reasoning-section { margin-bottom: var(--space-4); }
.reasoning-section label {
  font-size: var(--text-xs); color: var(--text-muted);
  text-transform: uppercase; display: block; margin-bottom: var(--space-1);
}
.reasoning-text {
  font-size: var(--text-xs); color: var(--text-secondary);
  line-height: 1.5; background: var(--bg-subtle);
  padding: var(--space-2); border-radius: var(--radius-sm); white-space: pre-wrap;
}
.calibration-section {
  margin: var(--space-4) 0; padding-top: var(--space-4);
  border-top: 1px solid var(--border-default);
}
.calibration-section h4 {
  font-size: var(--text-sm); font-weight: 600;
  margin-bottom: var(--space-2); color: var(--text-primary);
}
.actions {
  display: flex; gap: var(--space-2);
  margin-top: var(--space-4); padding-top: var(--space-3);
  border-top: 1px solid var(--border-default);
}
.progress-section {
  padding: var(--space-3); background: var(--bg-surface);
  border-radius: var(--radius-md); margin-bottom: var(--space-4);
}
.progress-header {
  display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-2);
}
.spinner { animation: spin 1s linear infinite; color: var(--color-primary); }
@keyframes spin { to { transform: rotate(360deg); } }
.progress-label { flex: 1; font-size: var(--text-sm); font-weight: 500; }
.progress-pct { font-size: var(--text-xs); color: var(--text-muted); }
.progress-track {
  height: 4px; background: var(--bg-subtle);
  border-radius: var(--radius-sm); overflow: hidden;
}
.progress-fill {
  height: 100%; background: var(--color-primary);
  border-radius: var(--radius-sm); transition: width 0.4s ease;
}
.error-bar {
  padding: var(--space-2) var(--space-3);
  background: rgba(244, 63, 94, 0.1); color: var(--color-danger);
  font-size: var(--text-sm); border-radius: var(--radius-sm);
  margin-bottom: var(--space-3);
}
</style>
