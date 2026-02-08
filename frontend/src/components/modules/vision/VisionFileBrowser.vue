<template>
  <div class="vision-file-browser">
    <div class="browser-layout">
      <!-- LEFT: File list -->
      <div class="file-list-panel">
        <div class="panel-header">
          <h3>Drawing Pairs ({{ drawingPairs.length }})</h3>
        </div>

        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>Scanning files...</p>
        </div>

        <div v-else-if="error" class="error-state">
          <p>{{ error }}</p>
          <button @click="loadDrawingPairs" class="retry-button">Retry</button>
        </div>

        <div v-else class="file-pairs-list">
          <div
            v-for="pair in drawingPairs"
            :key="pair.baseName"
            class="file-pair"
            :class="{ selected: selectedPair?.baseName === pair.baseName }"
            @click="selectPair(pair)"
          >
            <div class="pair-name">{{ pair.baseName }}</div>
            <div class="pair-files">
              <span class="file-icon">📄</span>
              <span class="file-icon">🔷</span>
            </div>
          </div>
        </div>
      </div>

      <!-- RIGHT: PDF Preview + Analyze button -->
      <div class="preview-panel">
        <div v-if="!selectedPair" class="empty-state">
          <p>← Select a drawing pair to preview PDF</p>
        </div>

        <template v-else>
          <div class="panel-header">
            <h3>{{ selectedPair.baseName }}</h3>
            <button
              @click="startAnalysis"
              :disabled="analyzing"
              class="analyze-button"
            >
              {{ analyzing ? 'Starting...' : '🔍 Analyze This Part' }}
            </button>
          </div>

          <div class="pdf-viewer">
            <iframe
              :src="`/uploads/drawings/${selectedPair.pdfFile}`"
              class="pdf-frame"
            ></iframe>
          </div>

          <div class="file-info">
            <div class="info-row">
              <span class="label">PDF:</span>
              <span class="value">{{ selectedPair.pdfFile }}</span>
            </div>
            <div class="info-row">
              <span class="label">STEP:</span>
              <span class="value">{{ selectedPair.stepFile }}</span>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { apiClient } from '@/api/client'

interface DrawingPair {
  baseName: string
  pdfFile: string
  stepFile: string
}

const emit = defineEmits<{
  'analysis-started': [jobId: string, pair: DrawingPair]
}>()

const drawingPairs = ref<DrawingPair[]>([])
const selectedPair = ref<DrawingPair | null>(null)
const loading = ref(false)
const analyzing = ref(false)
const error = ref<string | null>(null)

async function loadDrawingPairs() {
  loading.value = true
  error.value = null

  try {
    const response = await apiClient.get<DrawingPair[]>('/vision-debug/drawing-files')
    drawingPairs.value = response.data
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to load drawing files'
    console.error('Failed to load drawing pairs:', err)
  } finally {
    loading.value = false
  }
}

function selectPair(pair: DrawingPair) {
  selectedPair.value = pair
}

async function startAnalysis() {
  if (!selectedPair.value) return

  analyzing.value = true
  error.value = null

  try {
    const response = await apiClient.post<{ job_id: string; base_name: string }>(
      '/vision-debug/refine-annotations-files',
      null,
      {
        params: {
          pdf_filename: selectedPair.value.pdfFile,
          step_filename: selectedPair.value.stepFile
        }
      }
    )

    emit('analysis-started', response.data.job_id, selectedPair.value)
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to start analysis'
    console.error('Failed to start analysis:', err)
  } finally {
    analyzing.value = false
  }
}

onMounted(() => {
  loadDrawingPairs()
})
</script>

<style scoped>
.vision-file-browser {
  height: 100%;
  background: var(--color-background);
}

.browser-layout {
  display: grid;
  grid-template-columns: 350px 1fr;
  height: 100%;
  gap: 0;
}

/* LEFT PANEL: File List */
.file-list-panel {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--color-border);
  background: var(--color-background-elevated);
}

.panel-header {
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-header h3 {
  margin: 0;
  font-size: var(--font-size-md);
  color: var(--color-text-primary);
}

.file-pairs-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-sm);
}

.file-pair {
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--border-radius-sm);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xs);
}

.file-pair:hover {
  background: var(--color-background-hover);
}

.file-pair.selected {
  background: var(--color-primary-light);
  border-left: 3px solid var(--color-primary);
}

.pair-name {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  font-weight: 500;
}

.pair-files {
  display: flex;
  gap: var(--spacing-xs);
}

.file-icon {
  font-size: var(--font-size-sm);
}

/* RIGHT PANEL: Preview */
.preview-panel {
  display: flex;
  flex-direction: column;
  background: var(--color-background);
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-secondary);
}

.pdf-viewer {
  flex: 1;
  min-height: 0;
  background: #525659;
}

.pdf-frame {
  width: 100%;
  height: 100%;
  border: none;
}

.file-info {
  padding: var(--spacing-sm) var(--spacing-md);
  border-top: 1px solid var(--color-border);
  background: var(--color-background-elevated);
  font-size: var(--font-size-xs);
}

.info-row {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.info-row .label {
  font-weight: 600;
  color: var(--color-text-secondary);
  min-width: 50px;
}

.info-row .value {
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
}

.analyze-button {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--border-radius-sm);
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.analyze-button:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.analyze-button:disabled {
  background: var(--color-border);
  cursor: not-allowed;
  opacity: 0.6;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
  gap: var(--spacing-md);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.retry-button {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--border-radius-sm);
  cursor: pointer;
}
</style>
