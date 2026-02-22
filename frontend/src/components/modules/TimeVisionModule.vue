<script setup lang="ts">
/**
 * TimeVision Module - AI Machining Time Estimation
 * 3-panel layout: Drawing list | PDF + TimeRibbon | Model-specific panel
 */
import { ref, watch, onMounted, nextTick } from 'vue'
import { useTimeVisionStore } from '@/stores/timeVision'
import { getDrawingPdfUrl } from '@/api/time-vision'
import TimeVisionDrawingListPanel from './timevision/TimeVisionDrawingListPanel.vue'
import TimeVisionPdfPreview from './timevision/TimeVisionPdfPreview.vue'
import TimeVisionTimeRibbon from './timevision/TimeVisionTimeRibbon.vue'
import TimeVisionTimePanel from './timevision/TimeVisionTimePanel.vue'
import TimeVisionFeaturesPanel from './timevision/TimeVisionFeaturesPanel.vue'

const store = useTimeVisionStore()

const leftWidth = ref(300)
const rightWidth = ref(420)
const isDraggingLeft = ref(false)
const isDraggingRight = ref(false)
const selectedFilename = ref<string | null>(null)
const activeModel = ref<'time_v1' | 'features_v2'>('time_v1')

const pdfUrl = ref<string | null>(null)

watch(selectedFilename, async (newFilename) => {
  await nextTick()
  store.openaiEstimation = null
  store.openaiError = null
  store.featuresEstimation = null
  store.featuresError = null

  // ADR-044: prefer file_id when available
  const drawing = store.drawings.find(d => d.filename === newFilename)
  pdfUrl.value = newFilename ? getDrawingPdfUrl(newFilename, drawing?.file_id ?? null) : null

  if (newFilename) {
    await Promise.all([
      store.loadOpenAIEstimation(newFilename),
      store.loadFeaturesEstimation(newFilename),
    ])
  }
}, { immediate: true })

function handleSelectDrawing(filename: string) {
  selectedFilename.value = filename
}

async function handleProcess(filename: string) {
  const drawing = store.drawings.find(d => d.filename === filename)
  await store.processFileOpenAI(filename, drawing?.file_id ?? null)
}

async function handleProcessAll() {
  const unestimated = store.drawings.filter(d => !d.has_openai_estimation)
  if (unestimated.length === 0) return
  for (const d of unestimated) {
    try {
      await store.processFileOpenAI(d.filename, d.file_id ?? null)
    } catch { /* continue */ }
  }
}

function startResizeLeft(event: MouseEvent) {
  event.preventDefault()
  isDraggingLeft.value = true
  const startX = event.clientX
  const startW = leftWidth.value
  function onMove(e: MouseEvent) {
    leftWidth.value = Math.max(220, Math.min(500, startW + e.clientX - startX))
  }
  function onUp() {
    isDraggingLeft.value = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    try { localStorage.setItem('tv_left_w', String(leftWidth.value)) } catch {}
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

function startResizeRight(event: MouseEvent) {
  event.preventDefault()
  isDraggingRight.value = true
  const startX = event.clientX
  const startW = rightWidth.value
  function onMove(e: MouseEvent) {
    rightWidth.value = Math.max(300, Math.min(600, startW - (e.clientX - startX)))
  }
  function onUp() {
    isDraggingRight.value = false
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    try { localStorage.setItem('tv_right_w', String(rightWidth.value)) } catch {}
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

onMounted(() => {
  store.loadDrawings()
  store.loadEstimations()
  store.loadModelInfo()
  try {
    const savedL = localStorage.getItem('tv_left_w')
    if (savedL) leftWidth.value = Math.max(220, Math.min(500, Number(savedL)))
    const savedR = localStorage.getItem('tv_right_w')
    if (savedR) rightWidth.value = Math.max(300, Math.min(600, Number(savedR)))
  } catch {}
})
</script>

<template>
  <div class="tv-module">
    <div class="tv-left" :style="{ width: leftWidth + 'px' }">
      <TimeVisionDrawingListPanel
        :selectedFilename="selectedFilename"
        @select="handleSelectDrawing"
        @process="handleProcess"
        @process-all="handleProcessAll"
      />
    </div>
    <div class="tv-resize" :class="{ active: isDraggingLeft }" @mousedown="startResizeLeft" />

    <div class="tv-middle">
      <template v-if="selectedFilename">
        <div class="model-header">
          <button
            :class="{ active: activeModel === 'time_v1' }"
            @click="activeModel = 'time_v1'"
          >FT v1 (časy)</button>
          <button
            :class="{ active: activeModel === 'features_v2' }"
            @click="activeModel = 'features_v2'"
          >FT v2 (features)</button>
        </div>
        <div class="tv-pdf-container">
          <TimeVisionPdfPreview :url="pdfUrl" />
        </div>
        <TimeVisionTimeRibbon
          :openai-estimation="store.openaiEstimation"
          :features-estimation="store.featuresEstimation"
          :active-model="activeModel"
          @switch-model="activeModel = $event"
        />
      </template>
      <div v-else class="tv-empty">
        <p>Vyberte výkres ze seznamu</p>
      </div>
    </div>

    <template v-if="selectedFilename">
      <div class="tv-resize" :class="{ active: isDraggingRight }" @mousedown="startResizeRight" />
      <div class="tv-right" :style="{ width: rightWidth + 'px' }">
        <TimeVisionTimePanel
          v-if="activeModel === 'time_v1'"
          :filename="selectedFilename"
        />
        <TimeVisionFeaturesPanel
          v-if="activeModel === 'features_v2'"
          :filename="selectedFilename"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.tv-module {
  display: flex;
  height: 100%;
  overflow: hidden;
}
.tv-left {
  flex-shrink: 0;
  overflow-y: auto;
  border-right: 1px solid var(--b2);
}
.tv-resize {
  width: 4px;
  cursor: col-resize;
  background: transparent;
  transition: background 0.15s;
  flex-shrink: 0;
}
.tv-resize:hover, .tv-resize.active {
  background: var(--red);
}
.tv-middle {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}
.tv-right {
  flex-shrink: 0;
  overflow-y: auto;
  border-left: 1px solid var(--b2);
}
.tv-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--t3);
}
.model-header {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--b2);
  background: var(--surface);
  flex-shrink: 0;
}
.model-header button {
  flex: 1;
  padding: 6px var(--pad);
  border: none;
  background: none;
  cursor: pointer;
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t3);
  border-bottom: 2px solid transparent;
  transition: all 0.15s;
}
.model-header button.active {
  color: var(--red);
  border-bottom-color: var(--red);
  font-weight: 600;
}
.tv-pdf-container {
  flex: 1;
  min-height: 200px;
  overflow: hidden;
}
</style>
