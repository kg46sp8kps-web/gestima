<script setup lang="ts">
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useItemTypeGuard } from '@/composables/useItemTypeGuard'
import * as filesApi from '@/api/files'
import { apiClient } from '@/api/client'
import type { FileWithLinks } from '@/types/file-record'
import type { ContextGroup } from '@/types/workspace'
import type { WebGLRenderer, PerspectiveCamera } from 'three'
import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import Spinner from '@/components/ui/Spinner.vue'
import InlineSelect from '@/components/ui/InlineSelect.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()
const typeGuard = useItemTypeGuard(['part'])

const OCCT_EXTS = new Set(['step', 'stp', 'iges', 'igs', 'brep', 'brp'])
const VIEW_EXTS = new Set([...OCCT_EXTS, 'stl', 'obj', '3mf'])

const files = ref<FileWithLinks[]>([])
const selectedId = ref<number | null>(null)
const loading = ref(false)
const loadingModel = ref(false)
const containerEl = ref<HTMLElement | null>(null)

interface ThreeState {
  renderer: WebGLRenderer
  camera: PerspectiveCamera
  controls: OrbitControls
  render: () => void
}
let threeState: ThreeState | null = null
let ovViewer: { Destroy(): void; Resize(): void } | null = null
let _resizeObserver: ResizeObserver | null = null
let _resizeTimer: ReturnType<typeof setTimeout> | null = null

const part = computed(() => parts.getFocusedPart(props.ctx))

function fileExt(f: FileWithLinks): string {
  return f.original_filename.split('.').pop()?.toLowerCase() ?? ''
}

function is3DFile(f: FileWithLinks): boolean {
  return VIEW_EXTS.has(fileExt(f))
}

function destroyViewer() {
  if (threeState) {
    threeState.controls.dispose()
    threeState.renderer.dispose()
    threeState.renderer.domElement.remove()
    threeState = null
  }
  if (ovViewer) {
    ovViewer.Destroy()
    ovViewer = null
  }
}

function onResize() {
  const el = containerEl.value
  if (!el) return
  if (threeState) {
    const w = el.clientWidth
    const h = el.clientHeight
    threeState.camera.aspect = w / h
    threeState.camera.updateProjectionMatrix()
    threeState.renderer.setSize(w, h)
    threeState.render()
  } else if (ovViewer) {
    ovViewer.Resize()
  }
}

function scheduleResize(delay = 150) {
  if (_resizeTimer) clearTimeout(_resizeTimer)
  _resizeTimer = setTimeout(onResize, delay)
}

async function loadFiles(partId: number) {
  loading.value = true
  files.value = []
  try {
    const all = await filesApi.listByEntity('part', partId)
    files.value = all.filter(is3DFile)
    selectedId.value = files.value[0]?.id ?? null
  } catch {
    // prázdný stav
  } finally {
    loading.value = false
  }
}

// ─── B-Rep edge extraction ────────────────────────────────────────────────
// Každá plocha (brep_face) má range trojúhelníků.
// Hrana uvnitř plochy se vyskytuje 2× → cancels out.
// Hrana na okraji plochy se vyskytuje 1× → to je B-Rep hrana.
// Výsledek: přesné hrany modelu (rádiusy, rohy, díry) bez threshold.

function extractBRepEdges(
  positions: number[],
  indices: number[],
  brepFaces: Array<{ first: number; last: number; color: [number, number, number] | null }>,
  THREE: typeof import('three'),
): import('three').BufferGeometry {
  const verts: number[] = []

  for (const face of brepFaces) {
    const boundary = new Map<string, [number, number]>()

    for (let t = face.first; t <= face.last; t++) {
      const i0 = indices[t * 3]!
      const i1 = indices[t * 3 + 1]!
      const i2 = indices[t * 3 + 2]!
      for (const [a, b] of [
        [Math.min(i0, i1), Math.max(i0, i1)],
        [Math.min(i1, i2), Math.max(i1, i2)],
        [Math.min(i2, i0), Math.max(i2, i0)],
      ] as [number, number][]) {
        const k = `${a}_${b}`
        // Hrana viděna 2× = interní; viděna 1× = boundary
        if (boundary.has(k)) boundary.delete(k)
        else boundary.set(k, [a, b])
      }
    }

    for (const [a, b] of boundary.values()) {
      verts.push(
        positions[a * 3]!, positions[a * 3 + 1]!, positions[a * 3 + 2]!,
        positions[b * 3]!, positions[b * 3 + 1]!, positions[b * 3 + 2]!,
      )
    }
  }

  const geom = new THREE.BufferGeometry()
  geom.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3))
  return geom
}

// ─── Custom Three.js renderer (STEP / IGES / BREP) ───────────────────────

async function loadWithOcct(file: FileWithLinks, container: HTMLElement) {
  const [THREE, { OrbitControls }, occtMod, resp] = await Promise.all([
    import('three'),
    import('three/examples/jsm/controls/OrbitControls.js'),
    import('occt-import-js'),
    apiClient.get<Blob>(`/files/${file.id}/download`, { responseType: 'blob' }),
  ])

  const uint8 = new Uint8Array(await (resp.data as Blob).arrayBuffer())
  const occt = await occtMod.default({ locateFile: () => '/occt/occt-import-js.wasm' })

  const tessParams = {
    linearDeflectionType: 'bounding_box_ratio',
    linearDeflection: 0.005,
    angularDeflection: 0.2,
  }
  const ext = fileExt(file)
  const result = ext === 'iges' || ext === 'igs'
    ? occt.ReadIgesFile(uint8, tessParams)
    : ext === 'brep' || ext === 'brp'
      ? occt.ReadBrepFile(uint8, tessParams)
      : occt.ReadStepFile(uint8, tessParams)

  if (!result.success || result.meshes.length === 0) return

  const w = container.clientWidth
  const h = container.clientHeight

  const renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setClearColor(0x1a1c22, 1)
  container.appendChild(renderer.domElement)

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(45, w / h, 0.001, 100000)

  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = false
  controls.minPolarAngle = 0
  controls.maxPolarAngle = Math.PI

  const faceMat = new THREE.MeshBasicMaterial({
    color: 0xc8cdd8,
    polygonOffset: true,
    polygonOffsetFactor: 1,
    polygonOffsetUnits: 1,
  })
  const edgeMat = new THREE.LineBasicMaterial({ color: 0x0c0f18 })

  const group = new THREE.Group()

  for (const mesh of result.meshes) {
    const pos = mesh.attributes.position.array
    const idx = mesh.index.array

    const faceGeom = new THREE.BufferGeometry()
    faceGeom.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3))
    if (mesh.attributes.normal) {
      faceGeom.setAttribute('normal', new THREE.Float32BufferAttribute(mesh.attributes.normal.array, 3))
    }
    faceGeom.setIndex(idx)
    const faceMesh = new THREE.Mesh(faceGeom, faceMat)
    faceMesh.renderOrder = 0
    group.add(faceMesh)

    if (mesh.brep_faces.length > 0) {
      const edgeGeom = extractBRepEdges(pos, idx, mesh.brep_faces, THREE)
      if (edgeGeom.getAttribute('position').count > 0) {
        const edgeMesh = new THREE.LineSegments(edgeGeom, edgeMat)
        edgeMesh.renderOrder = 1
        group.add(edgeMesh)
      }
    }
  }

  scene.add(group)

  // Kamera na model
  const box = new THREE.Box3().setFromObject(group)
  const center = box.getCenter(new THREE.Vector3())
  const size = box.getSize(new THREE.Vector3())
  const maxDim = Math.max(size.x, size.y, size.z)
  camera.position.set(center.x + maxDim * 1.5, center.y + maxDim, center.z + maxDim * 1.5)
  controls.target.copy(center)
  controls.update()

  // On-demand rendering — renderujeme pouze při pohybu, žádný RAF loop
  function render() { renderer.render(scene, camera) }
  controls.addEventListener('change', render)
  render()

  threeState = { renderer, camera, controls, render }
}

// ─── Fallback: online-3d-viewer (STL, OBJ, 3MF) ─────────────────────────

async function loadWithOv(file: FileWithLinks, container: HTMLElement) {
  const [OV, resp] = await Promise.all([
    import('online-3d-viewer'),
    apiClient.get<Blob>(`/files/${file.id}/download`, { responseType: 'blob' }),
  ])
  const f = new File([resp.data as BlobPart], file.original_filename)
  const viewer = new OV.EmbeddedViewer(container, {
    backgroundColor: new OV.RGBAColor(20, 22, 28, 255),
    defaultColor: new OV.RGBColor(228, 232, 238),
    edgeSettings: new OV.EdgeSettings(false, new OV.RGBColor(20, 25, 38), 35),
  })
  viewer.GetViewer().SetNavigationMode(OV.NavigationMode.FreeOrbit)
  viewer.LoadModelFromFileList([f])
  ovViewer = viewer
  scheduleResize(300)
}

// ─── Orchestrace ─────────────────────────────────────────────────────────

async function loadModel(file: FileWithLinks) {
  await nextTick()
  if (!containerEl.value) return
  destroyViewer()
  loadingModel.value = true
  try {
    if (OCCT_EXTS.has(fileExt(file))) {
      await loadWithOcct(file, containerEl.value)
    } else {
      await loadWithOv(file, containerEl.value)
    }
  } catch {
    // prázdný stav
  } finally {
    loadingModel.value = false
  }
}

watch(selectedId, async (id) => {
  if (!id) return
  const file = files.value.find(f => f.id === id)
  if (file) loadModel(file)
})

watch(part, (p) => {
  files.value = []
  selectedId.value = null
  destroyViewer()
  if (p) loadFiles(p.id)
}, { immediate: true })

watch(containerEl, (el) => {
  _resizeObserver?.disconnect()
  if (!el) return
  _resizeObserver = new ResizeObserver(() => scheduleResize(150))
  _resizeObserver.observe(el)
})

onBeforeUnmount(() => {
  destroyViewer()
  _resizeObserver?.disconnect()
  if (_resizeTimer) clearTimeout(_resizeTimer)
})
</script>

<template>
  <div class="w3d">
    <div v-if="!typeGuard.isSupported(ctx)" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">{{ typeGuard.focusedTypeName(ctx) }} nepodporuje 3D</span>
    </div>

    <div v-else-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <div v-else-if="!part" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Žádný díl</span>
    </div>

    <div v-else-if="files.length === 0" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Žádné 3D soubory</span>
    </div>

    <template v-else>
      <div v-if="files.length > 1" class="file-bar">
        <InlineSelect
          :modelValue="selectedId !== null ? String(selectedId) : ''"
          @update:modelValue="selectedId = $event ? Number($event) : null"
          class="file-sel"
          data-testid="3d-file-select"
        >
          <option v-for="f in files" :key="f.id" :value="String(f.id)">
            {{ f.original_filename }}
          </option>
        </InlineSelect>
      </div>

      <div class="viewer-area">
        <div v-if="loadingModel" class="model-loading" data-testid="3d-loading">
          <Spinner size="sm" />
        </div>
        <div ref="containerEl" class="ov-container" data-testid="3d-viewer-container" />
      </div>
    </template>
  </div>
</template>

<style scoped>
.w3d {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.mod-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
}

.mod-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--b2);
}

.mod-label {
  font-size: var(--fsm);
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.file-bar {
  display: flex;
  align-items: center;
  padding: 5px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}

/* visual styles come from InlineSelect component */
.file-sel { flex: 1; height: 28px; }

.viewer-area {
  flex: 1;
  min-height: 0;
  position: relative;
  overflow: hidden;
}

.model-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(14, 16, 24, 0.8);
  z-index: 2;
}

.ov-container {
  position: absolute;
  inset: 0;
}

.ov-container :deep(canvas) {
  display: block;
}
</style>
