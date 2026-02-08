<script setup lang="ts">
/**
 * Vision Debug Module - FILE-BASED MODE
 *
 * No database required — select files directly from uploads/drawings/
 *
 * Modes:
 * 1. FILE_BROWSER: Select PDF + STEP pair
 * 2. ANALYSIS: Watch refinement progress
 */

import { ref } from 'vue'
import { useUiStore } from '@/stores/ui'
import VisionFileBrowser from '../vision/VisionFileBrowser.vue'
import VisionStatusBar from './VisionStatusBar.vue'
import VisionPdfPanel from './VisionPdfPanel.vue'
import VisionFeaturesPanel from './VisionFeaturesPanel.vue'

interface DrawingPair {
  baseName: string
  pdfFile: string
  stepFile: string
}

interface RefinementFeature {
  type: string
  dimension: number
  depth?: number
  step_data: any
}

const uiStore = useUiStore()

// Mode state
const mode = ref<'browser' | 'analysis'>('browser')

// Analysis state
const jobId = ref('')
const currentPair = ref<DrawingPair | null>(null)
const iteration = ref(0)
const error = ref(100.0)
const extractedFeatures = ref<RefinementFeature[]>([])
const converged = ref(false)
const annotatedPdfUrl = ref('')
const originalPdfUrl = ref('')
const analyzing = ref(false)

let eventSource: EventSource | null = null

function onAnalysisStarted(newJobId: string, pair: DrawingPair) {
  jobId.value = newJobId
  currentPair.value = pair
  mode.value = 'analysis'

  // Set original PDF URL
  originalPdfUrl.value = `/uploads/drawings/${pair.pdfFile}`

  // Start watching progress
  watchProgress(newJobId)
}

function watchProgress(jobIdValue: string) {
  analyzing.value = true

  const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  eventSource = new EventSource(`${baseUrl}/api/vision-debug/progress/${jobIdValue}`)

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)

      // Defensive updates - handle partial data
      if (data.iteration != null) iteration.value = data.iteration
      if (data.error != null) error.value = data.error
      if (data.converged != null) converged.value = data.converged
      if (data.features) extractedFeatures.value = data.features
      if (data.annotated_pdf_url) annotatedPdfUrl.value = data.annotated_pdf_url

      // Handle completion
      if (data.status === 'completed' || data.converged) {
        analyzing.value = false
        eventSource?.close()
        eventSource = null
        if (data.iteration != null && data.error != null) {
          uiStore.showSuccess(`Converged in ${data.iteration} iterations (error: ${(data.error * 100).toFixed(2)}%)`)
        }
      }

      // Handle failure
      if (data.status === 'failed') {
        analyzing.value = false
        eventSource?.close()
        eventSource = null
        uiStore.showError(data.error_message || 'Analysis failed')
      }
    } catch (err) {
      console.error('Failed to parse SSE data:', err)
    }
  }

  eventSource.onerror = () => {
    uiStore.showError('Connection lost')
    analyzing.value = false
    eventSource?.close()
    eventSource = null
  }
}

function backToBrowser() {
  // Reset state
  mode.value = 'browser'
  jobId.value = ''
  currentPair.value = null
  iteration.value = 0
  error.value = 100.0
  extractedFeatures.value = []
  converged.value = false
  annotatedPdfUrl.value = ''
  originalPdfUrl.value = ''
  analyzing.value = false

  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}
</script>

<template>
  <div class="vision-debug-module">
    <!-- MODE 1: File Browser -->
    <div v-if="mode === 'browser'" class="browser-mode">
      <VisionFileBrowser @analysis-started="onAnalysisStarted" />
    </div>

    <!-- MODE 2: Analysis View -->
    <div v-else class="analysis-mode">
      <div class="analysis-header">
        <button @click="backToBrowser" class="back-button">← Back to File Browser</button>
        <div class="current-pair">
          <span class="label">Analyzing:</span>
          <span class="pair-name">{{ currentPair?.baseName }}</span>
        </div>
      </div>

      <VisionStatusBar
        :iteration="iteration"
        :error="error"
        :converged="converged"
        :analyzing="analyzing"
        :feature-count="extractedFeatures.length"
      />

      <div class="panels-container">
        <VisionPdfPanel title="Original PDF" :pdf-url="originalPdfUrl" />
        <VisionPdfPanel
          title="Annotated PDF"
          :pdf-url="annotatedPdfUrl"
          :iteration="iteration"
          :loading="analyzing"
        />
        <VisionFeaturesPanel :features="extractedFeatures" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.vision-debug-module {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-background);
}

.browser-mode,
.analysis-mode {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.analysis-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-background-elevated);
}

.back-button {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-sm);
  cursor: pointer;
  font-size: var(--font-size-sm);
  transition: all 0.2s;
}

.back-button:hover {
  background: var(--color-background-hover);
  border-color: var(--color-primary);
}

.current-pair {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.current-pair .label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.current-pair .pair-name {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
}

.panels-container {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--spacing-md);
  flex: 1;
  min-height: 0;
  padding: var(--spacing-md);
}
</style>
