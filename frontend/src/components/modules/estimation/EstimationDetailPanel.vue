<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import type { MachiningTimeEstimation } from '@/types/estimation'
import type { MaterialGroup } from '@/types/material'
import { Clock, FileText, AlertTriangle } from 'lucide-vue-next'
import TimeBreakdownWidget from './TimeBreakdownWidget.vue'
import GeometryInfoWidget from './GeometryInfoWidget.vue'
import ConstraintsWidget from './ConstraintsWidget.vue'
import { getMaterialGroups } from '@/api/materials'
import { useMachiningTimeEstimation } from '@/composables/useMachiningTimeEstimation'
import { useUiStore } from '@/stores/ui'
import { useWindowsStore } from '@/stores/windows'

interface Props {
  result: MachiningTimeEstimation
  allResults: MachiningTimeEstimation[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'updated', result: MachiningTimeEstimation): void
  (e: 'select', result: MachiningTimeEstimation): void
}>()

const uiStore = useUiStore()
const windowsStore = useWindowsStore()
const { reEstimate, loading: estimating } = useMachiningTimeEstimation()

const availableMaterials = ref<MaterialGroup[]>([])
const selectedMaterialCode = ref<string>(props.result.breakdown?.material ?? '')
const loadingMaterials = ref(false)
const localResult = ref<MachiningTimeEstimation>(props.result)
const pdfMapping = ref<Record<string, string>>({})

const totalTimeDisplay = computed(() => (localResult.value.total_time_min ?? 0).toFixed(2))

const hasConstraints = computed(() =>
  (localResult.value.breakdown?.critical_constraints?.length ?? 0) > 0
)

onMounted(async () => {
  await loadMaterials()
  await loadPdfMapping()
})

async function loadPdfMapping() {
  try {
    const response = await fetch('/uploads/drawings/step_pdf_mapping.json')
    pdfMapping.value = await response.json()
  } catch (error) {
    // Silently fail - PDF mapping is optional
  }
}

watch(() => props.result, (newResult) => {
  localResult.value = newResult
  selectedMaterialCode.value = newResult.breakdown?.material ?? ''

  // Auto-update PDF window title if already open
  updatePdfWindow()
}, { immediate: true })

// Update PDF window if it's already open
function updatePdfWindow() {
  const pdfWindow = windowsStore.findWindowByModule('pdf-viewer')
  if (!pdfWindow) return

  const pdfFilename = pdfMapping.value[localResult.value.filename]
  if (!pdfFilename) return

  const url = `/uploads/drawings/${encodeURIComponent(pdfFilename)}`
  const title = `Výkres: ${localResult.value.filename}|${url}`

  windowsStore.updateWindowTitle(pdfWindow.id, title)
}

async function loadMaterials() {
  loadingMaterials.value = true
  try {
    const groups = await getMaterialGroups()
    availableMaterials.value = groups.filter(g => g.mrr_milling_roughing !== null)
  } catch (error) {
    uiStore.showError('Failed to load materials')
  } finally {
    loadingMaterials.value = false
  }
}

async function handleMaterialChange() {
  if (selectedMaterialCode.value === (localResult.value.breakdown?.material ?? '')) return

  const newEstimate = await reEstimate(
    localResult.value.filename,
    selectedMaterialCode.value,
    localResult.value.breakdown?.stock_type ?? 'bbox'
  )

  if (newEstimate) {
    localResult.value = newEstimate
    emit('updated', newEstimate)
    uiStore.showSuccess('Machining time re-estimated')
  } else {
    selectedMaterialCode.value = localResult.value.breakdown?.material ?? ''
    uiStore.showError('Failed to re-estimate machining time')
  }
}

function openPdfInWindow() {
  const pdfFilename = pdfMapping.value[localResult.value.filename]
  if (!pdfFilename) {
    uiStore.showError('PDF drawing not found for this part')
    return
  }

  const url = `/uploads/drawings/${encodeURIComponent(pdfFilename)}`

  // Pass URL via window title (format: "Výkres: filename|url")
  const title = `Výkres: ${localResult.value.filename}|${url}`

  windowsStore.openWindow('pdf-viewer', title, null)
}
</script>

<template>
  <div class="estimation-detail-panel">
    <div class="panel-header">
      <h2>Detail dílu</h2>
    </div>

    <div class="drawing-selector-section">
      <button
        class="drawing-header-button"
        @click="openPdfInWindow"
      >
        <div class="drawing-header-content">
          <span class="drawing-label"><FileText :size="14" class="inline-icon" /> Výkres</span>
          <span class="drawing-filename">{{ localResult.filename }}</span>
        </div>
        <span class="toggle-icon">▶</span>
      </button>
    </div>

    <div class="total-time-section">
      <div class="total-time-value">
        <Clock :size="32" class="time-icon" />
        <div>
          <div class="time-display">{{ totalTimeDisplay }} min</div>
          <div class="time-label">Total Machining Time</div>
        </div>
      </div>
    </div>

    <div class="material-selector-section">
      <label for="material-select" class="material-label">Material</label>
      <select
        id="material-select"
        v-model="selectedMaterialCode"
        class="material-select"
        :disabled="estimating || loadingMaterials"
        @change="handleMaterialChange"
      >
        <option v-if="loadingMaterials" value="">Loading...</option>
        <option
          v-for="material in availableMaterials"
          :key="material.code"
          :value="material.code"
        >
          {{ material.code }} - {{ material.name }}
        </option>
      </select>
      <div v-if="estimating" class="estimating-indicator">Re-calculating...</div>
    </div>

    <TimeBreakdownWidget
      :roughing-main="localResult.roughing_time_main ?? 0"
      :roughing-aux="localResult.roughing_time_aux ?? 0"
      :finishing-main="localResult.finishing_time_main ?? 0"
      :finishing-aux="localResult.finishing_time_aux ?? 0"
    />

    <GeometryInfoWidget
      :material="localResult.breakdown?.material ?? 'N/A'"
      :stock-volume-mm3="localResult.breakdown?.stock_volume_mm3 ?? 0"
      :part-volume-mm3="localResult.breakdown?.part_volume_mm3 ?? 0"
      :material-to-remove-mm3="localResult.breakdown?.material_to_remove_mm3 ?? 0"
      :material-removal-percent="(localResult.breakdown?.material_to_remove_mm3 ?? 0) / (localResult.breakdown?.stock_volume_mm3 ?? 1) * 100"
      :surface-area-mm2="localResult.breakdown?.surface_area_mm2 ?? 0"
    />

    <div class="calculation-section">
      <h3 class="section-title">Kalkulační vzorec</h3>

      <div class="calc-card">
        <div class="calc-header">1. Hrubování (Roughing)</div>
        <div class="calc-formula">
          <div class="formula-line">
            <span class="formula-label">Objem k odebrání:</span>
            <span class="formula-value">{{ ((localResult.breakdown?.material_to_remove_mm3 ?? 0) / 1000).toFixed(2) }} cm³</span>
          </div>
          <div class="formula-line">
            <span class="formula-label">MRR ({{ localResult.breakdown?.material ?? 'N/A' }}):</span>
            <span class="formula-value">{{ localResult.breakdown?.mrr_roughing_cm3_min ?? 0 }} cm³/min</span>
          </div>
          <div class="formula-divider">÷</div>
          <div class="formula-line result">
            <span class="formula-label">Základní čas hrubování:</span>
            <span class="formula-value">{{ ((localResult.breakdown?.material_to_remove_mm3 ?? 0) / 1000 / (localResult.breakdown?.mrr_roughing_cm3_min ?? 1)).toFixed(2) }} min</span>
          </div>
          <div class="formula-line" v-if="(localResult.breakdown?.constraint_multiplier ?? 1) > 1">
            <span class="formula-label">× Constraint penalty:</span>
            <span class="formula-value warning">{{ (localResult.breakdown?.constraint_multiplier ?? 1).toFixed(2) }}×</span>
          </div>
          <div class="formula-line">
            <span class="formula-label">= Hlavní čas hrubování:</span>
            <span class="formula-value">{{ (localResult.roughing_time_main ?? 0).toFixed(2) }} min</span>
          </div>
          <div class="formula-line">
            <span class="formula-label">+ Vedlejší čas (přejezdy, 20%):</span>
            <span class="formula-value">{{ (localResult.roughing_time_aux ?? 0).toFixed(2) }} min</span>
          </div>
          <div class="formula-line final">
            <span class="formula-label">= CELKEM hrubování:</span>
            <span class="formula-value highlight">{{ (localResult.roughing_time_min ?? 0).toFixed(2) }} min</span>
          </div>
        </div>
      </div>

      <div class="calc-card">
        <div class="calc-header">2. Dokončování (Finishing)</div>
        <div class="calc-formula">
          <div class="formula-line">
            <span class="formula-label">Plocha povrchu:</span>
            <span class="formula-value">{{ ((localResult.breakdown?.surface_area_mm2 ?? 0) / 100).toFixed(2) }} cm²</span>
          </div>
          <div class="formula-line">
            <span class="formula-label">Finishing rate:</span>
            <span class="formula-value">{{ localResult.breakdown?.finishing_rate_cm2_min ?? 0 }} cm²/min</span>
          </div>
          <div class="formula-divider">÷</div>
          <div class="formula-line result">
            <span class="formula-label">Hlavní čas dokončování:</span>
            <span class="formula-value">{{ (localResult.finishing_time_main ?? 0).toFixed(2) }} min</span>
          </div>
          <div class="formula-line">
            <span class="formula-label">+ Vedlejší čas (přejezdy, 15%):</span>
            <span class="formula-value">{{ (localResult.finishing_time_aux ?? 0).toFixed(2) }} min</span>
          </div>
          <div class="formula-line final">
            <span class="formula-label">= CELKEM dokončování:</span>
            <span class="formula-value highlight">{{ (localResult.finishing_time_min ?? 0).toFixed(2) }} min</span>
          </div>
        </div>
      </div>

      <div class="calc-card total">
        <div class="calc-header">Celkový čas</div>
        <div class="calc-formula">
          <div class="formula-line">
            <span class="formula-label">Hrubování (hlavní + vedlejší):</span>
            <span class="formula-value">{{ (localResult.roughing_time_min ?? 0).toFixed(2) }} min</span>
          </div>
          <div class="formula-line">
            <span class="formula-label">Dokončování (hlavní + vedlejší):</span>
            <span class="formula-value">{{ (localResult.finishing_time_min ?? 0).toFixed(2) }} min</span>
          </div>
          <div class="formula-divider">+</div>
          <div class="formula-line final">
            <span class="formula-label">= CELKEM:</span>
            <span class="formula-value highlight">{{ (localResult.total_time_min ?? 0).toFixed(2) }} min</span>
          </div>
        </div>
      </div>

      <div v-if="(localResult.breakdown?.critical_constraints?.length ?? 0) > 0" class="constraints-info">
        <div class="constraint-item" v-for="constraint in (localResult.breakdown?.critical_constraints ?? [])" :key="constraint">
          <AlertTriangle :size="16" class="constraint-icon" />
          <span class="constraint-text">{{ constraint }}</span>
        </div>
      </div>
    </div>

    <ConstraintsWidget
      v-if="hasConstraints"
      :constraints="localResult.breakdown?.critical_constraints ?? []"
      :multiplier="localResult.breakdown?.constraint_multiplier ?? 1"
    />
  </div>
</template>

<style scoped>
.estimation-detail-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: var(--space-6);
  overflow-y: auto;
  height: 100%;
  background: var(--bg-base);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border-default);
}

.panel-header h2 {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
}

.debug-badge {
  padding: var(--space-1) var(--space-2);
  background: var(--color-warning);
  color: white;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  border-radius: var(--radius-sm);
}

.part-type-badge {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  border-radius: var(--radius-sm);
  text-transform: uppercase;
}

.part-type-badge.rot {
  background: var(--color-info);
  color: white;
}

.part-type-badge.pri {
  background: var(--color-success);
  color: white;
}

.total-time-section {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.total-time-value {
  display: flex;
  align-items: center;
  gap: var(--space-5);
}

.time-icon {
  color: var(--color-primary);
}

.time-display {
  font-size: var(--text-5xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  line-height: 1;
}

.time-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-top: var(--space-2);
}

.drawing-selector-section {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
  min-height: 60px;
  margin-bottom: var(--space-4);
}

.material-selector-section {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.drawing-header-button {
  width: 100%;
  padding: var(--space-4) var(--space-5);
  background: var(--bg-surface);
  border: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.drawing-header-button:hover {
  background: var(--state-hover);
}

.drawing-header-button.is-open {
  background: var(--bg-raised);
  border-bottom: 1px solid var(--border-default);
}

.drawing-header-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.drawing-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  text-transform: uppercase;
  font-weight: var(--font-medium);
}

.drawing-filename {
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-weight: var(--font-medium);
}

.toggle-icon {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  transition: transform 0.2s;
}

.drawing-content {
  padding: var(--space-5);
  display: block !important;
  animation: slideDown 0.2s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.pdf-viewer-container {
  width: 100%;
  height: 600px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--bg-base);
}

.pdf-viewer {
  width: 100%;
  height: 100%;
  border: none;
}

.material-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  text-transform: uppercase;
  font-weight: var(--font-medium);
}

.material-select {
  padding: var(--space-3) var(--space-4);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all 0.2s;
}

.material-select:hover:not(:disabled) {
  border-color: var(--color-primary);
  background: var(--state-hover);
}

.material-select:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.estimating-indicator {
  font-size: var(--text-xs);
  color: var(--color-primary);
  font-weight: var(--font-medium);
  padding: var(--space-2) 0;
}

.calculation-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.section-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
  padding-bottom: var(--space-3);
  border-bottom: 2px solid var(--border-default);
}

.calc-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.calc-card.total {
  background: var(--bg-base);
  border: 2px solid var(--color-primary);
}

.calc-header {
  background: var(--bg-base);
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-default);
}

.calc-card.total .calc-header {
  background: var(--color-primary);
  color: white;
  border-bottom: none;
}

.calc-formula {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.formula-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--text-sm);
}

.formula-line.result {
  padding-top: var(--space-2);
  border-top: 1px solid var(--border-subtle);
  font-weight: var(--font-medium);
}

.formula-line.final {
  padding-top: var(--space-3);
  border-top: 2px solid var(--border-default);
  font-size: var(--text-base);
  font-weight: var(--font-bold);
}

.formula-label {
  color: var(--text-secondary);
}

.formula-value {
  font-family: var(--font-mono);
  color: var(--text-primary);
  font-weight: var(--font-medium);
}

.formula-value.warning {
  color: var(--color-warning);
  font-weight: var(--font-bold);
}

.formula-value.highlight {
  color: var(--color-primary);
  font-size: var(--text-lg);
}

.formula-divider {
  text-align: center;
  color: var(--text-tertiary);
  font-size: var(--text-sm);
  padding: var(--space-1) 0;
}

.constraints-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--color-warning-bg);
  border: 1px solid var(--color-warning);
  border-radius: var(--radius-md);
}

.constraint-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.constraint-icon {
  font-size: var(--text-base);
}

.constraint-text {
  font-weight: var(--font-medium);
}
</style>
