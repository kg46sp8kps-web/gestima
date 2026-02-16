<script setup lang="ts">
/**
 * AI Estimate Panel - Collapsible right panel for AI time estimation
 * Uses TimeVision (OpenAI GPT-4o Vision) to estimate machining time from PDF drawing.
 * Creates 1 operation with total estimated time (locked).
 */

import { ref, computed, watch } from 'vue'
import { useTimeVisionStore } from '@/stores/timeVision'
import { useOperationsStore } from '@/stores/operations'
import { operationsApi } from '@/api/operations'
import { listDrawings } from '@/api/drawings'
import { fetchOpenAIEstimation } from '@/api/time-vision'
import { generateTechnology } from '@/api/technology'
import { confirm } from '@/composables/useDialog'
import type { Part } from '@/types/part'
import type { Drawing } from '@/types/drawing'
import type { TimeVisionEstimation, OperationBreakdown } from '@/types/time-vision'
import type { WorkCenter } from '@/types/operation'
import type { LinkingGroup } from '@/stores/windows'
import { X, Sparkles, Play, CheckCircle, AlertTriangle, RefreshCw } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  partId: number | null
  part: Part | null
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  linkingGroup: null
})

const emit = defineEmits<{
  'close': []
  'operation-created': []
}>()

const timeVisionStore = useTimeVisionStore()
const operationsStore = useOperationsStore()
// State
const primaryDrawing = ref<Drawing | null>(null)
const drawingsLoading = ref(false)
const estimation = ref<TimeVisionEstimation | null>(null)
const creating = ref(false)
const error = ref<string | null>(null)
const techWarnings = ref<string[]>([])

// Computed
const processing = computed(() => timeVisionStore.openaiProcessing)
const processingStep = computed(() => timeVisionStore.openaiProcessingStep)
const activeWorkCenters = computed(() => operationsStore.activeWorkCenters)
const operations = computed(() => operationsStore.getContext(props.linkingGroup).operations)

const hasExistingAIOperation = computed(() => {
  if (!estimation.value) return false
  return operations.value.some(op => op.ai_estimation_id === estimation.value!.id)
})

const breakdown = computed<OperationBreakdown[]>(() => {
  if (!estimation.value?.estimation_breakdown_json) return []
  try {
    return JSON.parse(estimation.value.estimation_breakdown_json)
  } catch {
    return []
  }
})

const drawingFilename = computed(() => {
  if (primaryDrawing.value) return primaryDrawing.value.filename
  if (props.part?.drawing_path) return props.part.drawing_path.split('/').pop() || null
  return null
})

// Load drawings when part changes
watch(() => props.part, async (newPart) => {
  estimation.value = null
  error.value = null
  primaryDrawing.value = null

  if (!newPart) return

  drawingsLoading.value = true
  try {
    const result = await listDrawings(newPart.part_number)
    const primary = result.drawings.find(d => d.is_primary) || result.drawings[0]
    primaryDrawing.value = primary || null
  } catch {
    // Fallback to drawing_path
  } finally {
    drawingsLoading.value = false
  }
}, { immediate: true })

// Reuse existing estimation or create new one
async function runEstimation() {
  const filename = drawingFilename.value
  if (!filename) {
    error.value = 'Díl nemá výkres'
    return
  }

  error.value = null
  estimation.value = null

  try {
    // Always reuse existing estimation (prevents duplicates in TimeVision/FT export)
    // ADR-045: Prefer part_id lookup (direct FK) over filename matching
    const existing = await fetchOpenAIEstimation(filename, props.partId)
    if (existing) {
      estimation.value = existing
      return
    }

    // No estimation exists — run AI via SSE (with part_id for FK binding)
    const result = await timeVisionStore.processFileOpenAI(filename, undefined, props.partId)
    estimation.value = result
  } catch (err: unknown) {
    error.value = (err as Error).message || 'AI odhad selhal'
  }
}

// Generate complete technology plan from estimation
async function createOperation() {
  if (!estimation.value || !props.partId) return

  creating.value = true
  error.value = null
  techWarnings.value = []

  try {
    const result = await generateTechnology({
      estimation_id: estimation.value.id,
      part_id: props.partId,
    })

    techWarnings.value = result.warnings

    // Reload operations in parent
    await operationsStore.loadOperations(props.partId, props.linkingGroup)

    emit('operation-created')
    emit('close')
  } catch (err: unknown) {
    error.value = (err as Error).message || 'Nepodařilo se vygenerovat technologii'
  } finally {
    creating.value = false
  }
}

// Confidence badge class
function confidenceClass(confidence: string | null): string {
  switch (confidence) {
    case 'high': return 'badge-success'
    case 'medium': return 'badge-warning'
    case 'low': return 'badge-danger'
    default: return 'badge-neutral'
  }
}
</script>

<template>
  <div class="ai-estimate-panel">
    <!-- Header -->
    <div class="panel-header">
      <div class="header-title">
        <Sparkles :size="ICON_SIZE.SMALL" class="sparkles-icon" />
        <h4>AI odhad</h4>
      </div>
      <button class="btn-close" @click="emit('close')" title="Zavřít">
        <X :size="ICON_SIZE.SMALL" />
      </button>
    </div>

    <div class="panel-content">
      <!-- No drawing -->
      <div v-if="!drawingFilename && !drawingsLoading" class="state-empty">
        <AlertTriangle :size="ICON_SIZE.LARGE" class="icon-warning" />
        <p>Díl nemá výkres</p>
        <p class="hint">Nahrajte PDF výkres na položku</p>
      </div>

      <!-- Loading drawings -->
      <div v-else-if="drawingsLoading" class="state-loading">
        <div class="spinner"></div>
        <p>Načítám výkres...</p>
      </div>

      <!-- Ready to estimate -->
      <template v-else-if="!estimation && !processing">
        <div class="drawing-info">
          <span class="label">Výkres:</span>
          <span class="filename">{{ drawingFilename }}</span>
        </div>
        <button
          class="btn-primary btn-run"
          @click="runEstimation"
          :disabled="!drawingFilename"
        >
          <Play :size="ICON_SIZE.SMALL" />
          Spustit AI odhad
        </button>
      </template>

      <!-- Processing -->
      <div v-else-if="processing" class="state-processing">
        <div class="spinner"></div>
        <p>{{ processingStep?.label || 'AI odhad běží...' }}</p>
        <p v-if="processingStep" class="step-info">
          Krok {{ processingStep.step }} / {{ processingStep.total }}
        </p>
      </div>

      <!-- Result -->
      <template v-else-if="estimation">
        <div class="result-section">
          <!-- Total time -->
          <div class="result-highlight">
            <span class="result-label">Celkový čas</span>
            <span class="result-value">{{ estimation.estimated_time_min?.toFixed(1) }} min</span>
          </div>

          <!-- Metadata -->
          <div class="result-meta">
            <div class="meta-row">
              <span class="label">Typ:</span>
              <span class="value">{{ estimation.part_type }}</span>
            </div>
            <div class="meta-row">
              <span class="label">Složitost:</span>
              <span class="value">{{ estimation.complexity }}</span>
            </div>
            <div v-if="estimation.material_detected" class="meta-row">
              <span class="label">Materiál:</span>
              <span class="value">{{ estimation.material_detected }}</span>
            </div>
            <div class="meta-row">
              <span class="label">Spolehlivost:</span>
              <span class="badge" :class="confidenceClass(estimation.confidence)">
                {{ estimation.confidence }}
              </span>
            </div>
          </div>

          <!-- Breakdown -->
          <div v-if="breakdown.length > 0" class="breakdown-section">
            <h5>Rozpis operací</h5>
            <table class="breakdown-table">
              <tbody>
                <tr v-for="item in breakdown" :key="item.operation">
                  <td class="op-name">{{ item.operation }}</td>
                  <td class="op-time">{{ item.time_min }} min</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Actions -->
          <div class="result-actions">
            <button
              class="btn-primary"
              @click="createOperation"
              :disabled="creating"
            >
              <CheckCircle :size="ICON_SIZE.SMALL" />
              {{ creating ? 'Generuji...' : (hasExistingAIOperation ? 'Aktualizovat technologii' : 'Generovat technologii') }}
            </button>
            <button class="btn-secondary" @click="estimation = null">
              Zrušit
            </button>
          </div>

          <!-- Technology warnings -->
          <div v-if="techWarnings.length > 0" class="tech-warnings">
            <div v-for="(w, i) in techWarnings" :key="i" class="warning-item">
              <AlertTriangle :size="ICON_SIZE.SMALL" />
              <span>{{ w }}</span>
            </div>
          </div>
        </div>
      </template>

      <!-- Error -->
      <div v-if="error" class="error-banner">
        <p>{{ error }}</p>
        <button @click="error = null" class="btn-dismiss">&times;</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ai-estimate-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-surface);
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.header-title h4 {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.sparkles-icon {
  color: var(--brand-text);
}

.btn-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: none;
  border: none;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-close:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* States */
.state-empty, .state-loading, .state-processing {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-6) var(--space-4);
  text-align: center;
  color: var(--text-secondary);
}

.state-empty p, .state-loading p, .state-processing p {
  margin: 0;
  font-size: var(--text-sm);
}

.hint {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.icon-warning { color: var(--color-warning); }

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.step-info {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

/* Drawing info */
.drawing-info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--bg-muted);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}

.drawing-info .label {
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

.drawing-info .filename {
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  word-break: break-all;
}

/* Run button */
.btn-run {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}

.btn-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-primary:hover:not(:disabled) {
  background: var(--brand-subtle, rgba(153, 27, 27, 0.1));
  border-color: var(--color-brand, #991b1b);
  color: var(--color-brand, #991b1b);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  padding: var(--space-2) var(--space-4);
  background: none;
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-secondary:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

/* Result */
.result-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.result-highlight {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(99, 102, 241, 0.1));
  border-radius: var(--radius-md);
  border: 1px solid rgba(139, 92, 246, 0.2);
}

.result-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

.result-value {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--brand-text);
  font-family: var(--font-mono);
}

.result-meta {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--text-sm);
}

.meta-row .label {
  color: var(--text-secondary);
}

.meta-row .value {
  color: var(--text-primary);
  font-weight: var(--font-medium);
}

.badge {
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  text-transform: uppercase;
}

.badge-success { background: var(--color-success-bg); color: var(--color-success); }
.badge-warning { background: var(--color-warning-bg); color: var(--color-warning); }
.badge-danger { background: var(--color-danger-bg); color: var(--color-danger); }
.badge-neutral { background: var(--bg-muted); color: var(--text-secondary); }

/* Breakdown */
.breakdown-section h5 {
  margin: 0;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.breakdown-table {
  width: 100%;
  font-size: var(--text-sm);
  border-collapse: collapse;
}

.breakdown-table td {
  padding: var(--space-1) 0;
  border-bottom: 1px solid var(--border-subtle);
}

.op-name {
  color: var(--text-primary);
}

.op-time {
  text-align: right;
  font-family: var(--font-mono);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

/* Actions */
.result-actions {
  display: flex;
  gap: var(--space-2);
}

.result-actions .btn-primary {
  flex: 1;
}

/* Error */
.error-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3);
  background: var(--color-danger-bg);
  color: var(--color-danger);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}

.error-banner p { margin: 0; flex: 1; }

.btn-dismiss {
  background: none;
  border: none;
  color: var(--color-danger);
  font-size: var(--text-xl);
  font-weight: bold;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-dismiss:hover { opacity: 0.7; }

/* Technology warnings */
.tech-warnings {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.warning-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
}
</style>
