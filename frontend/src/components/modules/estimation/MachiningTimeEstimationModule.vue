<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { MachiningTimeEstimation } from '@/types/estimation'
import BatchEstimationTable from './BatchEstimationTable.vue'
import EstimationDetailPanel from './EstimationDetailPanel.vue'
import { FileQuestion } from 'lucide-vue-next'
import { useMachiningTimeEstimation } from '@/composables/useMachiningTimeEstimation'

const selectedResult = ref<MachiningTimeEstimation | null>(null)
const { results: batchResults, fetchBatchResults, loading, error } = useMachiningTimeEstimation()

onMounted(async () => {
  await loadBatchResults()
})

async function loadBatchResults() {
  await fetchBatchResults()
  console.log('📊 Batch results loaded:', batchResults.value.length, 'files')
  console.log('First result:', batchResults.value[0])
  if (batchResults.value.length > 0) {
    selectedResult.value = batchResults.value[0] ?? null
    console.log('✅ Selected first result:', selectedResult.value?.filename)
  } else {
    console.warn('⚠️ No batch results received!')
  }
}

function handleSelect(result: MachiningTimeEstimation) {
  selectedResult.value = result
}

function handleUpdated(newEstimate: MachiningTimeEstimation) {
  const index = batchResults.value.findIndex(r => r.filename === newEstimate.filename)
  if (index !== -1) {
    batchResults.value[index] = newEstimate
  }
  selectedResult.value = newEstimate
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
        <div v-if="!selectedResult" class="empty-state">
          <FileQuestion :size="48" class="empty-icon" />
          <p>Select a result to view details</p>
          <p class="debug-info">Debug: selectedResult is {{ selectedResult === null ? 'NULL' : 'NOT NULL' }}</p>
        </div>
        <EstimationDetailPanel
          v-else
          :result="selectedResult"
          :all-results="batchResults"
          @updated="handleUpdated"
          @select="handleSelect"
        />
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

.debug-info {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin-top: var(--space-2);
  font-family: var(--font-mono);
}
</style>
