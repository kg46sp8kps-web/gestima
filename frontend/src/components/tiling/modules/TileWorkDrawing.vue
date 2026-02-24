<script setup lang="ts">
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import { ChevronLeftIcon, ChevronRightIcon, ZoomInIcon, ZoomOutIcon, ScanIcon, DownloadIcon } from 'lucide-vue-next'
import { usePartsStore } from '@/stores/parts'
import { useItemTypeGuard } from '@/composables/useItemTypeGuard'
import * as filesApi from '@/api/files'
import type { PDFDocumentProxy, RenderTask } from 'pdfjs-dist'
import type { FileWithLinks } from '@/types/file-record'
import type { ContextGroup } from '@/types/workspace'
import Spinner from '@/components/ui/Spinner.vue'
import { ICON_SIZE_SM } from '@/config/design'
// ?url tells Vite to resolve this to a URL string at build time — no code loaded yet
import pdfjsWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

// ── Module-level caches (survive unmount/remount) ──────────────────────────
const _fileCache = new Map<number, FileWithLinks[]>()
const _fetchedFor = new Map<string, number>()
// PDF documents are expensive to load — cache by file ID across mounts
const _docCache = new Map<number, PDFDocumentProxy>()

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()
const typeGuard = useItemTypeGuard(['part'])

const part = computed(() => parts.getFocusedPart(props.ctx))

const files = ref<FileWithLinks[]>([])
const loading = ref(false)
const error = ref(false)
const selectedFileId = ref<number | null>(null)

const selectedFile = computed(() => {
  if (selectedFileId.value != null)
    return files.value.find(f => f.id === selectedFileId.value) ?? null
  return files.value[0] ?? null
})

// ── PDF renderer state ─────────────────────────────────────────────────────
const canvasRef = ref<HTMLCanvasElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)
const pdfLoading = ref(false)
const pdfError = ref(false)
const currentPage = ref(1)
const totalPages = ref(0)

// Zoom: 'fit' = přizpůsobit panelu, number = absolutní měřítko (0.25–4.0)
const zoom = ref<number | 'fit'>('fit')
const displayZoom = ref('Fit')

const ZOOM_STEP = 0.25
const ZOOM_MIN = 0.25
const ZOOM_MAX = 4.0

// Non-reactive — no need for Vue tracking on these
let _pdfDoc: PDFDocumentProxy | null = null
let _renderTask: RenderTask | null = null
let _lastFitScale = 1.0
let _resizeObserver: ResizeObserver | null = null
let _resizeTimer: ReturnType<typeof setTimeout> | null = null

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const isRefetching = computed(() => loading.value && files.value.length > 0)
const isFit = computed(() => zoom.value === 'fit')

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

// ── PDF renderer ───────────────────────────────────────────────────────────
async function renderPage(doc: PDFDocumentProxy, pageNum: number) {
  if (!canvasRef.value || !containerRef.value) return

  if (_renderTask) {
    _renderTask.cancel()
    _renderTask = null
  }

  const page = await doc.getPage(pageNum)
  const w = containerRef.value.clientWidth
  const h = containerRef.value.clientHeight
  if (!w || !h) return

  const dpr = window.devicePixelRatio || 1
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

  const canvas = canvasRef.value
  canvas.width = Math.round(scaledVp.width)
  canvas.height = Math.round(scaledVp.height)
  canvas.style.width = `${Math.round(scaledVp.width / dpr)}px`
  canvas.style.height = `${Math.round(scaledVp.height / dpr)}px`

  // pdfjs-dist v5: pass canvas element directly (canvasContext is deprecated)
  _renderTask = page.render({ canvas, viewport: scaledVp })
  try {
    await _renderTask.promise
  } catch {
    // RenderingCancelledException on rapid changes — expected, ignore
  }
  _renderTask = null
}

async function loadPdf(fileId: number) {
  pdfLoading.value = true
  pdfError.value = false
  currentPage.value = 1
  totalPages.value = 0
  _pdfDoc = null
  zoom.value = 'fit'

  try {
    // Lazy-load pdfjs-dist — only executed on first PDF open
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
    await nextTick() // ensure canvas is in DOM before rendering
    await renderPage(doc, 1)
  } catch {
    pdfError.value = true
    pdfLoading.value = false
  }
}

// ── Zoom actions ───────────────────────────────────────────────────────────
function zoomIn() {
  const current = zoom.value === 'fit' ? _lastFitScale : (zoom.value as number)
  const next = Math.round((current + ZOOM_STEP) / ZOOM_STEP) * ZOOM_STEP
  zoom.value = Math.min(next, ZOOM_MAX)
  if (_pdfDoc) renderPage(_pdfDoc, currentPage.value)
}

function zoomOut() {
  const current = zoom.value === 'fit' ? _lastFitScale : (zoom.value as number)
  const next = Math.round((current - ZOOM_STEP) / ZOOM_STEP) * ZOOM_STEP
  zoom.value = Math.max(next, ZOOM_MIN)
  if (_pdfDoc) renderPage(_pdfDoc, currentPage.value)
}

function fitPage() {
  zoom.value = 'fit'
  if (_pdfDoc) renderPage(_pdfDoc, currentPage.value)
}

// Load PDF when selected file changes
watch(selectedFile, (f) => {
  if (f?.mime_type === 'application/pdf') loadPdf(f.id)
})

// Re-render when page changes
watch(currentPage, (p) => {
  if (_pdfDoc) renderPage(_pdfDoc, p)
})

// ResizeObserver — set up when container mounts, re-render on panel resize
watch(containerRef, (el) => {
  if (_resizeObserver) {
    _resizeObserver.disconnect()
    _resizeObserver = null
  }
  if (!el) return
  _resizeObserver = new ResizeObserver(() => {
    if (_resizeTimer) clearTimeout(_resizeTimer)
    _resizeTimer = setTimeout(() => {
      if (_pdfDoc) renderPage(_pdfDoc, currentPage.value)
    }, 200)
  })
  _resizeObserver.observe(el)
  // Container just appeared (file selector switch) — render if doc already loaded
  if (_pdfDoc) renderPage(_pdfDoc, currentPage.value)
})

onUnmounted(() => {
  if (_renderTask) _renderTask.cancel()
  if (_resizeObserver) _resizeObserver.disconnect()
  if (_resizeTimer) clearTimeout(_resizeTimer)
})

const downloadUrl = computed(() =>
  selectedFile.value ? `/api/files/${selectedFile.value.id}/download` : null,
)
</script>

<template>
  <div :class="['wdrw', { refetching: isRefetching }]">
    <!-- Unsupported item type -->
    <div v-if="!typeGuard.isSupported(props.ctx)" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Nedostupné pro {{ typeGuard.focusedTypeName(props.ctx) }}</span>
    </div>

    <!-- No part selected -->
    <div v-else-if="!part" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Vyberte díl ze seznamu</span>
    </div>

    <!-- Loading files -->
    <div v-else-if="loading && !files.length" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Error loading files -->
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>

    <!-- No files -->
    <div v-else-if="!files.length" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Díl nemá žádné soubory</span>
    </div>

    <!-- Data -->
    <template v-else>
      <!-- File selector — shown when part has multiple files -->
      <div v-if="files.length > 1" class="file-list">
        <button
          v-for="f in files"
          :key="f.id"
          :class="['file-item', { active: f.id === selectedFile?.id }]"
          :data-testid="`file-item-${f.id}`"
          @click="selectedFileId = f.id"
        >
          <span class="file-type">{{ f.file_type.toUpperCase() }}</span>
          <span class="file-name">{{ f.original_filename }}</span>
          <span class="file-size">{{ formatBytes(f.file_size) }}</span>
        </button>
      </div>

      <!-- PDF canvas viewer -->
      <div
        v-if="selectedFile?.mime_type === 'application/pdf'"
        class="pdf-wrap"
      >
        <!-- Loading spinner -->
        <div v-if="pdfLoading" class="mod-placeholder">
          <Spinner size="sm" />
        </div>

        <!-- Error state -->
        <div v-else-if="pdfError" class="mod-placeholder">
          <div class="mod-dot err" />
          <span class="mod-label">Chyba při načítání PDF</span>
        </div>

        <!-- Canvas area — flex:1, centers the canvas, ref for ResizeObserver -->
        <!-- overflow:auto enables scrolling when zoomed in beyond fit -->
        <div ref="containerRef" :class="['pdf-canvas-wrap', { scrollable: !isFit }]">
          <!-- Canvas — always in DOM so ref is stable; hidden during load -->
          <canvas
            ref="canvasRef"
            :class="['pdf-canvas', { hidden: pdfLoading || pdfError }]"
          />
        </div>

        <!-- Permanent bottom bar: page nav | zoom controls | download -->
        <div v-if="!pdfLoading && !pdfError && totalPages > 0" class="pdf-bar">
          <!-- Page navigation -->
          <button
            class="pdf-nav-btn"
            :disabled="currentPage <= 1"
            data-testid="pdf-prev"
            title="Předchozí strana"
            @click="currentPage--"
          >
            <ChevronLeftIcon :size="ICON_SIZE_SM - 2" />
          </button>
          <span class="pdf-page-info">{{ currentPage }} / {{ totalPages }}</span>
          <button
            class="pdf-nav-btn"
            :disabled="currentPage >= totalPages"
            data-testid="pdf-next"
            title="Další strana"
            @click="currentPage++"
          >
            <ChevronRightIcon :size="ICON_SIZE_SM - 2" />
          </button>

          <!-- Separator -->
          <span class="pdf-sep" />

          <!-- Zoom controls -->
          <button
            class="pdf-nav-btn"
            :disabled="zoom !== 'fit' && (zoom as number) <= ZOOM_MIN"
            data-testid="pdf-zoom-out"
            title="Oddálit"
            @click="zoomOut"
          >
            <ZoomOutIcon :size="ICON_SIZE_SM - 2" />
          </button>
          <span class="pdf-zoom-label" data-testid="pdf-zoom-label">{{ displayZoom }}</span>
          <button
            class="pdf-nav-btn"
            :disabled="zoom !== 'fit' && (zoom as number) >= ZOOM_MAX"
            data-testid="pdf-zoom-in"
            title="Přiblížit"
            @click="zoomIn"
          >
            <ZoomInIcon :size="ICON_SIZE_SM - 2" />
          </button>
          <button
            :class="['pdf-nav-btn', { active: isFit }]"
            data-testid="pdf-fit"
            title="Přizpůsobit panelu"
            @click="fitPage"
          >
            <ScanIcon :size="ICON_SIZE_SM - 2" />
          </button>

          <!-- Fill + download -->
          <span class="pdf-fill" />
          <a
            v-if="downloadUrl"
            :href="downloadUrl"
            target="_blank"
            rel="noopener"
            class="pdf-dl"
            title="Stáhnout soubor"
            data-testid="pdf-download"
          >
            <DownloadIcon :size="11" />
          </a>
        </div>
      </div>

      <!-- Non-PDF: info card + download -->
      <div v-else-if="selectedFile" class="mod-placeholder">
        <div class="mod-dot" />
        <div class="file-info-name">{{ selectedFile.original_filename }}</div>
        <div class="file-info-meta">
          {{ selectedFile.file_type.toUpperCase() }} · {{ formatBytes(selectedFile.file_size) }}
        </div>
        <a
          :href="`/api/files/${selectedFile.id}/download`"
          class="dl-link"
          target="_blank"
          :data-testid="`file-download-${selectedFile.id}`"
        >
          Stáhnout soubor
        </a>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wdrw {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  transition: opacity 0.15s;
}
.wdrw.refetching { opacity: 0.4; }

/* ─── Placeholder ─── */
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

/* ─── File selector ─── */
.file-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  border-bottom: 1px solid var(--b1);
  max-height: 110px;
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
.file-type { font-size: var(--fss); font-weight: 600; padding: 1px 4px; border-radius: var(--rs); background: var(--b2); color: var(--t3); flex-shrink: 0; }
.file-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-size { font-size: var(--fsm); color: var(--t4); flex-shrink: 0; }

/* ─── PDF canvas container ─── */
.pdf-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Canvas area — fills remaining space */
.pdf-canvas-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: var(--ground);
}

/* When zoomed in, allow scrolling */
.pdf-canvas-wrap.scrollable {
  overflow: auto;
  align-items: flex-start;
  justify-content: flex-start;
}

.pdf-canvas {
  display: block;
  /* Crisp edges for technical drawings */
  image-rendering: crisp-edges;
  image-rendering: -webkit-optimize-contrast;
}
.pdf-canvas.hidden { visibility: hidden; }

/* ─── Permanent bottom bar ─── */
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

.pdf-sep {
  width: 1px;
  height: 12px;
  background: var(--b2);
  margin: 0 3px;
  flex-shrink: 0;
}

.pdf-fill { flex: 1; }

.pdf-nav-btn {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: var(--t3);
  cursor: pointer;
  border-radius: var(--rs);
  transition: color 0.08s, background 0.08s;
  flex-shrink: 0;
}
.pdf-nav-btn:hover:not(:disabled) { color: var(--t1); background: var(--b2); }
.pdf-nav-btn:disabled { opacity: 0.3; cursor: default; }
.pdf-nav-btn.active { color: var(--t1); background: var(--b2); }
.pdf-nav-btn:focus-visible { outline: 2px solid rgba(255,255,255,0.5); }

.pdf-page-info {
  font-size: var(--fsm);
  color: var(--t3);
  padding: 0 3px;
 
  white-space: nowrap;
}

.pdf-zoom-label {
  font-size: var(--fsm);
  color: var(--t3);
  padding: 0 3px;
 
  white-space: nowrap;
  min-width: 34px;
  text-align: center;
}

.pdf-dl {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--rs);
  border: 1px solid var(--b2);
  color: var(--t3);
  text-decoration: none;
  transition: color 0.1s, border-color 0.1s, background 0.1s;
  flex-shrink: 0;
}
.pdf-dl:hover { color: var(--t1); border-color: var(--b3); background: var(--b1); }
.pdf-dl:focus-visible { outline: 2px solid rgba(255,255,255,0.5); }

/* ─── Non-PDF fallback ─── */
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
