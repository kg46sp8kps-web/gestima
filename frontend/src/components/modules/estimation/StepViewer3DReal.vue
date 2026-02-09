<template>
  <div class="step-viewer-3d-real">
    <div class="viewer-header">
      <h4>3D Preview — {{ filename }}</h4>
      <div class="viewer-controls">
        <button @click="toggleStock" :class="{ active: showStock }" class="control-btn" title="Toggle Stock">
          <Package :size="14" /> Stock
        </button>
        <button @click="togglePart" :class="{ active: showPart }" class="control-btn" title="Toggle Part">
          <Wrench :size="14" /> Part
        </button>
        <button @click="toggleRemoval" :class="{ active: showRemoval }" class="control-btn" title="Toggle Removal Material">
          <CircleDot :size="14" /> Removal
        </button>
        <button @click="toggleFeatures" :class="{ active: showFeatures }" class="control-btn" title="Toggle Feature Colors">
          <Palette :size="14" /> Features
        </button>
        <button @click="resetCamera" class="control-btn" title="Reset Camera">
          <Target :size="14" /> Reset
        </button>
      </div>
    </div>

    <div ref="canvasContainer" class="canvas-container">
      <div v-if="loading" class="loading-overlay">
        <div class="spinner"></div>
        <p>Loading 3D model...</p>
        <p class="hint">{{ loadingStep }}</p>
      </div>
      <div v-else-if="error" class="error-overlay">
        <p><AlertTriangle :size="20" /> {{ error }}</p>
        <button @click="retryLoad" class="retry-btn"><RefreshCw :size="16" /> Retry</button>
      </div>
      <canvas ref="canvas" v-show="!loading && !error"></canvas>
    </div>

    <div class="viewer-info">
      <span class="info-item"><Ruler :size="14" /> BBox: {{ bbox }}</span>
      <span class="info-item"><PieChart :size="14" /> Part: {{ volume }}</span>
      <span class="info-item"><RefreshCw :size="14" /> Removal: {{ removal }}%</span>
      <span v-if="featureCount > 0" class="info-item"><Palette :size="14" /> Features: {{ featureCount }}</span>
    </div>

    <!-- FEATURE LEGEND -->
    <div v-if="showFeatures && features.length > 0" class="feature-legend">
      <h5>Identified Features:</h5>
      <div class="legend-items">
        <div v-for="(feature, idx) in uniqueFeatures" :key="idx" class="legend-item">
          <span class="color-box" :style="{ background: feature.color }"></span>
          <span class="feature-name">{{ feature.label }} ({{ feature.count }})</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { Package, Wrench, CircleDot, Palette, Target, Ruler, PieChart, RefreshCw, AlertTriangle } from 'lucide-vue-next'

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

// Refs
const canvas = ref<HTMLCanvasElement | null>(null)
const canvasContainer = ref<HTMLDivElement | null>(null)
const loading = ref(true)
const loadingStep = ref('Initializing...')
const error = ref<string | null>(null)

// Visibility toggles
const showStock = ref(true)
const showPart = ref(true)
const showRemoval = ref(false)
const showFeatures = ref(false)

// Three.js objects
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let renderer: THREE.WebGLRenderer | null = null
let controls: OrbitControls | null = null
let stockMesh: THREE.LineSegments | null = null
let partMesh: THREE.Mesh | null = null
let removalMesh: THREE.Mesh | null = null
let animationFrameId: number | null = null

// Feature data
const features = ref<Array<{ type: string; color: string; faceIndices: number[] }>>([])
const featureCount = computed(() => features.value.length)

// Computed
const bbox = computed(() =>
  `${props.bboxX.toFixed(0)} × ${props.bboxY.toFixed(0)} × ${props.bboxZ.toFixed(0)} mm`
)
const volume = computed(() => `${props.partVolume.toFixed(0)} mm³`)
const removal = computed(() => `${(props.removalRatio * 100).toFixed(0)}`)

const uniqueFeatures = computed(() => {
  const map = new Map<string, { label: string; color: string; count: number }>()
  features.value.forEach(f => {
    const existing = map.get(f.type)
    if (existing) {
      existing.count++
    } else {
      map.set(f.type, { label: f.type, color: f.color, count: 1 })
    }
  })
  return Array.from(map.values())
})

// FEATURE COLOR MAPPING (from CLAUDE.local.md session 2026-02-07)
const FEATURE_COLORS: Record<string, string> = {
  // Cylindrical
  shaft_segment: '#4CAF50',    // green
  bore: '#2196F3',              // blue
  groove_wall: '#FF9800',       // orange
  step_transition: '#9C27B0',   // purple

  // Planar
  end_face: '#FFEB3B',          // yellow
  step_face: '#00BCD4',         // cyan
  pocket_bottom: '#E91E63',     // pink
  groove_bottom: '#FF5722',     // deep orange

  // Conical
  chamfer: '#8BC34A',           // light green
  taper: '#FFC107',             // amber

  // Toroidal
  fillet_inner: '#9E9E9E',      // gray
  fillet_outer: '#607D8B',      // blue-gray

  // Unknown
  unknown: '#CCCCCC'            // light gray
}

// Initialize 3D scene
function init3DScene() {
  if (!canvas.value || !canvasContainer.value) return

  // Scene
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x1a1a1a)

  // Camera
  const aspect = canvasContainer.value.clientWidth / canvasContainer.value.clientHeight
  camera = new THREE.PerspectiveCamera(50, aspect, 0.1, 10000)
  camera.position.set(props.bboxX * 1.5, props.bboxY * 1.5, props.bboxZ * 2)
  camera.lookAt(0, 0, 0)

  // Renderer
  renderer = new THREE.WebGLRenderer({ canvas: canvas.value, antialias: true })
  renderer.setSize(canvasContainer.value.clientWidth, canvasContainer.value.clientHeight)
  renderer.setPixelRatio(window.devicePixelRatio)

  // Controls
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05

  // Lights
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
  scene.add(ambientLight)

  const directionalLight1 = new THREE.DirectionalLight(0xffffff, 0.8)
  directionalLight1.position.set(1, 1, 1)
  scene.add(directionalLight1)

  const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.4)
  directionalLight2.position.set(-1, -1, -0.5)
  scene.add(directionalLight2)

  // Grid helper
  const gridHelper = new THREE.GridHelper(Math.max(props.bboxX, props.bboxY, props.bboxZ) * 2, 20)
  scene.add(gridHelper)

  // Axes helper
  const axesHelper = new THREE.AxesHelper(Math.max(props.bboxX, props.bboxY, props.bboxZ))
  scene.add(axesHelper)
}

// Load STEP file and render
async function loadAndRender() {
  loading.value = true
  error.value = null
  loadingStep.value = 'Loading STEP file...'

  try {
    init3DScene()

    // Create stock (wireframe box)
    loadingStep.value = 'Creating stock geometry...'
    createStockMesh()

    // Load part geometry via backend
    loadingStep.value = 'Loading part geometry...'
    const stepPath = `/uploads/drawings/${props.filename}`

    // Simple placeholder geometry (real OCCT integration would go here)
    loadingStep.value = 'Parsing STEP data...'
    await createPlaceholderPartGeometry()

    // Load features if available
    if (showFeatures.value) {
      loadingStep.value = 'Loading feature data...'
      await loadFeatureData()
    }

    loading.value = false
    animate()
  } catch (err: any) {
    error.value = err.message || 'Failed to load 3D model'
    loading.value = false
  }
}

function createStockMesh() {
  if (!scene) return

  // Cylindrical stock for ROT parts, box for PRI
  const isRotational = props.rotationalScore > 0.6
  let geometry: THREE.BufferGeometry

  if (isRotational) {
    const diameter = Math.max(props.bboxX, props.bboxY)
    const length = props.bboxZ
    geometry = new THREE.CylinderGeometry(diameter / 2, diameter / 2, length, 32)
    geometry.rotateX(Math.PI / 2)  // Align with Z-axis
  } else {
    geometry = new THREE.BoxGeometry(props.bboxX, props.bboxY, props.bboxZ)
  }

  const edges = new THREE.EdgesGeometry(geometry)
  stockMesh = new THREE.LineSegments(
    edges,
    new THREE.LineBasicMaterial({ color: 0x666666, linewidth: 2 })
  )
  stockMesh.visible = showStock.value
  scene.add(stockMesh)
}

async function createPlaceholderPartGeometry() {
  if (!scene) return

  // Placeholder: Create simplified part mesh
  // TODO: Replace with real OCCT mesh from backend
  const scale = 0.8
  const geometry = new THREE.BoxGeometry(
    props.bboxX * scale,
    props.bboxY * scale,
    props.bboxZ * scale
  )

  const material = new THREE.MeshPhongMaterial({
    color: 0x2196F3,
    transparent: false,
    side: THREE.DoubleSide
  })

  partMesh = new THREE.Mesh(geometry, material)
  partMesh.visible = showPart.value
  scene!.add(partMesh)
}

async function loadFeatureData() {
  // TODO: Call backend endpoint /api/step/face-features/{filename}
  // For now, create mock features
  features.value = [
    { type: 'shaft_segment', color: FEATURE_COLORS.shaft_segment ?? '#4CAF50', faceIndices: [0, 1] },
    { type: 'end_face', color: FEATURE_COLORS.end_face ?? '#FFEB3B', faceIndices: [2, 3] },
    { type: 'chamfer', color: FEATURE_COLORS.chamfer ?? '#8BC34A', faceIndices: [4] }
  ]
}

function animate() {
  if (!renderer || !scene || !camera || !controls) return

  animationFrameId = requestAnimationFrame(animate)
  controls.update()
  renderer.render(scene, camera)
}

function toggleStock() {
  showStock.value = !showStock.value
  if (stockMesh) stockMesh.visible = showStock.value
}

function togglePart() {
  showPart.value = !showPart.value
  if (partMesh) partMesh.visible = showPart.value
}

function toggleRemoval() {
  showRemoval.value = !showRemoval.value
  if (removalMesh) removalMesh.visible = showRemoval.value
}

function toggleFeatures() {
  showFeatures.value = !showFeatures.value
  // TODO: Switch part material to feature-colored multi-material
}

function resetCamera() {
  if (!camera || !controls) return
  camera.position.set(props.bboxX * 1.5, props.bboxY * 1.5, props.bboxZ * 2)
  camera.lookAt(0, 0, 0)
  controls.reset()
}

function retryLoad() {
  loadAndRender()
}

function handleResize() {
  if (!camera || !renderer || !canvasContainer.value) return
  const width = canvasContainer.value.clientWidth
  const height = canvasContainer.value.clientHeight
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

watch(() => props.filename, () => {
  cleanup()
  loadAndRender()
})

onMounted(() => {
  loadAndRender()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  cleanup()
  window.removeEventListener('resize', handleResize)
})

function cleanup() {
  if (animationFrameId !== null) {
    cancelAnimationFrame(animationFrameId)
  }
  if (renderer) {
    renderer.dispose()
  }
  if (controls) {
    controls.dispose()
  }
  // Clear scene objects
  scene = null
  camera = null
  renderer = null
  controls = null
  stockMesh = null
  partMesh = null
  removalMesh = null
}
</script>

<style scoped>
.step-viewer-3d-real {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  min-height: 600px;
}

.viewer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-default);
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
  flex-wrap: wrap;
}

.control-btn {
  padding: var(--space-1) var(--space-2);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.control-btn:hover {
  background: var(--bg-hover);
  transform: translateY(-1px);
}

.control-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.canvas-container {
  position: relative;
  flex: 1;
  min-height: 400px;
  background: #1a1a1a;
  border-radius: var(--radius-md);
  overflow: hidden;
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
  background: rgba(0, 0, 0, 0.9);
  color: white;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid rgba(255, 255, 255, 0.2);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.hint {
  font-size: var(--text-sm);
  opacity: 0.7;
}

.retry-btn {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--text-sm);
}

.viewer-info {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-2);
  background: var(--bg-surface);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  flex-wrap: wrap;
}

.info-item {
  color: var(--text-secondary);
  white-space: nowrap;
}

.feature-legend {
  padding: var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.feature-legend h5 {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.legend-items {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--space-2);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.color-box {
  width: 16px;
  height: 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-default);
  flex-shrink: 0;
}

.feature-name {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}
</style>
