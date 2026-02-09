<template>
  <div class="step-viewer-3d">
    <div class="viewer-header">
      <h4>3D Preview</h4>
      <div class="viewer-controls">
        <button @click="toggleStock" :class="{ active: showStock }" class="control-btn">
          {{ showStock ? '📦' : '📦' }} Stock
        </button>
        <button @click="togglePart" :class="{ active: showPart }" class="control-btn">
          {{ showPart ? '🔧' : '🔧' }} Part
        </button>
        <button @click="toggleNegative" :class="{ active: showNegative }" class="control-btn">
          {{ showNegative ? '🔴' : '🔴' }} Removal
        </button>
      </div>
    </div>

    <div ref="canvasContainer" class="canvas-container">
      <div v-if="loading" class="loading-overlay">
        <div class="spinner"></div>
        <p>Loading STEP file...</p>
      </div>
      <div v-else-if="error" class="error-overlay">
        <p>⚠️ {{ error }}</p>
        <p class="hint">3D viewer requires OCCT backend support</p>
      </div>
      <canvas ref="canvas" v-show="!loading && !error"></canvas>
    </div>

    <div class="viewer-info">
      <span class="info-item">📐 BBox: {{ bbox }}</span>
      <span class="info-item">📊 Volume: {{ volume }}</span>
      <span class="info-item">🔄 Removal: {{ removal }}%</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'

interface Props {
  filename: string
  bboxX: number
  bboxY: number
  bboxZ: number
  partVolume: number
  removalRatio: number
  rotationalScore: number
}

const props = defineProps<Props>()

const canvas = ref<HTMLCanvasElement | null>(null)
const canvasContainer = ref<HTMLDivElement | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const showStock = ref(true)
const showPart = ref(true)
const showNegative = ref(false)

const bbox = computed(() =>
  `${props.bboxX.toFixed(0)} × ${props.bboxY.toFixed(0)} × ${props.bboxZ.toFixed(0)} mm`
)
const volume = computed(() => `${props.partVolume.toFixed(0)} mm³`)
const removal = computed(() => `${(props.removalRatio * 100).toFixed(0)}`)

// Placeholder for 3D rendering (requires Three.js + occt-import-js)
function init3DViewer() {
  if (!canvas.value) return

  error.value = '3D viewer coming soon (requires Three.js + OCCT integration)'

  // TODO: Implement 3D rendering
  // 1. Load STEP file via /api/step/load/{filename}
  // 2. Parse with occt-import-js WASM
  // 3. Render with Three.js:
  //    - Stock: Wireframe box (transparent gray)
  //    - Part: Solid mesh (blue)
  //    - Negative: Stock - Part volume (red transparent)
}

function toggleStock() {
  showStock.value = !showStock.value
  // TODO: Update Three.js scene
}

function togglePart() {
  showPart.value = !showPart.value
  // TODO: Update Three.js scene
}

function toggleNegative() {
  showNegative.value = !showNegative.value
  // TODO: Update Three.js scene
}

watch(() => props.filename, () => {
  init3DViewer()
})

onMounted(() => {
  init3DViewer()
})

onUnmounted(() => {
  // TODO: Cleanup Three.js scene
})
</script>

<style scoped>
.step-viewer-3d {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  height: 500px;
}

.viewer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.viewer-header h4 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.viewer-controls {
  display: flex;
  gap: var(--space-2);
}

.control-btn {
  padding: var(--space-1) var(--space-2);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all 0.2s;
}

.control-btn:hover {
  background: var(--bg-hover);
}

.control-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.canvas-container {
  position: relative;
  flex: 1;
  background: #1a1a1a;
  border-radius: var(--radius-md);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.loading-overlay,
.error-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  background: rgba(0, 0, 0, 0.8);
  color: white;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255, 255, 255, 0.2);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-overlay p {
  margin: 0;
  text-align: center;
}

.hint {
  font-size: var(--text-sm);
  opacity: 0.7;
}

.viewer-info {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-2);
  background: var(--bg-surface);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}

.info-item {
  color: var(--text-secondary);
}
</style>
