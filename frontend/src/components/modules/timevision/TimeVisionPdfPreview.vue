<script setup lang="ts">
/**
 * TimeVision - PDF Preview with controls
 * Canvas render via pdf.js, auto-resize on ribbon drag, zoom/page controls.
 */
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ZoomIn, ZoomOut, Maximize, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import * as pdfjsLib from 'pdfjs-dist'
import type { PDFDocumentProxy, PDFPageProxy } from 'pdfjs-dist'
import { ICON_SIZE } from '@/config/design'

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()

interface Props {
  url: string | null
}
const props = defineProps<Props>()

const containerRef = ref<HTMLElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

// PDF state (cached)
let pdfDoc: PDFDocumentProxy | null = null
let loadedUrl: string | null = null
const currentPage = ref(1)
const totalPages = ref(1)

// Zoom state
type ZoomMode = 'fit' | 'manual'
const zoomMode = ref<ZoomMode>('fit')
const manualScale = ref(1.0)

let resizeObserver: ResizeObserver | null = null
let renderTimer: ReturnType<typeof setTimeout> | null = null
let renderGeneration = 0  // to cancel stale renders

async function loadPdf() {
  if (!props.url) return
  if (loadedUrl === props.url && pdfDoc) return // already loaded

  loading.value = true
  error.value = null

  try {
    if (pdfDoc) {
      pdfDoc.destroy()
      pdfDoc = null
    }
    const doc = await pdfjsLib.getDocument(props.url).promise
    pdfDoc = doc
    loadedUrl = props.url
    totalPages.value = doc.numPages
    currentPage.value = 1
    zoomMode.value = 'fit'
  } catch (e: unknown) {
    error.value = (e as Error).message ?? 'PDF load failed'
    pdfDoc = null
    loadedUrl = null
  } finally {
    loading.value = false
  }
}

async function renderPage() {
  if (!pdfDoc || !canvasRef.value || !containerRef.value) return

  const gen = ++renderGeneration

  try {
    const page: PDFPageProxy = await pdfDoc.getPage(currentPage.value)

    // Check if this render is still current
    if (gen !== renderGeneration) return

    const container = containerRef.value
    if (!container) return

    // Available space (account for toolbar height)
    const containerW = container.clientWidth
    const containerH = container.clientHeight
    if (containerW <= 0 || containerH <= 0) return

    const viewport0 = page.getViewport({ scale: 1 })

    let scale: number
    if (zoomMode.value === 'fit') {
      scale = Math.min(containerW / viewport0.width, containerH / viewport0.height)
      manualScale.value = scale
    } else {
      scale = manualScale.value
    }

    const viewport = page.getViewport({ scale })

    const canvas = canvasRef.value
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = Math.floor(viewport.width * dpr)
    canvas.height = Math.floor(viewport.height * dpr)
    canvas.style.width = `${Math.floor(viewport.width)}px`
    canvas.style.height = `${Math.floor(viewport.height)}px`
    ctx.scale(dpr, dpr)

    // Check again before rendering
    if (gen !== renderGeneration) return

    await page.render({ canvas, canvasContext: ctx, viewport }).promise
  } catch (e: unknown) {
    if (gen === renderGeneration) {
      const msg = (e as Error).message ?? ''
      if (!msg.includes('destroy') && !msg.includes('cancelled')) {
        error.value = msg
      }
    }
  }
}

// Debounced render for resize
function debouncedRender() {
  if (renderTimer) clearTimeout(renderTimer)
  renderTimer = setTimeout(() => renderPage(), 80)
}

// Controls
function zoomIn() {
  zoomMode.value = 'manual'
  manualScale.value = Math.min(manualScale.value * 1.25, 5)
  renderPage()
}

function zoomOut() {
  zoomMode.value = 'manual'
  manualScale.value = Math.max(manualScale.value / 1.25, 0.2)
  renderPage()
}

function fitToPage() {
  zoomMode.value = 'fit'
  renderPage()
}

function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--
    renderPage()
  }
}

function nextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    renderPage()
  }
}

const zoomPercent = ref('')
watch(manualScale, (s) => {
  zoomPercent.value = `${Math.round(s * 100)}%`
}, { immediate: true })

// URL change → load new PDF + render
watch(() => props.url, async (newUrl) => {
  if (!newUrl) {
    pdfDoc?.destroy()
    pdfDoc = null
    loadedUrl = null
    return
  }
  await loadPdf()
  await nextTick()
  await renderPage()
}, { immediate: false })

// Resize observer → re-render (no re-load!)
onMounted(async () => {
  await nextTick()

  if (containerRef.value) {
    resizeObserver = new ResizeObserver(() => {
      if (zoomMode.value === 'fit') {
        debouncedRender()
      }
    })
    resizeObserver.observe(containerRef.value)
  }

  if (props.url) {
    await loadPdf()
    await nextTick()
    await renderPage()
  }
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  if (renderTimer) clearTimeout(renderTimer)
  pdfDoc?.destroy()
  pdfDoc = null
  loadedUrl = null
})
</script>

<template>
  <div class="pdf-wrapper">
    <!-- Toolbar -->
    <div v-if="url && pdfDoc" class="pdf-toolbar">
      <div class="toolbar-group">
        <button class="tool-btn" title="Zoom out" @click="zoomOut">
          <ZoomOut :size="ICON_SIZE.SMALL" />
        </button>
        <span class="zoom-label">{{ zoomPercent }}</span>
        <button class="tool-btn" title="Zoom in" @click="zoomIn">
          <ZoomIn :size="ICON_SIZE.SMALL" />
        </button>
        <button
          class="tool-btn"
          :class="{ active: zoomMode === 'fit' }"
          title="Fit to page"
          @click="fitToPage"
        >
          <Maximize :size="ICON_SIZE.SMALL" />
        </button>
      </div>
      <div v-if="totalPages > 1" class="toolbar-group">
        <button class="tool-btn" :disabled="currentPage <= 1" @click="prevPage">
          <ChevronLeft :size="ICON_SIZE.SMALL" />
        </button>
        <span class="page-label">{{ currentPage }} / {{ totalPages }}</span>
        <button class="tool-btn" :disabled="currentPage >= totalPages" @click="nextPage">
          <ChevronRight :size="ICON_SIZE.SMALL" />
        </button>
      </div>
    </div>

    <!-- Canvas area -->
    <div ref="containerRef" class="pdf-container" :class="{ 'scroll-mode': zoomMode === 'manual' }">
      <canvas v-show="!error && pdfDoc" ref="canvasRef" class="pdf-canvas" />
      <div v-if="loading" class="pdf-loading">
        <span class="loading-dot" />
      </div>
      <div v-if="error" class="pdf-error">{{ error }}</div>
      <div v-if="!url" class="no-pdf">
        <p>Žádný výkres</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pdf-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Toolbar */
.pdf-toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  padding: var(--space-0\.5) var(--space-3);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
}
.toolbar-group {
  display: flex;
  align-items: center;
  gap: var(--space-0\.5);
}
.tool-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.1s;
}
.tool-btn:hover:not(:disabled) {
  background: var(--state-hover);
  color: var(--text-primary);
}
.tool-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.tool-btn.active {
  background: var(--brand-subtle, rgba(153, 27, 27, 0.1));
  border: 1px solid var(--color-brand, #991b1b);
  color: var(--color-brand, #991b1b);
}
.zoom-label, .page-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  min-width: 40px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

/* Canvas container */
.pdf-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: var(--bg-subtle);
  position: relative;
}
.pdf-container.scroll-mode {
  overflow: auto;
  align-items: flex-start;
  justify-content: flex-start;
}
.pdf-canvas {
  display: block;
}
.pdf-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.loading-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: pulse 1s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}
.pdf-error {
  color: var(--color-danger);
  font-size: var(--text-xs);
  padding: var(--space-2);
}
.no-pdf {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
}
</style>
