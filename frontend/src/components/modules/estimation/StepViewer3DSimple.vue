<template>
  <div class="step-viewer-simple">
    <div class="viewer-header">
      <h4>🔧 3D Model — {{ filename }}</h4>
      <button @click="resetCamera" class="control-btn" title="Reset Camera">
        🎯 Reset View
      </button>
    </div>

    <div ref="canvasContainer" class="canvas-container">
      <div v-if="loading" class="loading-overlay">
        <div class="spinner"></div>
        <p>Loading STEP model...</p>
      </div>
      <div v-else-if="error" class="error-overlay">
        <p>⚠️ Failed to load model</p>
        <p class="error-detail">{{ error }}</p>
      </div>
      <canvas ref="canvas" v-show="!loading && !error"></canvas>
    </div>

    <div class="viewer-info">
      <span class="info-item">📐 {{ bboxX.toFixed(1) }} × {{ bboxY.toFixed(1) }} × {{ bboxZ.toFixed(1) }} mm</span>
      <span class="info-item">📊 {{ (partVolume / 1000).toFixed(1) }} cm³</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

interface Props {
  filename: string
  bboxX: number
  bboxY: number
  bboxZ: number
  partVolume: number
}

const props = defineProps<Props>()

// Refs
const canvas = ref<HTMLCanvasElement | null>(null)
const canvasContainer = ref<HTMLDivElement | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// Three.js objects
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let renderer: THREE.WebGLRenderer | null = null
let controls: OrbitControls | null = null
let partMesh: THREE.Mesh | null = null
let animationFrameId: number | null = null

async function initViewer() {
  if (!canvas.value || !canvasContainer.value) return

  try {
    loading.value = true
    error.value = null

    // Scene setup
    scene = new THREE.Scene()
    scene.background = new THREE.Color(0x2a2a2a) // Dark background

    // Camera setup
    const width = canvasContainer.value.clientWidth
    const height = canvasContainer.value.clientHeight
    camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 10000)
    camera.position.set(200, 200, 200)

    // Renderer setup
    renderer = new THREE.WebGLRenderer({ canvas: canvas.value, antialias: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(window.devicePixelRatio)

    // Orbit controls
    controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05

    // Lighting (brighter for light part on dark background)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4)
    scene.add(ambientLight)

    const directionalLight1 = new THREE.DirectionalLight(0xffffff, 0.6)
    directionalLight1.position.set(100, 100, 100)
    scene.add(directionalLight1)

    const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.4)
    directionalLight2.position.set(-100, -100, -100)
    scene.add(directionalLight2)

    // Grid (darker for dark background)
    const gridSize = Math.max(props.bboxX, props.bboxY, props.bboxZ) * 2
    const grid = new THREE.GridHelper(gridSize, 20, 0x505050, 0x404040)
    scene.add(grid)

    // Axes
    const axes = new THREE.AxesHelper(gridSize / 4)
    scene.add(axes)

    // Load STEP model
    await loadStepModel()

    // Start animation loop
    animate()

    loading.value = false
  } catch (err) {
    console.error('Viewer initialization failed:', err)
    error.value = (err as Error).message
    loading.value = false
  }
}

async function loadStepModel() {
  try {
    // Use occt-import-js WASM to load STEP file
    const occtimportjs = (window as any).occtimportjs

    if (!occtimportjs) {
      throw new Error('OCCT WASM not loaded')
    }

    const occt = await occtimportjs()

    // Fetch STEP file
    const stepUrl = `/uploads/drawings/${props.filename}`
    const response = await fetch(stepUrl)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const stepData = await response.arrayBuffer()
    const fileBuffer = new Uint8Array(stepData)

    // Read STEP with OCCT
    const result = occt.ReadStepFile(fileBuffer, null)

    if (!result.success) {
      throw new Error('Failed to parse STEP file')
    }

    // Create Three.js geometry from OCCT mesh
    const geometry = new THREE.BufferGeometry()

    // Vertices
    const vertices = new Float32Array(result.meshes[0].attributes.position.array)
    geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3))

    // Normals
    if (result.meshes[0].attributes.normal) {
      const normals = new Float32Array(result.meshes[0].attributes.normal.array)
      geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3))
    } else {
      geometry.computeVertexNormals()
    }

    // Index
    if (result.meshes[0].index) {
      const indices = new Uint32Array(result.meshes[0].index.array)
      geometry.setIndex(new THREE.BufferAttribute(indices, 1))
    }

    // Material - light gray with edges
    const material = new THREE.MeshStandardMaterial({
      color: 0xd0d0d0, // Light gray
      metalness: 0.3,
      roughness: 0.5,
      flatShading: false
    })

    // Create mesh
    partMesh = new THREE.Mesh(geometry, material)
    partMesh.castShadow = true
    partMesh.receiveShadow = true

    // Add edges for better visibility
    const edges = new THREE.EdgesGeometry(geometry, 15) // 15 degree threshold
    const lineMaterial = new THREE.LineBasicMaterial({ color: 0x000000, linewidth: 1 })
    const edgeLines = new THREE.LineSegments(edges, lineMaterial)
    partMesh.add(edgeLines)

    // Add to scene
    scene!.add(partMesh)

    // Center camera on part
    const box = new THREE.Box3().setFromObject(partMesh)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    const maxDim = Math.max(size.x, size.y, size.z)

    camera!.position.set(center.x + maxDim, center.y + maxDim, center.z + maxDim)
    controls!.target.copy(center)
    controls!.update()
  } catch (err) {
    console.error('STEP loading failed:', err)
    throw new Error('Failed to load STEP model: ' + (err as Error).message)
  }
}

function animate() {
  animationFrameId = requestAnimationFrame(animate)

  if (controls) {
    controls.update()
  }

  if (renderer && scene && camera) {
    renderer.render(scene, camera)
  }
}

function resetCamera() {
  if (!partMesh || !camera || !controls) return

  const box = new THREE.Box3().setFromObject(partMesh)
  const center = box.getCenter(new THREE.Vector3())
  const size = box.getSize(new THREE.Vector3())
  const maxDim = Math.max(size.x, size.y, size.z)

  camera.position.set(center.x + maxDim, center.y + maxDim, center.z + maxDim)
  controls.target.copy(center)
  controls.update()
}

function cleanup() {
  if (animationFrameId !== null) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }

  if (partMesh) {
    if (partMesh.geometry) partMesh.geometry.dispose()
    if (partMesh.material) {
      if (Array.isArray(partMesh.material)) {
        partMesh.material.forEach(m => m.dispose())
      } else {
        partMesh.material.dispose()
      }
    }
    partMesh = null
  }

  if (renderer) {
    renderer.dispose()
    renderer = null
  }

  scene = null
  camera = null
  controls = null
}

onMounted(() => {
  initViewer()
})

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.step-viewer-simple {
  display: flex;
  flex-direction: column;
  height: 500px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.viewer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3);
  background: var(--bg-accent);
  border-bottom: 1px solid var(--border-default);
}

.viewer-header h4 {
  margin: 0;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
}

.control-btn {
  padding: var(--space-2) var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.control-btn:hover {
  background: var(--bg-hover);
  border-color: var(--color-primary);
}

.canvas-container {
  position: relative;
  flex: 1;
  background: #2a2a2a; /* Match Three.js scene background */
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
  background: rgba(255, 255, 255, 0.95);
  z-index: 10;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-overlay p,
.error-overlay p {
  margin: var(--space-3) 0 0 0;
  font-size: var(--text-base);
  color: var(--text-secondary);
}

.error-detail {
  font-size: var(--text-sm);
  color: var(--color-error);
}

.viewer-info {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-accent);
  border-top: 1px solid var(--border-default);
  font-size: var(--text-sm);
}

.info-item {
  color: var(--text-secondary);
}
</style>
