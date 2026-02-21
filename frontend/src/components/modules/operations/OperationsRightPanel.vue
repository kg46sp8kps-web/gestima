<script setup lang="ts">
/**
 * Operations Right Panel Component (BUILDING BLOCK - L-039)
 * Reusable right panel for PartOperations + PartTechnology modules
 *
 * Contains:
 * - MaterialInputSelector (dropdown + add button)
 * - OperationsHeader (when standalone)
 * - OperationsDetailPanel (operations table)
 * - OperationDetailPanel (feature detail split)
 */

import { ref, computed, watch } from 'vue'
import { useOperationsStore } from '@/stores/operations'
import { useMaterialsStore } from '@/stores/materials'
import { useUiStore } from '@/stores/ui'
import { generateTechnology } from '@/api/technology'
import { fetchEstimationById, calibrateEstimation, fetchOpenAIEstimation } from '@/api/time-vision'
import type { CalibrationUpdate } from '@/api/time-vision'
import type { TimeVisionEstimation, OperationBreakdown } from '@/types/time-vision'
import type { LinkingGroup } from '@/stores/windows'
import type { Part } from '@/types/part'
import type { Operation } from '@/types/operation'
import { GraduationCap, Sparkles, Save, CheckCircle, Clock, ChevronRight, ChevronDown, AlertTriangle, Plus } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

import OperationsHeader from './OperationsHeader.vue'
import OperationsDetailPanel from './OperationsDetailPanel.vue'
import MaterialInputSelectorV2 from './MaterialInputSelectorV2.vue'
import AIEstimatePanel from './AIEstimatePanel.vue'
import ProductionHistoryPanel from '../production/ProductionHistoryPanel.vue'

interface Props {
  part: Part | null
  partId: number | null
  linkingGroup?: LinkingGroup
  showHeader?: boolean  // Show OperationsHeader (true for standalone, false for linked)
}

const props = withDefaults(defineProps<Props>(), {
  linkingGroup: null,
  showHeader: true
})

// State
const detailPanelRef = ref<InstanceType<typeof OperationsDetailPanel> | null>(null)
const showAIPanel = ref(false)
const productionHistoryCollapsed = ref(true)
const mlCollapsed = ref(true)
const materialCollapsed = ref(false)
const operationsCollapsed = ref(false)

const operationsStore = useOperationsStore()
const materialsStore = useMaterialsStore()
const uiStore = useUiStore()

// Model Learning state
const aiEstimation = ref<TimeVisionEstimation | null>(null)
const mlComplexity = ref<'simple' | 'medium' | 'complex' | null>(null)
const mlPartType = ref<'ROT' | 'PRI' | 'COMBINED' | null>(null)
const mlHumanEstimate = ref<number | null>(null)
const mlActualTime = ref<number | null>(null)
const mlNotes = ref<string>('')
const mlSaving = ref(false)
const mlLoading = ref(false)

// TimeVision estimation state (independent of ai_estimation_id — loads by part_id)
const tvEstimation = ref<TimeVisionEstimation | null>(null)
const tvCollapsed = ref(true)
const tvLoading = ref(false)

const tvBreakdown = computed<OperationBreakdown[]>(() => {
  if (!tvEstimation.value?.estimation_breakdown_json) return []
  try {
    return JSON.parse(tvEstimation.value.estimation_breakdown_json)
  } catch {
    return []
  }
})

// Computed
const operationsCount = computed(() => detailPanelRef.value?.operationsCount || 0)
const materialsCount = computed(() => materialsStore.getContext(props.linkingGroup).materialInputs.length)

const hasAIEstimation = computed(() => {
  const ops = operationsStore.getContext(props.linkingGroup).operations
  return ops.some(op => op.ai_estimation_id != null)
})

const firstAIOperation = computed(() => {
  const ops = operationsStore.getContext(props.linkingGroup).operations
  return ops.find(o => o.ai_estimation_id != null) ?? null
})

const firstAIEstimationId = computed(() => firstAIOperation.value?.ai_estimation_id ?? null)

// Current operation time (for bidirectional display)
const currentOperationTime = computed(() => firstAIOperation.value?.operation_time_min ?? null)

// Auto-regenerate technology when material changes (recalculates OP10 cutting time)
const materialInputs = computed(() => materialsStore.getContext(props.linkingGroup).materialInputs)
const regenerating = ref(false)
let materialWatchInitialized = false

watch(materialInputs, async () => {
  // Skip initial load — only react to user changes
  if (!materialWatchInitialized) {
    materialWatchInitialized = true
    return
  }
  if (!firstAIEstimationId.value || !props.partId || regenerating.value) return

  regenerating.value = true
  try {
    await generateTechnology({
      estimation_id: firstAIEstimationId.value,
      part_id: props.partId,
    })
    await operationsStore.loadOperations(props.partId, props.linkingGroup)
  } catch {
    // Silent — user can click "Aktualizovat technologii" manually
  } finally {
    regenerating.value = false
  }
}, { deep: true })

// Smooth transition on part switch — dim content while loading instead of flash
const operationsLoading = computed(() => operationsStore.getContext(props.linkingGroup).loading)
const materialsLoading = computed(() => materialsStore.getContext(props.linkingGroup).loadingInputs)
const isTransitioning = computed(() => {
  // Only dim when switching parts (not on initial load)
  const opsCtx = operationsStore.getContext(props.linkingGroup)
  return (operationsLoading.value || materialsLoading.value) && !opsCtx.initialLoading
})

watch(() => props.partId, async (newPartId, oldPartId) => {
  // Reset UI state only on actual part switch (not initial load)
  if (oldPartId !== undefined) {
    showAIPanel.value = false
    materialWatchInitialized = false
    selectedWorkCenterType.value = null
  }

  // Load TimeVision estimation by part_id (works for both AI-generated and Infor-imported ops)
  tvEstimation.value = null
  if (newPartId) {
    tvLoading.value = true
    try {
      // fetchOpenAIEstimation with partId uses /estimations/by-part/{id} endpoint
      tvEstimation.value = await fetchOpenAIEstimation('', newPartId)
    } catch {
      // No estimation available — silent
    } finally {
      tvLoading.value = false
    }
  }
}, { immediate: true })
watch(operationsCount, (count) => {
  if (count === 0) showAIPanel.value = false
})

// Status helpers
function getStatusColor(status: string | null): string {
  switch (status) {
    case 'estimated': return 'var(--color-warning)'
    case 'calibrated': return 'var(--color-info)'
    case 'verified': return 'var(--color-success)'
    default: return 'var(--text-muted)'
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

// Deviations (same as TimeVisionActualTimeForm — with %)
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

// Watch for AI estimation changes — load full estimation by ID
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
  } catch {
    // Silent fail — estimation may have been deleted
  } finally {
    mlLoading.value = false
  }
}, { immediate: true })

// Sync local refs from estimation (reusable for initial load + conflict re-fetch)
function syncFromEstimation(est: TimeVisionEstimation) {
  aiEstimation.value = est
  mlComplexity.value = (est.complexity as 'simple' | 'medium' | 'complex') ?? null
  mlPartType.value = (est.part_type as 'ROT' | 'PRI' | 'COMBINED') ?? null
  mlHumanEstimate.value = est.human_estimate_min ?? null
  mlActualTime.value = est.actual_time_min ?? null
  mlNotes.value = est.actual_notes ?? ''
}

// Save calibration (clone of TimeVisionActualTimeForm.handleSave logic)
async function saveCalibration() {
  if (!aiEstimation.value) return

  const est = aiEstimation.value

  // Fix #2: Compare via !== (not truthy guard) so null reset is detected
  const hasChanges =
    (mlComplexity.value ?? null) !== (est.complexity ?? null) ||
    (mlPartType.value ?? null) !== (est.part_type ?? null) ||
    (mlHumanEstimate.value && mlHumanEstimate.value > 0 && mlHumanEstimate.value !== est.human_estimate_min) ||
    (mlActualTime.value && mlActualTime.value > 0 && mlActualTime.value !== est.actual_time_min) ||
    mlNotes.value !== (est.actual_notes ?? '')

  if (!hasChanges) return

  mlSaving.value = true
  try {
    const payload: CalibrationUpdate = {
      version: est.version,
    }

    if ((mlComplexity.value ?? null) !== (est.complexity ?? null)) {
      payload.complexity = mlComplexity.value ?? undefined
    }
    if ((mlPartType.value ?? null) !== (est.part_type ?? null)) {
      payload.part_type = mlPartType.value ?? undefined
    }
    if (mlHumanEstimate.value && mlHumanEstimate.value > 0) {
      payload.human_estimate_min = mlHumanEstimate.value
    }
    if (mlActualTime.value && mlActualTime.value > 0) {
      payload.actual_time_min = mlActualTime.value
    }
    if (mlNotes.value !== (est.actual_notes ?? '')) {
      payload.actual_notes = mlNotes.value || null
    }

    const updated = await calibrateEstimation(est.id, payload)
    syncFromEstimation(updated)
    uiStore.showSuccess('Kalibrace uložena')
  } catch (err: unknown) {
    // Fix #1: Handle 409 version conflict — re-fetch fresh data + notify user
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 409) {
      try {
        const fresh = await fetchEstimationById(est.id)
        syncFromEstimation(fresh)
      } catch { /* re-fetch failed — keep stale data */ }
      uiStore.showWarning('Data byla změněna. Zkontrolujte hodnoty a uložte znovu.')
    } else {
      uiStore.showError('Nepodařilo se uložit kalibraci')
    }
  } finally {
    mlSaving.value = false
  }
}

const emit = defineEmits<{
  'refresh-part': []
  'open-material': []
  'open-operations': []
  'open-pricing': []
  'open-drawing': [drawingId?: number]
}>()

// Handle select operation — filter production history by machine type
const selectedWorkCenterType = ref<string | null>(null)

function handleSelectOperation(op: Operation | null) {
  if (!op?.work_center_id) {
    selectedWorkCenterType.value = null
    return
  }
  const wc = operationsStore.workCenters.find(w => w.id === op.work_center_id)
  selectedWorkCenterType.value = wc?.work_center_type ?? null
}

// Expose operationsCount for parent
defineExpose({
  operationsCount: computed(() => operationsCount.value)
})
</script>

<template>
  <div class="operations-right-panel" :class="{ 'is-transitioning': isTransitioning }">
    <!-- OPERATIONS HEADER (when standalone) -->
    <OperationsHeader
      v-if="showHeader"
      :part="part"
      :operationsCount="operationsCount"
      :hasAIEstimation="hasAIEstimation"
      @refresh="emit('refresh-part')"
      @open-material="emit('open-material')"
      @open-operations="emit('open-operations')"
      @open-pricing="emit('open-pricing')"
      @open-drawing="(id?: number) => emit('open-drawing', id)"
    />

    <!-- MATERIAL RIBBON (collapsible) -->
    <div class="section-ribbon">
      <div class="section-ribbon-header" @click="materialCollapsed = !materialCollapsed">
        <component :is="materialCollapsed ? ChevronRight : ChevronDown" :size="ICON_SIZE.SMALL" class="ribbon-chevron" />
        <span class="section-ribbon-title">Materiál</span>
        <span v-if="materialsCount > 0" class="section-ribbon-badge">{{ materialsCount }}</span>
      </div>
      <div v-if="!materialCollapsed" class="section-ribbon-body">
        <MaterialInputSelectorV2
          :partId="partId"
          :linkingGroup="linkingGroup"
          :hideHeader="true"
        />
      </div>
    </div>

    <!-- OPERATIONS RIBBON (collapsible) -->
    <div class="section-ribbon operations-ribbon" :class="{ 'ribbon-expanded': !operationsCollapsed }">
      <div class="section-ribbon-header" @click="operationsCollapsed = !operationsCollapsed">
        <component :is="operationsCollapsed ? ChevronRight : ChevronDown" :size="ICON_SIZE.SMALL" class="ribbon-chevron" />
        <span class="section-ribbon-title">Operace</span>
        <span v-if="operationsCount > 0" class="section-ribbon-badge">{{ operationsCount }}</span>
        <span
          v-if="detailPanelRef?.hasAIEstimation"
          class="ai-info-badge"
          :class="{ 'is-modified': detailPanelRef?.aiTimeModified }"
          :title="detailPanelRef?.aiTimeModified ? 'AI čas byl upraven' : 'Operace obsahuje AI odhad'"
        >
          <AlertTriangle :size="ICON_SIZE.SMALL" />
        </span>
        <div class="ribbon-actions" @click.stop>
          <button
            class="icon-btn"
            @click="showAIPanel = !showAIPanel"
            :disabled="!partId"
            title="AI odhad času z výkresu"
          >
            <Sparkles :size="ICON_SIZE.STANDARD" />
          </button>
          <button
            class="icon-btn"
            @click="detailPanelRef?.addOperation()"
            :disabled="!partId"
            title="Přidat operaci"
          >
            <Plus :size="ICON_SIZE.STANDARD" />
          </button>
        </div>
      </div>
      <div v-if="!operationsCollapsed" class="section-ribbon-body operations-body">
        <div class="operations-split">
          <div class="operations-main">
            <OperationsDetailPanel
              ref="detailPanelRef"
              :partId="partId"
              :part="part"
              :linkingGroup="linkingGroup"
              :hideHeader="true"
              @select-operation="handleSelectOperation"
              @toggle-ai-panel="showAIPanel = !showAIPanel"
            />
          </div>

          <!-- AI ESTIMATE PANEL (collapsible) -->
          <div v-if="showAIPanel" class="ai-panel">
            <AIEstimatePanel
              :partId="partId"
              :part="part"
              :linkingGroup="linkingGroup"
              @close="showAIPanel = false"
              @operation-created="showAIPanel = false; detailPanelRef?.resetAIWarning()"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- BOTTOM PANELS (scrollable container — operations stay visible) -->
    <div class="bottom-panels">
    <!-- TIMEVISION RESULT (collapsible, above production history) -->
    <div v-if="tvEstimation || tvLoading" class="tv-ribbon">
      <div class="tv-header" @click="tvCollapsed = !tvCollapsed">
        <component :is="tvCollapsed ? ChevronRight : ChevronDown" :size="ICON_SIZE.SMALL" class="tv-chevron" />
        <Sparkles :size="ICON_SIZE.SMALL" class="tv-icon" />
        <span class="tv-title">AI odhad</span>
        <!-- Collapsed summary -->
        <template v-if="tvEstimation">
          <span class="tv-status-badge" :style="{ color: getStatusColor(tvEstimation.status) }">
            <CheckCircle v-if="tvEstimation.status === 'verified'" :size="ICON_SIZE.SMALL" />
            <Clock v-else :size="ICON_SIZE.SMALL" />
            {{ getStatusLabel(tvEstimation.status) }}
          </span>
          <span v-if="tvCollapsed" class="tv-collapsed-summary">
            <span class="tv-cs-item teal">{{ tvEstimation.estimated_time_min?.toFixed(1) ?? '—' }} min</span>
            <span class="tv-cs-sep">|</span>
            <span class="tv-cs-item">{{ tvEstimation.part_type ?? '—' }}</span>
            <span class="tv-cs-sep">|</span>
            <span class="tv-cs-item">{{ tvEstimation.complexity ?? '—' }}</span>
            <span v-if="tvEstimation.confidence" class="tv-cs-sep">|</span>
            <span v-if="tvEstimation.confidence" class="tv-cs-item" :class="'confidence-' + tvEstimation.confidence">{{ tvEstimation.confidence }}</span>
          </span>
        </template>
      </div>

      <div v-if="!tvCollapsed" class="tv-body">
        <div v-if="tvLoading" class="tv-loading">
          <div class="ml-spinner"></div>
        </div>

        <template v-else-if="tvEstimation">
          <!-- Summary grid -->
          <div class="tv-summary">
            <div class="tv-summary-item highlight">
              <label>AI čas</label>
              <span class="tv-time-value">{{ tvEstimation.estimated_time_min?.toFixed(1) ?? '—' }} min</span>
            </div>
            <div class="tv-summary-item">
              <label>Typ</label>
              <span>{{ tvEstimation.part_type ?? '—' }}</span>
            </div>
            <div class="tv-summary-item">
              <label>Složitost</label>
              <span>{{ tvEstimation.complexity ?? '—' }}</span>
            </div>
            <div class="tv-summary-item">
              <label>Spolehlivost</label>
              <span :class="'confidence-' + tvEstimation.confidence">{{ tvEstimation.confidence ?? '—' }}</span>
            </div>
            <div v-if="tvEstimation.material_detected" class="tv-summary-item">
              <label>Materiál</label>
              <span>{{ tvEstimation.material_detected }}</span>
            </div>
            <div v-if="tvEstimation.ai_provider" class="tv-summary-item">
              <label>Model</label>
              <span>{{ tvEstimation.ai_provider === 'openai_ft' ? 'Fine-tuned' : 'GPT-4o' }}</span>
            </div>
          </div>

          <!-- Breakdown table -->
          <div v-if="tvBreakdown.length > 0" class="tv-breakdown">
            <div v-for="item in tvBreakdown" :key="item.operation" class="tv-breakdown-row">
              <span class="tv-op-name">{{ item.operation }}</span>
              <span class="tv-op-time">{{ item.time_min }} min</span>
            </div>
          </div>

          <!-- Reasoning (truncated) -->
          <div v-if="tvEstimation.estimation_reasoning" class="tv-reasoning">
            <span class="tv-reasoning-text">{{ tvEstimation.estimation_reasoning }}</span>
          </div>
        </template>
      </div>
    </div>

    <!-- PRODUCTION HISTORY (collapsible, always grouped by Job) -->
    <ProductionHistoryPanel
      v-if="partId"
      :partId="partId"
      :workCenterType="selectedWorkCenterType"
      :collapsed="productionHistoryCollapsed"
      @update:collapsed="productionHistoryCollapsed = $event"
    />

    <!-- MODEL LEARNING RIBBON (collapsible, like ProductionHistory) -->
    <div v-if="hasAIEstimation" class="ml-ribbon">
      <div class="ml-header" @click="mlCollapsed = !mlCollapsed">
        <component :is="mlCollapsed ? ChevronRight : ChevronDown" :size="ICON_SIZE.SMALL" class="ml-chevron" />
        <GraduationCap :size="ICON_SIZE.SMALL" class="ml-icon" />
        <span class="ml-title">Učení modelu</span>
        <!-- Status badge -->
        <span
          v-if="aiEstimation"
          class="ml-status-badge"
          :style="{ color: getStatusColor(aiEstimation.status) }"
        >
          <CheckCircle v-if="aiEstimation.status === 'verified'" :size="ICON_SIZE.SMALL" />
          <Clock v-else :size="ICON_SIZE.SMALL" />
          {{ getStatusLabel(aiEstimation.status) }}
        </span>
        <!-- Collapsed summary: show times inline -->
        <span v-if="mlCollapsed && aiEstimation" class="ml-collapsed-summary">
          <span class="ml-cs-item teal">{{ aiEstimation.estimated_time_min?.toFixed(1) ?? '—' }}</span>
          <span class="ml-cs-sep">/</span>
          <span class="ml-cs-item blue">{{ mlHumanEstimate?.toFixed(1) ?? '—' }}</span>
          <span class="ml-cs-sep">/</span>
          <span class="ml-cs-item amber">{{ mlActualTime?.toFixed(1) ?? '—' }}</span>
          <span class="ml-cs-unit">min</span>
        </span>
      </div>

      <template v-if="!mlCollapsed">
        <div v-if="mlLoading" class="ml-loading">
          <div class="ml-spinner"></div>
        </div>

        <template v-else-if="aiEstimation">
          <div class="ml-body">
            <!-- 4 times in row -->
            <div class="ml-times">
              <div class="ml-time-col teal">
                <label>AI odhad</label>
                <div class="ml-input-wrap">
                  <input type="number" :value="aiEstimation.estimated_time_min?.toFixed(1)" disabled class="ml-input" />
                  <span class="ml-unit">min</span>
                </div>
              </div>
              <div class="ml-time-col blue">
                <label>Můj odhad</label>
                <div class="ml-input-wrap">
                  <input type="number" step="0.1" min="0" v-model.number="mlHumanEstimate" class="ml-input" placeholder="—" />
                  <span class="ml-unit">min</span>
                </div>
              </div>
              <div class="ml-time-col amber">
                <label>Skutečný čas</label>
                <div class="ml-input-wrap">
                  <input type="number" step="0.1" min="0" v-model.number="mlActualTime" class="ml-input" placeholder="—" />
                  <span class="ml-unit">min</span>
                </div>
              </div>
              <div class="ml-time-col grey">
                <label>Na operaci</label>
                <div class="ml-input-wrap">
                  <input type="number" :value="currentOperationTime?.toFixed(1)" disabled class="ml-input" />
                  <span class="ml-unit">min</span>
                </div>
              </div>
            </div>

            <!-- Deviations inline -->
            <div v-if="deviation.ai_vs_actual || deviation.human_vs_actual || deviation.ai_vs_human" class="ml-deviation-grid">
              <div v-if="deviation.ai_vs_actual" class="ml-deviation-item">
                <label>AI vs Skut.</label>
                <span :class="Number(deviation.ai_vs_actual.diff) > 0 ? 'over' : 'under'">
                  {{ Number(deviation.ai_vs_actual.diff) > 0 ? '+' : '' }}{{ deviation.ai_vs_actual.diff }} ({{ Number(deviation.ai_vs_actual.pct) > 0 ? '+' : '' }}{{ deviation.ai_vs_actual.pct }}%)
                </span>
              </div>
              <div v-if="deviation.human_vs_actual" class="ml-deviation-item">
                <label>Odhad vs Skut.</label>
                <span :class="Number(deviation.human_vs_actual.diff) > 0 ? 'over' : 'under'">
                  {{ Number(deviation.human_vs_actual.diff) > 0 ? '+' : '' }}{{ deviation.human_vs_actual.diff }} ({{ Number(deviation.human_vs_actual.pct) > 0 ? '+' : '' }}{{ deviation.human_vs_actual.pct }}%)
                </span>
              </div>
              <div v-if="deviation.ai_vs_human" class="ml-deviation-item">
                <label>Odhad vs AI</label>
                <span :class="Number(deviation.ai_vs_human.diff) > 0 ? 'over' : 'under'">
                  {{ Number(deviation.ai_vs_human.diff) > 0 ? '+' : '' }}{{ deviation.ai_vs_human.diff }} ({{ Number(deviation.ai_vs_human.pct) > 0 ? '+' : '' }}{{ deviation.ai_vs_human.pct }}%)
                </span>
              </div>
            </div>

            <!-- Metadata + Notes + Save (compact row) -->
            <div class="ml-compact-row">
              <select v-model="mlPartType" class="ml-select ml-select-narrow" title="Typ dílu">
                <option :value="null">—</option>
                <option value="ROT">ROT</option>
                <option value="PRI">PRI</option>
                <option value="COMBINED">COMB</option>
              </select>
              <select v-model="mlComplexity" class="ml-select ml-select-narrow" title="Složitost">
                <option :value="null">—</option>
                <option value="simple">S</option>
                <option value="medium">M</option>
                <option value="complex">C</option>
              </select>
              <input
                type="text"
                v-model="mlNotes"
                class="ml-notes-inline"
                placeholder="Poznámky..."
              />
              <button class="ml-save-btn" @click="saveCalibration" :disabled="mlSaving">
                <Save :size="ICON_SIZE.SMALL" />
                {{ mlSaving ? '...' : 'Uložit' }}
              </button>
            </div>
          </div>
        </template>
      </template>
    </div>
    </div><!-- /bottom-panels -->
  </div>
</template>

<style scoped>
/* === PANEL LAYOUT === */
.operations-right-panel {
  transition: opacity 0.15s ease;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* Smooth transition on part switch — brief fade instead of jarring content swap */
.operations-right-panel {
  transition: opacity 0.15s ease;
}
.operations-right-panel.is-transitioning {
  opacity: 0.6;
  pointer-events: none;
}

/* === SECTION RIBBONS (Material + Operations — collapsible) === */
.section-ribbon {
  flex-shrink: 0;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-surface);
}

.operations-ribbon.ribbon-expanded {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.section-ribbon-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  user-select: none;
}

.section-ribbon-header:hover {
  background: var(--bg-raised);
}

.ribbon-chevron {
  color: var(--text-tertiary);
  flex-shrink: 0;
  transition: transform 0.2s;
}

.section-ribbon-title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.section-ribbon-badge {
  margin-left: var(--space-1);
  padding: 0 var(--space-1);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  font-weight: var(--font-semibold);
  color: var(--text-tertiary);
  background: var(--bg-muted);
  border-radius: var(--radius-sm);
}

.ribbon-actions {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-left: auto;
}

.ai-info-badge {
  display: flex;
  align-items: center;
  color: var(--status-ok);
  flex-shrink: 0;
}

.ai-info-badge.is-modified {
  color: var(--color-warning);
}

.section-ribbon-body {
  border-top: 1px solid var(--border-subtle);
}

.operations-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

/* === OPERATIONS SPLIT (Operations | Features) === */
.operations-split {
  display: flex;
  flex: 1;
  min-height: 200px;
  overflow: hidden;
}

/* === BOTTOM PANELS (scrollable, max 40% height) === */
.bottom-panels {
  flex-shrink: 1;
  max-height: 40%;
  overflow-y: auto;
  border-top: 1px solid var(--border-default);
}

.operations-main {
  flex: 1;
  overflow: hidden;
}

.ai-panel {
  flex-shrink: 0;
  width: 340px;
  border-left: 1px solid var(--border-default);
  overflow: hidden;
}

/* === MODEL LEARNING RIBBON (collapsible) === */
.ml-ribbon {
  border-top: 1px solid var(--border-default);
  background: var(--bg-surface);
}

.ml-header {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  user-select: none;
  background: var(--bg-surface);
}

.ml-header:hover { background: var(--bg-raised); }

.ml-chevron {
  color: var(--text-tertiary);
  transition: transform 0.2s;
  flex-shrink: 0;
}

.ml-icon {
  color: var(--status-ok);
  flex-shrink: 0;
}

.ml-title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.ml-status-badge {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  margin-left: auto;
}

/* Collapsed summary: inline times */
.ml-collapsed-summary {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: var(--space-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.ml-cs-item.teal { color: var(--status-ok); }
.ml-cs-item.blue { color: var(--color-info); }
.ml-cs-item.amber { color: var(--status-warn); }
.ml-cs-sep { color: var(--text-tertiary); }
.ml-cs-unit { color: var(--text-tertiary); margin-left: 2px; }

.ml-loading {
  display: flex;
  justify-content: center;
  padding: var(--space-2);
}

.ml-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-default);
  border-top-color: var(--status-ok);
  border-radius: 50%;
  animation: ml-spin 0.8s linear infinite;
}

@keyframes ml-spin {
  to { transform: rotate(360deg); }
}

.ml-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: 0 var(--space-3) var(--space-2);
}

.ml-times {
  display: flex;
  gap: var(--space-2);
}

.ml-time-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ml-time-col label {
  font-size: 9px;
  font-weight: var(--font-medium);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.ml-time-col.teal label { color: var(--status-ok); }
.ml-time-col.blue label { color: var(--color-info); }
.ml-time-col.amber label { color: var(--status-warn); }
.ml-time-col.grey label { color: var(--text-secondary); }

.ml-input-wrap {
  display: flex;
  align-items: center;
  gap: 2px;
}

.ml-input {
  width: 100%;
  padding: 2px var(--space-1);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  font-family: var(--font-mono);
  text-align: right;
}

.ml-time-col.teal .ml-input {
  background: rgba(20, 184, 166, 0.08);
  border-color: rgba(20, 184, 166, 0.3);
  color: var(--status-ok);
}

.ml-time-col.blue .ml-input { border-color: rgba(59, 130, 246, 0.3); }
.ml-time-col.blue .ml-input:focus { border-color: var(--color-info); outline: none; background: rgba(59, 130, 246, 0.05); }
.ml-time-col.amber .ml-input { border-color: rgba(245, 158, 11, 0.3); }
.ml-time-col.amber .ml-input:focus { border-color: var(--status-warn); outline: none; background: rgba(245, 158, 11, 0.05); }
.ml-input:disabled { opacity: 0.8; cursor: not-allowed; }

.ml-unit {
  font-size: 9px;
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.ml-time-col.grey .ml-input {
  background: var(--bg-muted);
  border-color: var(--border-default);
  color: var(--text-secondary);
}

/* Deviation grid (compact inline) */
.ml-deviation-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-3);
}

.ml-deviation-item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.ml-deviation-item label {
  font-size: 9px;
  color: var(--text-tertiary);
  text-transform: uppercase;
}

.ml-deviation-item span {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  font-family: var(--font-mono);
}

.over { color: var(--color-danger); }
.under { color: var(--color-success); }

/* Compact bottom row: selects + notes + save */
.ml-compact-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.ml-select {
  padding: 2px var(--space-1);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  background: var(--bg-input);
  color: var(--text-primary);
  flex-shrink: 0;
}

.ml-select-narrow {
  max-width: 64px;
}

.ml-notes-inline {
  flex: 1;
  min-width: 0;
  padding: 2px var(--space-2);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-xs);
  font-family: inherit;
}

.ml-notes-inline:focus {
  outline: none;
  border-color: var(--state-focus-border);
}

.ml-save-btn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: 2px var(--space-2);
  background: var(--status-ok);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  cursor: pointer;
  white-space: nowrap;
  transition: var(--transition-fast);
  flex-shrink: 0;
}

.ml-save-btn:hover:not(:disabled) { opacity: 0.9; }
.ml-save-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* === TIMEVISION RESULT RIBBON (collapsible) === */
.tv-ribbon {
  background: var(--bg-surface);
}

.tv-header {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  user-select: none;
  background: var(--bg-surface);
}

.tv-header:hover { background: var(--bg-raised); }

.tv-chevron {
  color: var(--text-tertiary);
  transition: transform 0.2s;
  flex-shrink: 0;
}

.tv-icon {
  color: var(--color-primary);
  flex-shrink: 0;
}

.tv-title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.tv-status-badge {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  margin-left: auto;
}

.tv-collapsed-summary {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-left: var(--space-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.tv-cs-item.teal { color: var(--status-ok); font-weight: var(--font-semibold); }
.tv-cs-sep { color: var(--text-tertiary); }

.tv-loading {
  display: flex;
  justify-content: center;
  padding: var(--space-2);
}

.tv-body {
  padding: 0 var(--space-3) var(--space-2);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.tv-summary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
}

.tv-summary-item {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.tv-summary-item label {
  font-size: 9px;
  font-weight: var(--font-medium);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: var(--text-tertiary);
}

.tv-summary-item span {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.tv-summary-item.highlight label { color: var(--status-ok); }
.tv-time-value {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--status-ok);
  font-family: var(--font-mono);
}

.confidence-high { color: var(--color-success); }
.confidence-medium { color: var(--color-warning); }
.confidence-low { color: var(--color-danger); }

.tv-breakdown {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--bg-raised);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-2);
}

.tv-breakdown-row {
  display: flex;
  justify-content: space-between;
  padding: var(--space-0\.5) 0;
}

.tv-op-name {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.tv-op-time {
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.tv-reasoning {
  padding: var(--space-1) var(--space-2);
  background: var(--bg-raised);
  border-radius: var(--radius-sm);
}

.tv-reasoning-text {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  line-height: 1.4;
  white-space: pre-wrap;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
