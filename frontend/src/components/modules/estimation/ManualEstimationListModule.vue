<template>
  <div class="manual-estimation-module">
    <div class="split-pane-container">
      <!-- LEFT: List Panel -->
      <div class="left-pane">
        <ManualEstimationListPanel
          :records="pendingRecords"
          :selected-id="selectedId"
          :part-type="partType"
          :loading="loading"
          @select="handleSelect"
          @change-part-type="handlePartTypeChange"
          @export="handleExport"
          @refresh="loadPendingEstimates"
        />
      </div>

      <!-- RIGHT: Detail Panel -->
      <div class="right-pane">
        <ManualEstimationDetailPanel
          v-if="selectedRecord"
          :record="selectedRecord"
          :similar-parts="similarParts"
          :loading-similar="loadingSimilar"
          @submit-estimate="handleSubmitEstimate"
          @next-part="handleNextPart"
          @refresh-similar="loadSimilarParts"
          @vision-extracted="handleVisionExtracted"
        />
        <div v-else class="empty-state">
          <p>Select a part from the list to view details</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import ManualEstimationListPanel from './ManualEstimationListPanel.vue'
import ManualEstimationDetailPanel from './ManualEstimationDetailPanel.vue'
import type { CorrectionFormData } from './ManualCorrectionFormWidget.vue'
import type { EstimationRecord, PartType, SimilarPart } from '@/types/estimation'

const API_BASE = '/api/estimation'

const pendingRecords = ref<EstimationRecord[]>([])
const selectedId = ref<number | null>(null)
const partType = ref<PartType>('ROT')
const loading = ref(false)
const similarParts = ref<SimilarPart[]>([])
const loadingSimilar = ref(false)

const selectedRecord = computed(() => {
  if (!selectedId.value) return null
  return pendingRecords.value.find(r => r.id === selectedId.value) || null
})

async function loadPendingEstimates() {
  loading.value = true
  try {
    const response = await fetch(`${API_BASE}/pending-estimates?part_type=${partType.value}`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    pendingRecords.value = await response.json()
  } catch (error) {
    pendingRecords.value = []
  } finally {
    loading.value = false
  }
}

async function loadSimilarParts() {
  if (!selectedId.value) return
  loadingSimilar.value = true
  try {
    const response = await fetch(
      `${API_BASE}/similar-parts/${selectedId.value}?part_type=${partType.value}&limit=5`
    )
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    similarParts.value = await response.json()
  } catch (error) {
    similarParts.value = []
  } finally {
    loadingSimilar.value = false
  }
}

function handleSelect(id: number) {
  selectedId.value = id
  loadSimilarParts()
}

function handlePartTypeChange(newType: PartType) {
  partType.value = newType
  selectedId.value = null
  similarParts.value = []
  loadPendingEstimates()
}

async function handleSubmitEstimate(formData: CorrectionFormData) {
  if (!selectedId.value) return

  const totalTime =
    (formData.roughingTime || 0) + (formData.finishingTime || 0) + (formData.setupTime || 0)

  const payload = {
    corrected_part_type: formData.partType,
    corrected_material_code: formData.materialCode,
    corrected_bbox_x_mm: formData.bboxX,
    corrected_bbox_y_mm: formData.bboxY,
    corrected_bbox_z_mm: formData.bboxZ,
    corrected_stock_type: formData.stockType,
    corrected_stock_diameter: formData.stockDiameter,
    corrected_stock_length: formData.stockLength,
    estimated_roughing_time_min: formData.roughingTime,
    estimated_finishing_time_min: formData.finishingTime,
    estimated_setup_time_min: formData.setupTime,
    estimated_time_min: totalTime,
    correction_notes: formData.notes,
    correction_reason: 'Manual correction from UI'
  }

  try {
    const response = await fetch(
      `${API_BASE}/finalize-estimate/${selectedId.value}?part_type=${partType.value}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      }
    )
    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    // Remove from pending list
    pendingRecords.value = pendingRecords.value.filter(r => r.id !== selectedId.value)

    // Auto-select next part
    if (pendingRecords.value.length > 0) {
      selectedId.value = pendingRecords.value[0]?.id ?? null
      if (selectedId.value) {
        loadSimilarParts()
      }
    } else {
      selectedId.value = null
      similarParts.value = []
    }

    alert(`Estimate saved: ${totalTime.toFixed(1)} minutes`)
  } catch (error) {
    alert('Failed to submit estimate. Please try again.')
  }
}

function handleNextPart() {
  if (pendingRecords.value.length === 0) return

  const currentIndex = pendingRecords.value.findIndex(r => r.id === selectedId.value)
  const nextIndex = currentIndex + 1

  if (nextIndex < pendingRecords.value.length) {
    selectedId.value = pendingRecords.value[nextIndex]?.id ?? null
    if (selectedId.value) loadSimilarParts()
  } else {
    // Wrap to first
    selectedId.value = pendingRecords.value[0]?.id ?? null
    if (selectedId.value) loadSimilarParts()
  }
}

async function handleVisionExtracted() {
  // Store current selection
  const currentFilename = selectedRecord.value?.filename

  // Refresh list
  await loadPendingEstimates()

  // Force-update selection to trigger detail panel refresh
  if (currentFilename) {
    // Find updated record by filename
    const updatedRecord = pendingRecords.value.find(r => r.filename === currentFilename)
    if (updatedRecord) {
      selectedId.value = updatedRecord.id
      await loadSimilarParts()
    }
  }
}

async function handleExport() {
  try {
    const response = await fetch(`${API_BASE}/export-training-data?part_type=${partType.value}`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `training_data_${partType.value}.csv`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (error) {
    alert('Failed to export data. Ensure some parts have manual estimates.')
  }
}

onMounted(() => {
  loadPendingEstimates()
})
</script>

<style scoped>
.manual-estimation-module {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.split-pane-container {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.left-pane {
  width: 400px;
  border-right: 1px solid var(--color-border);
  overflow-y: auto;
}

.right-pane {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-secondary);
}
</style>
