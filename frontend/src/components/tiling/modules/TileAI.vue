<script setup lang="ts">
/**
 * TileAI — AI/TimeVision module for tiling workspace
 * Extracted from PartDetailTabs.vue — renders TV estimation + ML calibration
 */

import { ref, computed, watch } from 'vue'
import { useOperationsStore } from '@/stores/operations'
import { useUiStore } from '@/stores/ui'
import { fetchOpenAIEstimation, fetchEstimationById, calibrateEstimation } from '@/api/time-vision'
import type { CalibrationUpdate } from '@/api/time-vision'
import type { TimeVisionEstimation, OperationBreakdown } from '@/types/time-vision'
import type { LinkingGroup } from '@/types/workspace'
import { GraduationCap, Sparkles, Save, CheckCircle, Clock, ChevronRight, ChevronDown } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  partId: number | null
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  linkingGroup: null,
})

const operationsStore = useOperationsStore()
const uiStore = useUiStore()

// TimeVision state
const tvEstimation = ref<TimeVisionEstimation | null>(null)
const tvCollapsed = ref(false)
const tvLoading = ref(false)

// ML calibration state
const mlCollapsed = ref(false)
const mlLoading = ref(false)
const mlSaving = ref(false)
const aiEstimation = ref<TimeVisionEstimation | null>(null)
const mlComplexity = ref<'simple' | 'medium' | 'complex' | null>(null)
const mlPartType = ref<'ROT' | 'PRI' | 'COMBINED' | null>(null)
const mlHumanEstimate = ref<number | null>(null)
const mlActualTime = ref<number | null>(null)
const mlNotes = ref<string>('')

// Computed
const hasAIEstimation = computed(() => {
  const ops = operationsStore.getContext(props.linkingGroup).operations
  return ops.some(op => op.ai_estimation_id != null)
})

const firstAIEstimationId = computed(() => {
  const ops = operationsStore.getContext(props.linkingGroup).operations
  const op = ops.find(o => o.ai_estimation_id != null)
  return op?.ai_estimation_id ?? null
})

const currentOperationTime = computed(() => {
  const ops = operationsStore.getContext(props.linkingGroup).operations
  const op = ops.find(o => o.ai_estimation_id != null)
  return op?.operation_time_min ?? null
})

const tvBreakdown = computed<OperationBreakdown[]>(() => {
  if (!tvEstimation.value?.estimation_breakdown_json) return []
  try {
    return JSON.parse(tvEstimation.value.estimation_breakdown_json)
  } catch {
    return []
  }
})

interface Deviation {
  ai_vs_actual?: { diff: string; pct: string }
  human_vs_actual?: { diff: string; pct: string }
  ai_vs_human?: { diff: string; pct: string }
}

const deviation = computed<Deviation>(() => {
  const result: Deviation = {}
  const est = aiEstimation.value
  if (est?.estimated_time_min && mlActualTime.value) {
    const diff = mlActualTime.value - est.estimated_time_min
    const pct = (diff / est.estimated_time_min) * 100
    result.ai_vs_actual = { diff: diff.toFixed(0), pct: pct.toFixed(0) }
  }
  if (mlHumanEstimate.value && mlActualTime.value) {
    const diff = mlActualTime.value - mlHumanEstimate.value
    const pct = (diff / mlHumanEstimate.value) * 100
    result.human_vs_actual = { diff: diff.toFixed(0), pct: pct.toFixed(0) }
  }
  if (est?.estimated_time_min && mlHumanEstimate.value) {
    const diff = mlHumanEstimate.value - est.estimated_time_min
    const pct = (diff / est.estimated_time_min) * 100
    result.ai_vs_human = { diff: diff.toFixed(0), pct: pct.toFixed(0) }
  }
  return result
})

// Helpers
function getStatusColor(status: string | null): string {
  switch (status) {
    case 'estimated': return 'var(--warn)'
    case 'calibrated': return 'var(--t3)'
    case 'verified': return 'var(--ok)'
    default: return 'var(--t3)'
  }
}

function getStatusLabel(status: string | null): string {
  switch (status) {
    case 'estimated': return 'Odhadnuto'
    case 'calibrated': return 'Kalibrováno'
    case 'verified': return 'Ověřeno'
    default: return '—'
  }
}

function syncFromEstimation(est: TimeVisionEstimation) {
  aiEstimation.value = est
  mlComplexity.value = (est.complexity as 'simple' | 'medium' | 'complex') ?? null
  mlPartType.value = (est.part_type as 'ROT' | 'PRI' | 'COMBINED') ?? null
  mlHumanEstimate.value = est.human_estimate_min ?? null
  mlActualTime.value = est.actual_time_min ?? null
  mlNotes.value = est.actual_notes ?? ''
}

async function saveCalibration() {
  if (!aiEstimation.value) return
  const est = aiEstimation.value
  const hasChanges =
    (mlComplexity.value ?? null) !== (est.complexity ?? null) ||
    (mlPartType.value ?? null) !== (est.part_type ?? null) ||
    (mlHumanEstimate.value && mlHumanEstimate.value > 0 && mlHumanEstimate.value !== est.human_estimate_min) ||
    (mlActualTime.value && mlActualTime.value > 0 && mlActualTime.value !== est.actual_time_min) ||
    mlNotes.value !== (est.actual_notes ?? '')
  if (!hasChanges) return

  mlSaving.value = true
  try {
    const payload: CalibrationUpdate = { version: est.version }
    if ((mlComplexity.value ?? null) !== (est.complexity ?? null)) payload.complexity = mlComplexity.value ?? undefined
    if ((mlPartType.value ?? null) !== (est.part_type ?? null)) payload.part_type = mlPartType.value ?? undefined
    if (mlHumanEstimate.value && mlHumanEstimate.value > 0) payload.human_estimate_min = mlHumanEstimate.value
    if (mlActualTime.value && mlActualTime.value > 0) payload.actual_time_min = mlActualTime.value
    if (mlNotes.value !== (est.actual_notes ?? '')) payload.actual_notes = mlNotes.value || null
    const updated = await calibrateEstimation(est.id, payload)
    syncFromEstimation(updated)
    uiStore.showSuccess('Kalibrace uložena')
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 409) {
      try { const fresh = await fetchEstimationById(est.id); syncFromEstimation(fresh) } catch { /* noop */ }
      uiStore.showWarning('Data byla změněna. Zkontrolujte hodnoty a uložte znovu.')
    } else {
      uiStore.showError('Nepodařilo se uložit kalibraci')
    }
  } finally {
    mlSaving.value = false
  }
}

// Watch partId — load TV estimation
watch(() => props.partId, async (newPartId) => {
  tvEstimation.value = null
  if (newPartId) {
    tvLoading.value = true
    try {
      tvEstimation.value = await fetchOpenAIEstimation('', newPartId)
    } catch { /* noop */ }
    finally { tvLoading.value = false }
  }
}, { immediate: true })

// Watch AI estimation ID — load calibration data
watch(firstAIEstimationId, async (newId) => {
  aiEstimation.value = null
  mlComplexity.value = null
  mlPartType.value = null
  mlHumanEstimate.value = null
  mlActualTime.value = null
  mlNotes.value = ''
  if (!newId) return
  mlLoading.value = true
  try {
    const est = await fetchEstimationById(newId)
    syncFromEstimation(est)
  } catch { /* noop */ }
  finally { mlLoading.value = false }
}, { immediate: true })
</script>

<template>
  <div class="tile-ai" data-testid="tile-ai">
    <!-- TimeVision Result -->
    <div v-if="tvEstimation || tvLoading" class="ai-section">
      <div class="section-header" @click="tvCollapsed = !tvCollapsed" data-testid="tv-section-toggle">
        <component :is="tvCollapsed ? ChevronRight : ChevronDown" :size="ICON_SIZE.SMALL" />
        <Sparkles :size="ICON_SIZE.SMALL" class="section-icon tv" />
        <span class="section-title">AI odhad</span>
        <template v-if="tvEstimation">
          <span class="status-badge" :style="{ color: getStatusColor(tvEstimation.status) }">
            <CheckCircle v-if="tvEstimation.status === 'verified'" :size="ICON_SIZE.SMALL" />
            <Clock v-else :size="ICON_SIZE.SMALL" />
            {{ getStatusLabel(tvEstimation.status) }}
          </span>
        </template>
      </div>
      <div v-if="!tvCollapsed" class="section-body">
        <div v-if="tvLoading" class="section-loading"><div class="spinner" /></div>
        <template v-else-if="tvEstimation">
          <div class="tv-summary">
            <div class="tv-item highlight">
              <label>AI čas</label>
              <span class="tv-time">{{ tvEstimation.estimated_time_min?.toFixed(1) ?? '—' }} min</span>
            </div>
            <div class="tv-item"><label>Typ</label><span>{{ tvEstimation.part_type ?? '—' }}</span></div>
            <div class="tv-item"><label>Složitost</label><span>{{ tvEstimation.complexity ?? '—' }}</span></div>
            <div class="tv-item"><label>Spolehlivost</label><span :class="'confidence-' + tvEstimation.confidence">{{ tvEstimation.confidence ?? '—' }}</span></div>
            <div v-if="tvEstimation.material_detected" class="tv-item"><label>Materiál</label><span>{{ tvEstimation.material_detected }}</span></div>
            <div v-if="tvEstimation.ai_provider" class="tv-item"><label>Model</label><span>{{ tvEstimation.ai_provider === 'openai_ft' ? 'Fine-tuned' : 'GPT-4o' }}</span></div>
          </div>
          <div v-if="tvBreakdown.length > 0" class="tv-breakdown">
            <div v-for="item in tvBreakdown" :key="item.operation" class="tv-row">
              <span>{{ item.operation }}</span>
              <span class="tv-row-time">{{ item.time_min }} min</span>
            </div>
          </div>
          <div v-if="tvEstimation.estimation_reasoning" class="tv-reasoning">
            {{ tvEstimation.estimation_reasoning }}
          </div>
        </template>
      </div>
    </div>

    <!-- Model Learning -->
    <div v-if="hasAIEstimation" class="ai-section">
      <div class="section-header" @click="mlCollapsed = !mlCollapsed" data-testid="ml-section-toggle">
        <component :is="mlCollapsed ? ChevronRight : ChevronDown" :size="ICON_SIZE.SMALL" />
        <GraduationCap :size="ICON_SIZE.SMALL" class="section-icon ml" />
        <span class="section-title">Učení modelu</span>
        <span v-if="aiEstimation" class="status-badge" :style="{ color: getStatusColor(aiEstimation.status) }">
          <CheckCircle v-if="aiEstimation.status === 'verified'" :size="ICON_SIZE.SMALL" />
          <Clock v-else :size="ICON_SIZE.SMALL" />
          {{ getStatusLabel(aiEstimation.status) }}
        </span>
      </div>
      <template v-if="!mlCollapsed">
        <div v-if="mlLoading" class="section-loading"><div class="spinner" /></div>
        <template v-else-if="aiEstimation">
          <div class="ml-body">
            <div class="ml-times">
              <div class="ml-col teal">
                <label>AI odhad</label>
                <div class="ml-wrap">
                  <input type="number" :value="aiEstimation.estimated_time_min?.toFixed(1)" disabled class="ml-input" data-testid="ml-ai-time" />
                  <span class="ml-unit">min</span>
                </div>
              </div>
              <div class="ml-col blue">
                <label>Můj odhad</label>
                <div class="ml-wrap">
                  <input type="number" step="0.1" min="0" v-model.number="mlHumanEstimate" class="ml-input" placeholder="—" data-testid="ml-human-estimate" />
                  <span class="ml-unit">min</span>
                </div>
              </div>
              <div class="ml-col amber">
                <label>Skutečný čas</label>
                <div class="ml-wrap">
                  <input type="number" step="0.1" min="0" v-model.number="mlActualTime" class="ml-input" placeholder="—" data-testid="ml-actual-time" />
                  <span class="ml-unit">min</span>
                </div>
              </div>
              <div class="ml-col grey">
                <label>Na operaci</label>
                <div class="ml-wrap">
                  <input type="number" :value="currentOperationTime?.toFixed(1)" disabled class="ml-input" data-testid="ml-op-time" />
                  <span class="ml-unit">min</span>
                </div>
              </div>
            </div>
            <div v-if="deviation.ai_vs_actual || deviation.human_vs_actual || deviation.ai_vs_human" class="ml-deviations">
              <div v-if="deviation.ai_vs_actual" class="dev-item">
                <label>AI vs Skut.</label>
                <span :class="Number(deviation.ai_vs_actual.diff) > 0 ? 'over' : 'under'">
                  {{ Number(deviation.ai_vs_actual.diff) > 0 ? '+' : '' }}{{ deviation.ai_vs_actual.diff }} ({{ Number(deviation.ai_vs_actual.pct) > 0 ? '+' : '' }}{{ deviation.ai_vs_actual.pct }}%)
                </span>
              </div>
              <div v-if="deviation.human_vs_actual" class="dev-item">
                <label>Odhad vs Skut.</label>
                <span :class="Number(deviation.human_vs_actual.diff) > 0 ? 'over' : 'under'">
                  {{ Number(deviation.human_vs_actual.diff) > 0 ? '+' : '' }}{{ deviation.human_vs_actual.diff }} ({{ Number(deviation.human_vs_actual.pct) > 0 ? '+' : '' }}{{ deviation.human_vs_actual.pct }}%)
                </span>
              </div>
              <div v-if="deviation.ai_vs_human" class="dev-item">
                <label>Odhad vs AI</label>
                <span :class="Number(deviation.ai_vs_human.diff) > 0 ? 'over' : 'under'">
                  {{ Number(deviation.ai_vs_human.diff) > 0 ? '+' : '' }}{{ deviation.ai_vs_human.diff }} ({{ Number(deviation.ai_vs_human.pct) > 0 ? '+' : '' }}{{ deviation.ai_vs_human.pct }}%)
                </span>
              </div>
            </div>
            <div class="ml-actions">
              <select v-model="mlPartType" class="ml-select" title="Typ dílu" data-testid="ml-part-type">
                <option :value="null">—</option>
                <option value="ROT">ROT</option>
                <option value="PRI">PRI</option>
                <option value="COMBINED">COMB</option>
              </select>
              <select v-model="mlComplexity" class="ml-select" title="Složitost" data-testid="ml-complexity">
                <option :value="null">—</option>
                <option value="simple">S</option>
                <option value="medium">M</option>
                <option value="complex">C</option>
              </select>
              <input type="text" v-model="mlNotes" class="ml-notes" placeholder="Poznámky..." data-testid="ml-notes" />
              <button class="ml-save" @click="saveCalibration" :disabled="mlSaving" data-testid="ml-save-btn">
                <Save :size="ICON_SIZE.SMALL" />
                {{ mlSaving ? '...' : 'Uložit' }}
              </button>
            </div>
          </div>
        </template>
      </template>
    </div>

    <!-- Empty state -->
    <div v-if="!tvEstimation && !tvLoading && !hasAIEstimation" class="empty-state">
      <p>Žádná AI data pro tento díl</p>
    </div>
  </div>
</template>

<style scoped>
.tile-ai {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 6px;
  height: 100%;
  overflow-y: auto;
}

/* Sections */
.ai-section {
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px var(--pad);
  cursor: pointer;
  user-select: none;
  background: var(--surface);
  border-radius: var(--r);
}

.section-header:hover {
  background: var(--raised);
}

.section-icon.tv { color: var(--red); }
.section-icon.ml { color: var(--ok); }

.section-title {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs);
  font-weight: 500;
  margin-left: auto;
}

.section-body {
  padding: 6px var(--pad);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.section-loading {
  display: flex;
  justify-content: center;
  padding: var(--pad);
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--b2);
  border-top-color: var(--ok);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* TV Summary */
.tv-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
}

.tv-item {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.tv-item label {
  font-size: var(--fs);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: var(--t3);
}

.tv-item span {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t1);
}

.tv-item.highlight label { color: var(--ok); }

.tv-time {
  font-size: 16px;
  font-weight: 700;
  color: var(--ok);
  font-family: var(--mono);
}

.confidence-high { color: var(--ok); }
.confidence-medium { color: var(--warn); }
.confidence-low { color: var(--err); }

.tv-breakdown {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--raised);
  border-radius: var(--rs);
  padding: 4px 6px;
}

.tv-row {
  display: flex;
  justify-content: space-between;
  padding: 2px 0;
  font-size: var(--fs);
  color: var(--t3);
}

.tv-row-time {
  font-family: var(--mono);
  font-weight: 500;
  color: var(--t1);
}

.tv-reasoning {
  font-size: var(--fs);
  color: var(--t3);
  line-height: 1.4;
  padding: 4px 6px;
  background: var(--raised);
  border-radius: var(--rs);
  white-space: pre-wrap;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ML Body */
.ml-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 0 var(--pad) 6px;
}

.ml-times {
  display: flex;
  gap: 6px;
}

.ml-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ml-col label {
  font-size: var(--fs);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.ml-col.teal label { color: var(--ok); }
.ml-col.blue label { color: var(--t3); }
.ml-col.amber label { color: var(--warn); }
.ml-col.grey label { color: var(--t3); }

.ml-wrap {
  display: flex;
  align-items: center;
  gap: 2px;
}

.ml-input {
  width: 100%;
  padding: 2px 4px;
  background: var(--ground);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  font-weight: 600;
  font-family: var(--mono);
  text-align: right;
}

.ml-input:disabled { opacity: 0.8; cursor: not-allowed; }
.ml-input:focus { outline: none; border-color: var(--b3); }

.ml-unit {
  font-size: var(--fs);
  color: var(--t3);
  flex-shrink: 0;
}

/* Deviations */
.ml-deviations {
  display: flex;
  flex-wrap: wrap;
  gap: 4px var(--pad);
}

.dev-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.dev-item label {
  font-size: var(--fs);
  color: var(--t3);
  text-transform: uppercase;
}

.dev-item span {
  font-size: var(--fs);
  font-weight: 600;
  font-family: var(--mono);
}

.over { color: var(--err); }
.under { color: var(--ok); }

/* ML Actions */
.ml-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ml-select {
  padding: 2px 4px;
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  font-size: var(--fs);
  background: var(--ground);
  color: var(--t1);
  flex-shrink: 0;
  max-width: 64px;
}

.ml-notes {
  flex: 1;
  min-width: 0;
  padding: 2px 6px;
  background: var(--ground);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  font-family: inherit;
}

.ml-notes:focus {
  outline: none;
  border-color: var(--b3);
}

.ml-save {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  background: var(--ok);
  color: var(--t1);
  border: none;
  border-radius: var(--rs);
  font-size: var(--fs);
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.1s;
  flex-shrink: 0;
}

.ml-save:hover:not(:disabled) { opacity: 0.9; }
.ml-save:disabled { opacity: 0.5; cursor: not-allowed; }

/* Empty state */
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--t4);
  font-size: var(--fs);
}
</style>
