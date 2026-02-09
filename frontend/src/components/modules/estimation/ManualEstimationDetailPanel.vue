<template>
  <div class="estimation-detail-panel">
    <div class="panel-header">
      <h3 class="filename">{{ record.filename }}</h3>
      <div class="header-actions">
        <button @click="handleExtractVision" :disabled="extracting" class="btn-vision">
          {{ extracting ? '⏳ Zpracovávám...' : '🤖 AI Vision Extract' }}
        </button>
        <button @click="handleOpenPdf" class="btn-pdf">📄 Výkres</button>
        <span class="part-type-badge">{{ record.part_type }} Part</span>
      </div>
    </div>

    <!-- VISION METADATA (if extracted) -->
    <div v-if="record.data_source" class="vision-metadata">
      <span class="metadata-badge" :class="`badge-${record.data_source}`">
        {{ visionSourceLabel }}
      </span>
      <span v-if="record.confidence" class="confidence-badge">
        📊 {{ (record.confidence * 100).toFixed(0) }}%
      </span>
      <div v-if="record.needs_manual_review" class="warning-banner">
        ⚠️ Potřebuje manuální kontrolu!
      </div>
    </div>

    <!-- AI VISION TIME ESTIMATE -->
    <section v-if="visionSummary" class="vision-section">
      <div class="vision-header">
        <h4 class="section-title">🤖 AI Vision Time Estimate</h4>
        <div class="vision-badges">
          <span class="badge badge-primary">{{ visionSummary.part_type }}</span>
          <span class="badge" :class="visionSummary.confidence > 0.8 ? 'badge-success' : 'badge-warning'">
            {{ (visionSummary.confidence * 100).toFixed(0) }}% confidence
          </span>
          <span class="badge badge-time">⏱️ {{ visionSummary.total_time_min?.toFixed(1) }} min</span>
        </div>
      </div>

      <!-- Summary Info + Controls -->
      <div class="vision-summary">
        <!-- Material & Stock -->
        <div class="summary-row">
          <span class="label">Material:</span>
          <input
            v-model="materialCode"
            type="text"
            class="material-input"
            placeholder="e.g., 1.4305"
            :disabled="recalculating"
            @change="handleRecalculate"
          />
        </div>
        <div class="summary-row">
          <span class="label">Stock:</span>
          <span class="value">{{ visionSummary.stock_type }} {{ visionSummary.stock_dims }}</span>
        </div>

        <!-- Speed Mode Selector -->
        <div class="summary-row">
          <span class="label">Speed Mode:</span>
          <select
            v-model="speedMode"
            class="speed-select"
            :disabled="recalculating"
            @change="handleRecalculate"
          >
            <option value="low">🐢 Low (conservative)</option>
            <option value="mid">⚡ Mid (standard)</option>
            <option value="high">🚀 High (aggressive)</option>
          </select>
          <span v-if="recalculating" class="recalc-indicator">⏳ Přepočítávám...</span>
        </div>

        <!-- Time Breakdown -->
        <div class="summary-row time-breakdown">
          <span class="label">Time Breakdown:</span>
          <span class="value">
            🔧 Machining: <strong>{{ visionSummary.machining_time_min?.toFixed(1) }} min</strong> |
            ⚙️ Setup: {{ visionSummary.setup_time_min?.toFixed(1) }} min |
            📏 Inspection: {{ visionSummary.inspection_time_min?.toFixed(1) }} min
          </span>
        </div>

        <div v-if="visionSummary.notes" class="vision-notes">💡 {{ visionSummary.notes }}</div>
      </div>

      <!-- Machining Operations Table (ONLY cutting operations) -->
      <div class="operations-table">
        <div class="table-header">
          <h5>🔧 Strojní operace (čas v řezu + vedlejší časy)</h5>
        </div>
        <table>
          <thead>
            <tr>
              <th style="width: 40px">#</th>
              <th style="width: 180px">Operace</th>
              <th>Popis</th>
              <th style="width: 90px">Hlavní čas</th>
              <th style="width: 90px">Vedlejší čas</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="op in visionOperations" :key="op.step">
              <td class="step-num">{{ op.step }}</td>
              <td class="op-name">{{ op.operation }}</td>
              <td class="op-desc">
                <div class="op-description">{{ op.description }}</div>
                <div v-if="op.cutting_params" class="op-params">⚙️ {{ op.cutting_params }}</div>
                <div class="op-reason">{{ op.reason }}</div>
              </td>
              <td class="op-time main-time">{{ op.main_time_min?.toFixed(2) }} min</td>
              <td class="op-time aux-time">{{ op.auxiliary_time_min?.toFixed(2) }} min</td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td colspan="3" class="total-label"><strong>CELKEM OBRÁBĚNÍ</strong></td>
              <td colspan="2" class="total-time"><strong>{{ visionSummary.machining_time_min?.toFixed(1) }} min</strong></td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>

    <!-- KEY FEATURES -->
    <section class="features-section">
      <h4 class="section-title">Key Features</h4>
      <dl class="features-grid">
        <div v-for="(feature, idx) in keyFeatures" :key="idx" class="feature-item">
          <dt class="feature-label">{{ feature.label }}</dt>
          <dd class="feature-value">{{ feature.value }}</dd>
        </div>
      </dl>
    </section>

    <!-- SIMILAR PARTS -->
    <SimilarPartsWidget
      v-if="similarParts.length > 0"
      :similar-parts="similarParts"
      :loading="loadingSimilar"
      @refresh="$emit('refresh-similar')"
    />

    <!-- MANUAL CORRECTION FORM -->
    <ManualCorrectionFormWidget :record="record" @submit="handleSubmit" @next="handleNext" />

    <!-- 3D VIEWER (Simple - original STEP only) -->
    <StepViewer3DSimple
      :key="record.filename"
      :filename="record.filename"
      :bbox-x="record.bbox_x_mm"
      :bbox-y="record.bbox_y_mm"
      :bbox-z="record.bbox_z_mm"
      :part-volume="record.part_volume_mm3"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { EstimationRecord, SimilarPart } from '@/types/estimation'
import SimilarPartsWidget from './SimilarPartsWidget.vue'
import ManualCorrectionFormWidget, { type CorrectionFormData } from './ManualCorrectionFormWidget.vue'
import StepViewer3DSimple from './StepViewer3DSimple.vue'
import { useWindowsStore } from '@/stores/windows'

interface Props {
  record: EstimationRecord
  similarParts: SimilarPart[]
  loadingSimilar: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'submit-estimate', data: CorrectionFormData): void
  (e: 'next-part'): void
  (e: 'refresh-similar'): void
  (e: 'vision-extracted'): void
}>()

const windowsStore = useWindowsStore()
const extracting = ref(false)
const currentPdfWindowId = ref<string | null>(null)

// Material & Speed Mode controls
const materialCode = ref('')
const speedMode = ref<'low' | 'mid' | 'high'>('mid')
const recalculating = ref(false)

// Watch for record changes and update PDF if window is open
watch(() => props.record.filename, async (newFilename) => {
  if (currentPdfWindowId.value) {
    // Find and update the PDF window
    const window = windowsStore.windows.find(w => w.id === currentPdfWindowId.value)
    if (window) {
      try {
        // Fetch new PDF URL
        const response = await fetch(`/api/estimation/pdf-url/${encodeURIComponent(newFilename)}`)
        if (response.ok) {
          const data = await response.json()
          const pdfUrl = data.pdf_url

          // Update window title (EstimationPdfWindow parses this)
          windowsStore.updateWindowTitle(currentPdfWindowId.value, `Výkres: ${newFilename}|${pdfUrl}`)
        }
      } catch (error) {
        console.error('Failed to update PDF:', error)
      }
    }
  }
})

function handleSubmit(data: CorrectionFormData) {
  emit('submit-estimate', data)
}

function handleNext() {
  emit('next-part')
}

async function handleExtractVision() {
  extracting.value = true
  try {
    // Encode filename for URL (handle spaces and special chars)
    const encodedFilename = encodeURIComponent(props.record.filename)
    const response = await fetch(`/api/estimation/extract-features/${encodedFilename}`, {
      method: 'POST'
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`HTTP ${response.status}: ${errorText}`)
    }

    const result = await response.json()
    console.log('Vision extraction successful:', result)

    // Refresh data after extraction (BEFORE alert so it doesn't block)
    emit('vision-extracted')

    // Small delay to allow refresh, then show success
    await new Promise(resolve => setTimeout(resolve, 100))
    alert('✅ AI Vision extrakce úspěšná!')
  } catch (error) {
    console.error('Vision extraction failed:', error)
    alert('❌ AI Vision extrakce selhala:\n' + (error as Error).message)
  } finally {
    extracting.value = false
  }
}

async function handleOpenPdf() {
  try {
    // Fetch PDF URL from backend mapping
    const response = await fetch(`/api/estimation/pdf-url/${encodeURIComponent(props.record.filename)}`)

    if (!response.ok) {
      throw new Error(`PDF not found for ${props.record.filename}`)
    }

    const data = await response.json()
    const pdfUrl = data.pdf_url

    // Check if PDF window is already open
    if (currentPdfWindowId.value) {
      const existingWindow = windowsStore.windows.find(w => w.id === currentPdfWindowId.value)
      if (existingWindow) {
        // Just update the title
        windowsStore.updateWindowTitle(currentPdfWindowId.value, `Výkres: ${props.record.filename}|${pdfUrl}`)
        return
      }
    }

    // Open new window and store ID (openWindow returns the window ID string)
    const newWindowId = await windowsStore.openWindow(
      'pdf-viewer', // module type
      `Výkres: ${props.record.filename}|${pdfUrl}` // title with URL encoded
    )

    // Store window ID for future updates
    currentPdfWindowId.value = newWindowId
  } catch (error) {
    console.error('Failed to open PDF:', error)
    alert('❌ PDF výkres nenalezen pro tento díl')
  }
}

async function handleRecalculate() {
  if (!materialCode.value || recalculating.value) return

  recalculating.value = true
  try {
    const response = await fetch(
      `/api/estimation/recalculate-times/${props.record.id}?part_type=${props.record.part_type}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          material_code: materialCode.value,
          speed_mode: speedMode.value
        })
      }
    )

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`HTTP ${response.status}: ${errorText}`)
    }

    const result = await response.json()
    console.log('Times recalculated:', result)

    // Trigger refresh to reload updated data
    emit('vision-extracted')

    // Small delay to allow refresh
    await new Promise(resolve => setTimeout(resolve, 100))
    alert(`✅ Časy přepočítány!\n\n⏱️ Total: ${result.total_time_min?.toFixed(1)} min\n🔧 Machining: ${result.machining_time_min?.toFixed(1)} min\n⚙️ Setup: ${result.setup_time_min?.toFixed(1)} min\n📏 Inspection: ${result.inspection_time_min?.toFixed(1)} min`)
  } catch (error) {
    console.error('Recalculation failed:', error)
    alert('❌ Přepočet selhal:\n' + (error as Error).message)
  } finally {
    recalculating.value = false
  }
}

const visionSourceLabel = computed(() => {
  switch (props.record.data_source) {
    case 'vision_primary': return '🤖 AI Vision'
    case 'vision_override': return '🤖 Vision Override'
    case 'occt_validated': return '✅ OCCT Validated'
    case 'occt_fallback': return '⚠️ OCCT Fallback'
    case 'occt_only': return '🔧 OCCT Only'
    default: return 'Unknown'
  }
})

// Parse Vision data from decision_log JSON
const visionData = computed(() => {
  if (!props.record.decision_log) return null
  try {
    const parsed = JSON.parse(props.record.decision_log)
    return parsed.vision_raw || null
  } catch (e) {
    console.warn('Failed to parse decision_log:', e)
    return null
  }
})

// Parse Vision operations (machining steps with time breakdown)
// Filter out Setup and Inspection - show only MACHINING operations
const visionOperations = computed(() => {
  if (!visionData.value?.operations) return []

  return visionData.value.operations
    .filter((op: any) => {
      const opName = op.operation?.toLowerCase() || ''
      // Exclude Setup and Inspection
      return !opName.includes('setup') &&
             !opName.includes('clamping') &&
             !opName.includes('inspection')
    })
    .map((op: any, index: number) => ({
      step: index + 1, // Renumber after filtering
      operation: op.operation || op.type, // Support both 'operation' and 'type' fields
      description: op.description,
      // Support both old format (time_min) and new format (main_time_min + auxiliary_time_min)
      main_time_min: op.main_time_min || (op.time_min ? op.time_min * 0.75 : 0),
      auxiliary_time_min: op.auxiliary_time_min || (op.time_min ? op.time_min * 0.25 : 0),
      cutting_params: op.cutting_params, // NEW: cutting conditions from calculator
      reason: op.reason
    }))
})

const visionSummary = computed(() => {
  if (!visionData.value) return null

  // Support both old and new format
  const v = visionData.value
  const hasSeparateTimes = v.machining_time_min !== undefined

  // Calculate machining time from operations if not provided
  let machiningTime = v.machining_time_min || 0
  let setupTime = v.setup_time_min || 0
  let inspectionTime = v.inspection_time_min || 0

  if (!hasSeparateTimes && v.operations) {
    // Old format - calculate from operations
    v.operations.forEach((op: any) => {
      if (op.operation?.toLowerCase().includes('setup') || op.operation?.toLowerCase().includes('clamping')) {
        setupTime += op.time_min || 0
      } else if (op.operation?.toLowerCase().includes('inspection')) {
        inspectionTime += op.time_min || 0
      } else {
        machiningTime += op.time_min || 0
      }
    })
  }

  return {
    part_type: v.part_type,
    material_code: v.material_code,
    stock_type: v.stock_type,
    stock_dims: v.stock_dims,
    machining_time_min: machiningTime,
    setup_time_min: setupTime,
    inspection_time_min: inspectionTime,
    total_time_min: v.total_time_min || (machiningTime + setupTime + inspectionTime),
    confidence: v.confidence,
    notes: v.notes
  }
})

const keyFeatures = computed(() => [
  { label: 'Volume', value: `${props.record.part_volume_mm3.toFixed(0)} mm³` },
  {
    label: 'Removal',
    value: `${(props.record.removal_ratio * 100).toFixed(0)}% (${(props.record.part_volume_mm3 * props.record.removal_ratio).toFixed(0)} mm³)`
  },
  { label: 'Surface Area', value: `${props.record.surface_area_mm2.toFixed(0)} mm²` },
  {
    label: 'BBox',
    value: `${props.record.bbox_x_mm.toFixed(0)} × ${props.record.bbox_y_mm.toFixed(0)} × ${props.record.bbox_z_mm.toFixed(0)} mm`
  },
  { label: 'Max Dimension', value: `${props.record.max_dimension_mm.toFixed(0)} mm` },
  { label: 'Material', value: props.record.material_group_code },
  {
    label: 'Machinability',
    value: (props.record.material_machinability_index * 100).toFixed(0) + '%'
  },
  {
    label: 'Rotational Score',
    value: (props.record.rotational_score * 100).toFixed(0) + '%'
  },
  {
    label: 'Cylindrical Surface',
    value: (props.record.cylindrical_surface_ratio * 100).toFixed(0) + '%'
  },
  {
    label: 'Planar Surface',
    value: (props.record.planar_surface_ratio * 100).toFixed(0) + '%'
  }
])

// Initialize materialCode from Vision data when available (MUST be after visionSummary computed)
watch(() => visionSummary.value?.material_code, (newMaterial) => {
  if (newMaterial) materialCode.value = newMaterial
}, { immediate: true })
</script>

<style scoped>
.estimation-detail-panel {
  padding: var(--space-4);
  overflow-y: auto;
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 2px solid var(--border-default);
}

.filename {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--text-primary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.btn-vision,
.btn-pdf {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-vision:hover:not(:disabled),
.btn-pdf:hover {
  background: var(--bg-accent);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.btn-vision:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.part-type-badge {
  padding: var(--space-1) var(--space-3);
  background: var(--bg-accent);
  color: var(--color-primary);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 600;
  text-transform: uppercase;
}

/* Vision Metadata */
.vision-metadata {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-bottom: var(--space-4);
  padding: var(--space-3);
  background: var(--bg-accent);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
}

.metadata-badge,
.confidence-badge {
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: 600;
}

.metadata-badge {
  background: var(--color-success);
  color: white;
}

.badge-vision_primary {
  background: #4CAF50;
}

.badge-vision_override {
  background: #FF9800;
}

.badge-occt_validated {
  background: #2196F3;
}

.badge-occt_fallback {
  background: #FFC107;
}

.badge-occt_only {
  background: #9E9E9E;
}

.confidence-badge {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
}

/* Vision Time Estimate Section */
.vision-section {
  background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 100%);
  border: 2px solid #4285f4;
  border-radius: var(--radius-md);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}

.vision-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}

.vision-section .section-title {
  color: #1967d2;
  font-weight: 700;
  margin: 0;
}

.vision-badges {
  display: flex;
  gap: var(--space-2);
}

.badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: var(--text-sm);
  font-weight: 600;
}

.badge-primary {
  background: #2196F3;
  color: white;
}

.badge-success {
  background: #4CAF50;
  color: white;
}

.badge-warning {
  background: #FF9800;
  color: white;
}

.badge-time {
  background: #9C27B0;
  color: white;
}

.vision-summary {
  padding: var(--space-3);
  background: white;
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-3);
}

.summary-row {
  display: flex;
  gap: var(--space-2);
  margin: var(--space-2) 0;
  align-items: center;
}

.summary-row .label {
  font-weight: 700;
  color: #1967d2;
  min-width: 120px;
}

.summary-row .value {
  color: #333;
  font-weight: 500;
}

.material-input,
.speed-select {
  padding: var(--space-1) var(--space-2);
  border: 2px solid #2196F3;
  border-radius: var(--radius-sm);
  background: white;
  color: #333;
  font-size: var(--text-sm);
  font-weight: 600;
  font-family: 'Courier New', monospace;
  transition: all 0.2s;
  cursor: pointer;
}

.material-input {
  width: 120px;
  text-align: center;
}

.speed-select {
  min-width: 200px;
}

.material-input:focus,
.speed-select:focus {
  outline: none;
  border-color: #1967d2;
  box-shadow: 0 0 0 3px rgba(25, 103, 210, 0.1);
}

.material-input:hover,
.speed-select:hover {
  border-color: #1967d2;
  background: #f0f4ff;
}

.material-input:disabled,
.speed-select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  background: #f5f5f5;
}

.recalc-indicator {
  margin-left: var(--space-2);
  color: #1967d2;
  font-size: var(--text-sm);
  font-weight: 600;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.time-breakdown {
  padding: var(--space-2);
  background: #f0f4ff;
  border-radius: var(--radius-sm);
  border-left: 4px solid #1967d2;
}

.time-breakdown .value {
  font-size: var(--text-sm);
}

.time-breakdown strong {
  color: #9C27B0;
  font-size: var(--text-base);
}

.vision-notes {
  font-style: italic;
  color: #666;
  margin-top: var(--space-2);
  padding: var(--space-2);
  background: #fffef0;
  border-left: 3px solid #FFC107;
  border-radius: var(--radius-sm);
}

/* Operations Table */
.operations-table {
  background: white;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid #e0e0e0;
}

.table-header {
  background: #1967d2;
  color: white;
  padding: var(--space-2) var(--space-3);
}

.table-header h5 {
  margin: 0;
  font-size: var(--text-base);
  font-weight: 600;
}

.operations-table table {
  width: 100%;
  border-collapse: collapse;
}

.operations-table thead {
  background: #2979ff;
  color: white;
}

.operations-table th {
  padding: var(--space-2) var(--space-3);
  text-align: left;
  font-weight: 600;
  font-size: var(--text-sm);
  border-bottom: 2px solid #1967d2;
}

.operations-table tbody tr {
  border-bottom: 1px solid #e0e0e0;
}

.operations-table tbody tr:hover {
  background: #f8f9fa;
}

.operations-table td {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
}

.step-num {
  text-align: center;
  font-weight: 700;
  color: white;
  background: #1967d2;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.op-name {
  font-weight: 600;
  color: #1967d2;
}

.op-desc {
  color: #444;
}

.op-description {
  font-weight: 500;
  color: #222;
  margin-bottom: 4px;
}

.op-params {
  font-size: var(--text-xs);
  color: #1967d2;
  font-family: 'Courier New', monospace;
  margin-bottom: 4px;
  padding: 2px 6px;
  background: #e3f2fd;
  border-radius: 3px;
  display: inline-block;
}

.op-reason {
  font-size: var(--text-xs);
  color: #666;
  font-style: italic;
}

.op-time {
  text-align: right;
  font-weight: 600;
  font-family: 'Courier New', monospace;
}

.main-time {
  color: #2E7D32;
  background: #E8F5E9;
}

.aux-time {
  color: #F57C00;
  background: #FFF3E0;
}

.operations-table tfoot {
  background: #1967d2;
  color: white;
  border-top: 3px solid #0d47a1;
}

.operations-table tfoot td {
  padding: var(--space-3);
}

.total-label {
  text-align: right;
  font-size: var(--text-base);
  font-weight: 700;
  color: white;
}

.total-time {
  text-align: right;
  font-size: var(--text-lg);
  font-weight: 700;
  color: #FFD54F;
}

/* Badge colors for Vision features */
.badge-blue {
  background: #2196F3;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.badge-green {
  background: #4CAF50;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.badge-orange {
  background: #FF9800;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.badge-purple {
  background: #9C27B0;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.badge-gray {
  background: #757575;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.warning-banner {
  flex: 1 1 100%;
  padding: var(--space-2) var(--space-3);
  background: #FFF3E0;
  border: 1px solid #FF9800;
  border-radius: var(--radius-sm);
  color: #E65100;
  font-size: var(--text-sm);
  font-weight: 600;
}

.features-section {
  margin-bottom: var(--space-5);
}

.section-title {
  margin: 0 0 var(--space-3) 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
  margin: 0;
  padding: var(--space-3);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.feature-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.feature-label {
  font-size: var(--text-xs);
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.feature-value {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}
</style>
