<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { ChevronLeftIcon, ChevronRightIcon, ZoomInIcon, ZoomOutIcon, ScanIcon, DownloadIcon } from 'lucide-vue-next'
import { usePartsStore } from '@/stores/parts'
import { useItemTypeGuard } from '@/composables/useItemTypeGuard'
import * as filesApi from '@/api/files'
import { apiClient } from '@/api/client'
import type { PDFDocumentProxy, RenderTask } from 'pdfjs-dist'
import type { FileWithLinks } from '@/types/file-record'
import type { ContextGroup } from '@/types/workspace'
import Spinner from '@/components/ui/Spinner.vue'
import { ICON_SIZE_SM } from '@/config/design'
import pdfjsWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

// ── Module-level caches ────────────────────────────────────────────────────
const _fileCache = new Map<number, FileWithLinks[]>()
const _fetchedFor = new Map<string, number>()
const _docCache = new Map<number, PDFDocumentProxy>()

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()
const typeGuard = useItemTypeGuard(['part'])
const part = computed(() => parts.getFocusedPart(props.ctx))

// ── File state ─────────────────────────────────────────────────────────────
const files = ref<FileWithLinks[]>([])
const loading = ref(false)
const error = ref(false)
const selectedFileId = ref<number | null>(null)

const OCCT_EXTS = new Set(['step', 'stp', 'iges', 'igs', 'brep', 'brp', 'stl', 'obj', '3mf'])

function fileExt(f: FileWithLinks): string {
  return f.original_filename.split('.').pop()?.toLowerCase() ?? ''
}

function fileKind(f: FileWithLinks): 'pdf' | '3d' | 'other' {
  if (f.mime_type === 'application/pdf') return 'pdf'
  if (OCCT_EXTS.has(fileExt(f))) return '3d'
  return 'other'
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const selectedFile = computed(() => {
  if (selectedFileId.value != null)
    return files.value.find(f => f.id === selectedFileId.value) ?? null
  return files.value[0] ?? null
})

const selectedKind = computed(() => selectedFile.value ? fileKind(selectedFile.value) : null)
const isRefetching = computed(() => loading.value && files.value.length > 0)

// ── Files loader ───────────────────────────────────────────────────────────
watch(
  part,
  async (p) => {
    if (!p) { files.value = []; selectedFileId.value = null; return }
    if (_fileCache.has(p.id)) files.value = _fileCache.get(p.id)!
    if (_fetchedFor.get(props.leafId) === p.id) return
    _fetchedFor.set(props.leafId, p.id)
    loading.value = true
    error.value = false
    try {
      files.value = await filesApi.listByEntity('part', p.id)
      _fileCache.set(p.id, files.value)
      selectedFileId.value = null
    } catch {
      error.value = true
      _fetchedFor.delete(props.leafId)
      if (!files.value.length) files.value = []
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)

// ── PDF state ──────────────────────────────────────────────────────────────
const canvasRef = ref<HTMLCanvasElement | null>(null)
const pdfContainerRef = ref<HTMLDivElement | null>(null)
const pdfLoading = ref(false)
const pdfError = ref(false)
const currentPage = ref(1)
const totalPages = ref(0)
const zoom = ref<number | 'fit'>('fit')
const displayZoom = ref('Fit')
const canvasTransform = ref('')

const ZOOM_STEP = 0.25
const ZOOM_MIN = 0.25
const ZOOM_MAX = 4.0

let _pdfDoc: PDFDocumentProxy | null = null
let _renderTask: RenderTask | null = null
let _lastFitScale = 1.0
let _pdfResizeObserver: ResizeObserver | null = null
let _pdfResizeTimer: ReturnType<typeof setTimeout> | null = null
let _vpResizeTimer: ReturnType<typeof setTimeout> | null = null
let _renderedW = 0
let _renderedH = 0

const isFit = computed(() => zoom.value === 'fit')

async function renderPage(doc: PDFDocumentProxy, pageNum: number) {
  if (!canvasRef.value || !pdfContainerRef.value) return
  if (_renderTask) { _renderTask.cancel(); _renderTask = null }

  const page = await doc.getPage(pageNum)
  const w = pdfContainerRef.value.clientWidth
  const h = pdfContainerRef.value.clientHeight
  if (!w || !h) return

  const vpScale = window.visualViewport?.scale ?? 1
  const dpr = (window.devicePixelRatio || 1) * vpScale
  const vp = page.getViewport({ scale: 1 })

  let scale: number
  if (zoom.value === 'fit') {
    const fitScale = Math.min(w / vp.width, h / vp.height)
    _lastFitScale = fitScale
    displayZoom.value = `${Math.round(fitScale * 100)}%`
    scale = fitScale * dpr
  } else {
    scale = (zoom.value as number) * dpr
    displayZoom.value = `${Math.round((zoom.value as number) * 100)}%`
  }

  const scaledVp = page.getViewport({ scale })
  const pw = Math.round(scaledVp.width)
  const ph = Math.round(scaledVp.height)
  const cssW = Math.round(scaledVp.width / dpr)
  const cssH = Math.round(scaledVp.height / dpr)

  const offscreen = document.createElement('canvas')
  offscreen.width = pw
  offscreen.height = ph

  _renderTask = page.render({ canvas: offscreen, viewport: scaledVp })
  try {
    await _renderTask.promise
  } catch {
    _renderTask = null
    return
  }
  _renderTask = null

  const canvas = canvasRef.value
  if (!canvas) return
  canvas.width = pw
  canvas.height = ph
  canvas.style.width = `${cssW}px`
  canvas.style.height = `${cssH}px`
  canvas.getContext('2d')?.drawImage(offscreen, 0, 0)
  canvasTransform.value = ''
  _renderedW = w
  _renderedH = h
}

async function loadPdf(fileId: number) {
  pdfLoading.value = true
  pdfError.value = false
  currentPage.value = 1
  totalPages.value = 0
  _pdfDoc = null
  zoom.value = 'fit'

  try {
    const pdfjsLib = await import('pdfjs-dist')
    pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorkerUrl

    let doc = _docCache.get(fileId) ?? null
    if (!doc) {
      doc = await pdfjsLib.getDocument(filesApi.previewUrl(fileId)).promise
      _docCache.set(fileId, doc)
    }
    _pdfDoc = doc
    totalPages.value = doc.numPages
    pdfLoading.value = false
    await nextTick()
    await renderPage(doc, 1)
  } catch {
    pdfError.value = true
    pdfLoading.value = false
  }
}

function zoomIn() {
  const current = zoom.value === 'fit' ? _lastFitScale : (zoom.value as number)
  zoom.value = Math.min(Math.round((current + ZOOM_STEP) / ZOOM_STEP) * ZOOM_STEP, ZOOM_MAX)
  if (_pdfDoc) renderPage(_pdfDoc, currentPage.value)
}

function zoomOut() {
  const current = zoom.value === 'fit' ? _lastFitScale : (zoom.value as number)
  zoom.value = Math.max(Math.round((current - ZOOM_STEP) / ZOOM_STEP) * ZOOM_STEP, ZOOM_MIN)
  if (_pdfDoc) renderPage(_pdfDoc, currentPage.value)
}

function fitPage() {
  zoom.value = 'fit'
  if (_pdfDoc) renderPage(_pdfDoc, currentPage.value)
}

watch(currentPage, (p) => { if (_pdfDoc) renderPage(_pdfDoc, p) })

watch(pdfContainerRef, (el) => {
  if (_pdfResizeObserver) { _pdfResizeObserver.disconnect(); _pdfResizeObserver = null }
  if (!el) return
  _pdfResizeObserver = new ResizeObserver((entries) => {
    const rect = entries[0]?.contentRect
    if (!rect) return
    const { width: newW, height: newH } = rect
    if (zoom.value === 'fit' && _renderedW > 0 && _renderedH > 0) {
      const s = Math.min(newW / _renderedW, newH / _renderedH)
      canvasTransform.value = `scale(${s.toFixed(4)})`
    }
    if (_pdfResizeTimer) clearTimeout(_pdfResizeTimer)
    _pdfResizeTimer = setTimeout(() => {
      if (_pdfDoc) renderPage(_pdfDoc, currentPage.value)
    }, 200)
  })
  _pdfResizeObserver.observe(el)
  if (_pdfDoc) renderPage(_pdfDoc, currentPage.value)
})

function onVisualViewportResize() {
  if (_vpResizeTimer) clearTimeout(_vpResizeTimer)
  _vpResizeTimer = setTimeout(() => {
    if (_pdfDoc) renderPage(_pdfDoc, currentPage.value)
  }, 150)
}

// ── 3D state ───────────────────────────────────────────────────────────────
const containerEl3d = ref<HTMLElement | null>(null)
const loadingModel = ref(false)
let ovViewer: { Destroy(): void; Resize(): void } | null = null
let _3dResizeObserver: ResizeObserver | null = null
let _3dResizeTimer: ReturnType<typeof setTimeout> | null = null

function destroyViewer() {
  if (ovViewer) { ovViewer.Destroy(); ovViewer = null }
}

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

async function loadModel(file: FileWithLinks) {
  await nextTick()
  if (!containerEl3d.value) return
  destroyViewer()
  loadingModel.value = true

  try {
    const isOcct = OCCT_EXTS.has(fileExt(file))
    const [OV, resp] = await Promise.all([
      import('online-3d-viewer'),
      apiClient.get<Blob>(`/files/${file.id}/download`, { responseType: 'blob' }),
    ])
    const blob = resp.data as Blob
    const ovFile = new File([blob], file.original_filename)
    let uint8: Uint8Array | null = null
    if (isOcct) uint8 = new Uint8Array(await blob.arrayBuffer())

    const viewer = new OV.EmbeddedViewer(containerEl3d.value, {
      backgroundColor: new OV.RGBAColor(20, 22, 28, 255),
      defaultColor: new OV.RGBColor(210, 218, 228),
      edgeSettings: new OV.EdgeSettings(true, new OV.RGBColor(20, 25, 38), 35),
      onModelLoaded: isOcct ? async () => {
        try {
          const [THREE, occtMod] = await Promise.all([
            import('three'),
            import('occt-import-js'),
          ])
          const occt = await occtMod.default({ locateFile: () => '/occt/occt-import-js.wasm' })
          const tessParams = { linearDeflectionType: 'bounding_box_ratio', linearDeflection: 0.002, angularDeflection: 0.08 }
          const ext = fileExt(file)
          const result = ext === 'iges' || ext === 'igs'
            ? occt.ReadIgesFile(uint8!, tessParams)
            : ext === 'brep' || ext === 'brp'
              ? occt.ReadBrepFile(uint8!, tessParams)
              : occt.ReadStepFile(uint8!, tessParams)
          if (!result.success || result.meshes.length === 0) return
          const ovScene = viewer.GetViewer().scene
          ovScene.traverse((obj: { type: string; visible: boolean }) => {
            if (obj.type === 'LineSegments') obj.visible = false
          })
          const edgeMat = new THREE.LineBasicMaterial({ color: 0x202028 })
          for (const mesh of result.meshes) {
            const edgeGeom = extractBRepEdges(mesh.attributes.position.array, mesh.index.array, mesh.brep_faces, THREE)
            if (edgeGeom.getAttribute('position').count > 0) {
              ovScene.add(new THREE.LineSegments(edgeGeom, edgeMat))
            }
          }
          viewer.GetViewer().Render()
        } catch { /* prázdný stav */ }
      } : undefined,
    })

    viewer.GetViewer().SetNavigationMode(OV.NavigationMode.FreeOrbit)
    viewer.LoadModelFromFileList([ovFile])
    ovViewer = viewer
    if (_3dResizeTimer) clearTimeout(_3dResizeTimer)
    _3dResizeTimer = setTimeout(() => ovViewer?.Resize(), 300)
  } catch { /* prázdný stav */ } finally {
    loadingModel.value = false
  }
}

watch(containerEl3d, (el) => {
  if (_3dResizeObserver) { _3dResizeObserver.disconnect(); _3dResizeObserver = null }
  if (!el) return
  _3dResizeObserver = new ResizeObserver(() => {
    if (_3dResizeTimer) clearTimeout(_3dResizeTimer)
    _3dResizeTimer = setTimeout(() => ovViewer?.Resize(), 150)
  })
  _3dResizeObserver.observe(el)
})

// ── Unified file selection ─────────────────────────────────────────────────
watch(selectedFile, (f) => {
  // Cleanup previous viewer when switching types
  if (!f || fileKind(f) !== '3d') destroyViewer()
  if (!f || fileKind(f) !== 'pdf') {
    if (_renderTask) { _renderTask.cancel(); _renderTask = null }
    _pdfDoc = null
  }
  if (!f) return
  const kind = fileKind(f)
  if (kind === 'pdf') loadPdf(f.id)
  if (kind === '3d') loadModel(f)
})

onMounted(() => {
  window.visualViewport?.addEventListener('resize', onVisualViewportResize)
})

onUnmounted(() => {
  if (_renderTask) _renderTask.cancel()
  if (_pdfResizeObserver) _pdfResizeObserver.disconnect()
  if (_pdfResizeTimer) clearTimeout(_pdfResizeTimer)
  if (_vpResizeTimer) clearTimeout(_vpResizeTimer)
  window.visualViewport?.removeEventListener('resize', onVisualViewportResize)
  destroyViewer()
  if (_3dResizeObserver) _3dResizeObserver.disconnect()
  if (_3dResizeTimer) clearTimeout(_3dResizeTimer)
})

const downloadUrl = computed(() =>
  selectedFile.value ? `/api/files/${selectedFile.value.id}/download` : null,
)
</script>

<template>
  <div :class="['wdocs', { refetching: isRefetching }]">
    <div v-if="!typeGuard.isSupported(props.ctx)" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Nedostupné pro {{ typeGuard.focusedTypeName(props.ctx) }}</span>
    </div>

    <div v-else-if="!part" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Vyberte díl ze seznamu</span>
    </div>

    <div v-else-if="loading && !files.length" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>

    <div v-else-if="!files.length" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Díl nemá žádné soubory</span>
    </div>

    <template v-else>
      <!-- File list — always visible -->
      <div class="file-list">
        <button
          v-for="f in files"
          :key="f.id"
          :class="['file-item', { active: f.id === selectedFile?.id }]"
          :data-testid="`doc-file-${f.id}`"
          @click="selectedFileId = f.id"
        >
          <span :class="['file-badge', `badge-${fileKind(f)}`]">
            {{ fileKind(f) === 'pdf' ? 'PDF' : fileKind(f) === '3d' ? '3D' : fileExt(f).toUpperCase() }}
          </span>
          <span class="file-name">{{ f.original_filename }}</span>
          <span class="file-size">{{ formatBytes(f.file_size) }}</span>
        </button>
      </div>

      <!-- PDF viewer -->
      <div v-if="selectedKind === 'pdf'" class="viewer-wrap">
        <div v-if="pdfLoading" class="mod-placeholder">
          <Spinner size="sm" />
        </div>
        <div v-else-if="pdfError" class="mod-placeholder">
          <div class="mod-dot err" />
          <span class="mod-label">Chyba při načítání PDF</span>
        </div>
        <div ref="pdfContainerRef" :class="['pdf-canvas-wrap', { scrollable: !isFit }]">
          <canvas
            ref="canvasRef"
            :class="['pdf-canvas', { hidden: pdfLoading || pdfError }]"
            :style="canvasTransform ? { transform: canvasTransform } : undefined"
          />
        </div>
        <div v-if="!pdfLoading && !pdfError && totalPages > 0" class="pdf-bar">
          <button class="pdf-nav-btn" :disabled="currentPage <= 1" data-testid="pdf-prev" title="Předchozí strana" @click="currentPage--">
            <ChevronLeftIcon :size="ICON_SIZE_SM - 2" />
          </button>
          <span class="pdf-page-info">{{ currentPage }} / {{ totalPages }}</span>
          <button class="pdf-nav-btn" :disabled="currentPage >= totalPages" data-testid="pdf-next" title="Další strana" @click="currentPage++">
            <ChevronRightIcon :size="ICON_SIZE_SM - 2" />
          </button>
          <span class="pdf-sep" />
          <button class="pdf-nav-btn" :disabled="zoom !== 'fit' && (zoom as number) <= ZOOM_MIN" data-testid="pdf-zoom-out" title="Oddálit" @click="zoomOut">
            <ZoomOutIcon :size="ICON_SIZE_SM - 2" />
          </button>
          <span class="pdf-zoom-label" data-testid="pdf-zoom-label">{{ displayZoom }}</span>
          <button class="pdf-nav-btn" :disabled="zoom !== 'fit' && (zoom as number) >= ZOOM_MAX" data-testid="pdf-zoom-in" title="Přiblížit" @click="zoomIn">
            <ZoomInIcon :size="ICON_SIZE_SM - 2" />
          </button>
          <button :class="['pdf-nav-btn', { active: isFit }]" data-testid="pdf-fit" title="Přizpůsobit panelu" @click="fitPage">
            <ScanIcon :size="ICON_SIZE_SM - 2" />
          </button>
          <span class="pdf-fill" />
          <a v-if="downloadUrl" :href="downloadUrl" target="_blank" rel="noopener" class="pdf-dl" title="Stáhnout soubor" data-testid="pdf-download">
            <DownloadIcon :size="11" />
          </a>
        </div>
      </div>

      <!-- 3D viewer -->
      <div v-else-if="selectedKind === '3d'" class="viewer-wrap">
        <div v-if="loadingModel" class="model-loading">
          <Spinner size="sm" />
        </div>
        <div ref="containerEl3d" class="ov-container" data-testid="3d-viewer-container" />
      </div>

      <!-- Other file: download -->
      <div v-else-if="selectedFile" class="mod-placeholder">
        <div class="mod-dot" />
        <div class="file-info-name">{{ selectedFile.original_filename }}</div>
        <div class="file-info-meta">{{ fileExt(selectedFile).toUpperCase() }} · {{ formatBytes(selectedFile.file_size) }}</div>
        <a :href="`/api/files/${selectedFile.id}/download`" class="dl-link" target="_blank" :data-testid="`file-download-${selectedFile.id}`">
          Stáhnout soubor
        </a>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wdocs {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  transition: opacity 0.15s;
}
.wdocs.refetching { opacity: 0.4; }

.mod-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
}
.mod-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--b2); }
.mod-dot.err { background: var(--err); }
.mod-label { font-size: var(--fsm); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

/* ─── File list ─── */
.file-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  border-bottom: 1px solid var(--b1);
  max-height: 130px;
  overflow-y: auto;
  flex-shrink: 0;
}
.file-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px var(--pad);
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  color: var(--t2);
  font-size: var(--fs);
  transition: background 0.1s;
}
.file-item:hover { background: var(--b1); }
.file-item.active { background: var(--b1); color: var(--t1); }
.file-badge {
  font-size: var(--fss);
  font-weight: 600;
  padding: 1px 4px;
  border-radius: var(--rs);
  background: var(--b2);
  color: var(--t3);
  flex-shrink: 0;
}
.badge-pdf { color: var(--red); }
.badge-3d  { color: var(--ok); }
.file-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-size { font-size: var(--fsm); color: var(--t4); flex-shrink: 0; }

/* ─── Viewer wrapper ─── */
.viewer-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

/* ─── PDF canvas ─── */
.pdf-canvas-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: var(--ground);
}
.pdf-canvas-wrap.scrollable { overflow: auto; align-items: flex-start; justify-content: flex-start; }
.pdf-canvas { display: block; }
.pdf-canvas.hidden { visibility: hidden; }

/* ─── PDF toolbar ─── */
.pdf-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 1px;
  padding: 2px 4px;
  border-top: 1px solid var(--b1);
  background: var(--raised);
  min-height: 26px;
}
.pdf-sep { width: 1px; height: 12px; background: var(--b2); margin: 0 3px; flex-shrink: 0; }
.pdf-fill { flex: 1; }
.pdf-nav-btn {
  width: 22px; height: 22px;
  display: flex; align-items: center; justify-content: center;
  background: none; border: none; color: var(--t3); cursor: pointer;
  border-radius: var(--rs);
  transition: color 0.08s, background 0.08s;
  flex-shrink: 0;
}
.pdf-nav-btn:hover:not(:disabled) { color: var(--t1); background: var(--b2); }
.pdf-nav-btn:disabled { opacity: 0.3; cursor: default; }
.pdf-nav-btn.active { color: var(--t1); background: var(--b2); }
.pdf-nav-btn:focus-visible { outline: 2px solid rgba(255,255,255,0.5); }
.pdf-page-info { font-size: var(--fsm); color: var(--t3); padding: 0 3px; white-space: nowrap; }
.pdf-zoom-label { font-size: var(--fsm); color: var(--t3); padding: 0 3px; white-space: nowrap; min-width: 34px; text-align: center; }
.pdf-dl {
  width: 22px; height: 22px;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--rs); border: 1px solid var(--b2);
  color: var(--t3); text-decoration: none;
  transition: color 0.1s, border-color 0.1s, background 0.1s;
  flex-shrink: 0;
}
.pdf-dl:hover { color: var(--t1); border-color: var(--b3); background: var(--b1); }
.pdf-dl:focus-visible { outline: 2px solid rgba(255,255,255,0.5); }

/* ─── 3D viewer ─── */
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
.ov-container :deep(canvas) { display: block; }

/* ─── Other file ─── */
.file-info-name { font-size: var(--fs); color: var(--t1); font-weight: 500; }
.file-info-meta { font-size: var(--fsm); color: var(--t4); }
.dl-link {
  margin-top: 4px;
  padding: 5px 14px;
  border-radius: var(--rs);
  border: 1px solid var(--b2);
  color: var(--t2);
  font-size: var(--fs);
  text-decoration: none;
  transition: border-color 0.15s, color 0.15s;
}
.dl-link:hover { border-color: var(--b3); color: var(--t1); }
</style>
