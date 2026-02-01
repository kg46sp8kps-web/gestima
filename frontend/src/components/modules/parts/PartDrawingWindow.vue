<script setup lang="ts">
/**
 * PartDrawingWindow - Floating PDF viewer for part drawings
 *
 * Features:
 * - Full PDF viewer (iframe)
 * - Download button
 * - Title shows part number
 * - Context-aware (linked windows)
 *
 * Used in FloatingWindow with type 'part-drawing'
 */

import { ref, computed, watch, onMounted } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useWindowContextStore } from '@/stores/windowContext'
import type { Part } from '@/types/part'
import type { LinkingGroup } from '@/stores/windows'
import { drawingsApi } from '@/api/drawings'
import { FileText, AlertTriangle, Download } from 'lucide-vue-next'

interface Props {
  linkingGroup?: LinkingGroup
  windowTitle?: string // Window title (contains drawing ID if specific drawing)
}

const props = withDefaults(defineProps<Props>(), {
  linkingGroup: null,
  windowTitle: undefined
})

// Parse drawing ID and part number from window title
// Pattern: "Drawing #123 - PN001" where 123 is drawing_id, PN001 is part_number
// OR: "Drawing - PN001" for primary drawing
const drawingIdFromTitle = computed(() => {
  if (!props.windowTitle) return undefined
  const match = props.windowTitle.match(/Drawing #(\d+)/)
  return match && match[1] ? parseInt(match[1], 10) : undefined
})

const partNumberFromTitle = computed(() => {
  if (!props.windowTitle) return undefined
  // Extract part number after " - "
  const match = props.windowTitle.match(/ - (.+)$/)
  return match && match[1] ? match[1] : undefined
})

const partsStore = usePartsStore()
const contextStore = useWindowContextStore()

// State
const currentPart = ref<Part | null>(null)

// Computed: Get partId from window context
const contextPartId = computed(() => {
  if (!props.linkingGroup) return null

  switch (props.linkingGroup) {
    case 'red': return contextStore.redContext.partId
    case 'blue': return contextStore.blueContext.partId
    case 'green': return contextStore.greenContext.partId
    case 'yellow': return contextStore.yellowContext.partId
    default: return null
  }
})

const drawingUrl = computed(() => {
  if (!currentPart.value?.part_number) return ''
  // If specific drawing ID is provided (parsed from title), use it; otherwise use primary
  return drawingsApi.getDrawingUrl(currentPart.value.part_number, drawingIdFromTitle.value)
})

// Check if drawing exists:
// - If specific drawing ID from modal: assume it exists (show viewer)
// - If primary drawing: check if part has drawing_path
const hasDrawing = computed(() => {
  if (!currentPart.value) return false
  // Specific drawing from modal - always show (let iframe handle 404)
  if (drawingIdFromTitle.value) return true
  // Primary drawing - check if exists
  return !!currentPart.value.drawing_path
})

function handleDownload() {
  if (!drawingUrl.value) return
  // Open PDF in new tab (browser will show download dialog)
  window.open(drawingUrl.value, '_blank')
}

// Watch context changes and load part
watch(contextPartId, async (newPartId) => {
  if (newPartId) {
    // Fetch fresh parts to ensure drawing_path is synced
    await partsStore.fetchParts()
    const part = partsStore.parts.find(p => p.id === newPartId)
    if (part) {
      currentPart.value = part
    }
  }
}, { immediate: true })

// Watch part number from title (for standalone windows opened from modal)
watch(partNumberFromTitle, async (partNumber) => {
  if (partNumber) {
    await partsStore.fetchParts()
    const part = partsStore.parts.find(p => p.part_number === partNumber)
    if (part) {
      currentPart.value = part
    }
  }
}, { immediate: true })

// Load parts on mount
onMounted(async () => {
  await partsStore.fetchParts()

  // Priority 1: Load from title (standalone window from modal)
  if (partNumberFromTitle.value) {
    const part = partsStore.parts.find(p => p.part_number === partNumberFromTitle.value)
    if (part) {
      currentPart.value = part
      return
    }
  }

  // Priority 2: Load from context (linked window)
  if (contextPartId.value) {
    const part = partsStore.parts.find(p => p.id === contextPartId.value)
    if (part) {
      currentPart.value = part
    }
  }
})
</script>

<template>
  <div class="part-drawing-window">
    <!-- No part selected -->
    <div v-if="!currentPart" class="empty-state">
      <FileText :size="64" class="empty-icon" />
      <p>No part selected</p>
      <p class="empty-hint">Open from Part Main window</p>
    </div>

    <!-- No drawing available -->
    <div v-else-if="!hasDrawing" class="empty-state">
      <AlertTriangle :size="64" class="empty-icon" />
      <p>No drawing available</p>
      <p class="empty-hint">Part: {{ currentPart.article_number || currentPart.part_number }}</p>
    </div>

    <!-- Drawing viewer -->
    <template v-else>
      <!-- Toolbar -->
      <div class="drawing-toolbar">
        <div class="toolbar-info">
          <span class="part-badge">{{ currentPart.article_number || currentPart.part_number }}</span>
          <span class="drawing-label">{{ currentPart.drawing_path || 'Drawing' }}</span>
        </div>
        <button class="btn-download" @click="handleDownload" title="Download PDF">
          <Download :size="16" />
          Download
        </button>
      </div>

      <!-- PDF Viewer -->
      <div class="pdf-viewer">
        <iframe
          :key="drawingUrl"
          :src="drawingUrl"
          class="pdf-iframe"
          title="PDF Drawing Viewer"
        ></iframe>
      </div>
    </template>
  </div>
</template>

<style scoped>
.part-drawing-window {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-surface);
}

/* Toolbar */
.drawing-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  background: var(--bg-raised);
  border-bottom: 1px solid var(--border-default);
  gap: var(--space-3);
}

.toolbar-info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
}

.drawing-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.btn-download {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: white;
  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-fast);
  white-space: nowrap;
}

.btn-download:hover {
  background: var(--color-primary-hover);
}

/* PDF Viewer */
.pdf-viewer {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: var(--bg-deepest);
}

.pdf-iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: none;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  height: 100%;
  padding: var(--space-8);
  text-align: center;
  color: var(--text-secondary);
}

.empty-icon {
  opacity: 0.5;
  color: var(--text-secondary);
}

.empty-state p {
  margin: 0;
  font-size: var(--text-base);
  color: var(--text-body);
}

.empty-hint {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}
</style>
