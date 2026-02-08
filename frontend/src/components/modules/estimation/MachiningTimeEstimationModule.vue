<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { MachiningTimeEstimation } from '@/types/estimation'
import BatchEstimationTable from './BatchEstimationTable.vue'
import EstimationDetailPanel from './EstimationDetailPanel.vue'
import { FileQuestion } from 'lucide-vue-next'

const batchResults = ref<MachiningTimeEstimation[]>([])
const selectedResult = ref<MachiningTimeEstimation | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

onMounted(async () => {
  await loadBatchResults()
})

async function loadBatchResults() {
  loading.value = true
  error.value = null

  try {
    const mockResults: MachiningTimeEstimation[] = [
      {
        filename: 'PDM-249322_03.stp',
        part_type: 'ROT',
        roughing_time_min: 12.5,
        finishing_time_min: 3.2,
        setup_time_min: 5.0,
        total_time_min: 20.7,
        breakdown: {
          material: '1.4301 (X5CrNi18-10)',
          stock_volume_mm3: 125000,
          part_volume_mm3: 85000,
          material_to_remove_mm3: 40000,
          material_removal_percent: 32,
          surface_area_mm2: 15000,
          machining_strategy: {
            rough: { mrr_mm3_min: 3200, cutting_time_min: 12.5 },
            finish: { mrr_mm3_min: 800, cutting_time_min: 3.2 }
          },
          critical_constraints: [],
          constraint_multiplier: 1.0,
          pure_machining_time_min: 15.7
        }
      }
    ]

    batchResults.value = mockResults
    const firstResult = mockResults[0]
    selectedResult.value = firstResult ?? null
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load batch results'
  } finally {
    loading.value = false
  }
}

function handleSelect(result: MachiningTimeEstimation) {
  selectedResult.value = result
}
</script>

<template>
  <div class="machining-time-estimation-module split-pane-layout">
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading batch results...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <p class="error-message">{{ error }}</p>
    </div>

    <template v-else>
      <div class="left-pane">
        <BatchEstimationTable :results="batchResults" @select="handleSelect" />
      </div>

      <div class="right-pane">
        <EstimationDetailPanel v-if="selectedResult" :result="selectedResult" />
        <div v-else class="empty-state">
          <FileQuestion :size="48" class="empty-icon" />
          <p>Select a result to view details</p>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.machining-time-estimation-module {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
  height: 100%;
  background: var(--bg-base);
  padding: var(--space-4);
}

.left-pane,
.right-pane {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-secondary);
}

.loading-state p,
.empty-state p {
  margin-top: var(--space-4);
  font-size: var(--text-base);
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.empty-icon {
  color: var(--text-tertiary);
}

.error-message {
  color: var(--color-danger);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  background: rgba(244, 63, 94, 0.1);
}
</style>
