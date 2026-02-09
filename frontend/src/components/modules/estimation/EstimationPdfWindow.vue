<script setup lang="ts">
/**
 * EstimationPdfWindow - Simple PDF viewer for estimation drawings
 *
 * Displays PDF from direct URL passed via window title
 * Format: "Výkres: filename.step|/uploads/drawings/file.pdf"
 */

import { ref, computed, onMounted } from 'vue'
import { FileText, AlertTriangle, Download } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  windowTitle?: string
}

const props = withDefaults(defineProps<Props>(), {
  windowTitle: undefined
})

const loadError = ref(false)

// Extract PDF URL from window title (format: "Výkres: filename|url")
const pdfUrl = computed(() => {
  if (!props.windowTitle) return ''
  const parts = props.windowTitle.split('|')
  return parts.length > 1 ? parts[1] : ''
})

const displayFilename = computed(() => {
  if (!props.windowTitle) return ''
  const parts = props.windowTitle.split('|')
  return (parts[0] ?? '').replace('Výkres: ', '')
})

// Verify PDF exists
async function verifyPdfExists(url: string) {
  if (!url) return
  try {
    const response = await fetch(url, { method: 'HEAD' })
    if (!response.ok) {
      loadError.value = true
    }
  } catch {
    loadError.value = true
  }
}

function handleDownload() {
  if (!pdfUrl.value) return
  window.open(pdfUrl.value, '_blank')
}

onMounted(() => {
  if (pdfUrl.value) {
    verifyPdfExists(pdfUrl.value)
  }
})
</script>

<template>
  <div class="estimation-pdf-window">
    <!-- No PDF URL -->
    <div v-if="!pdfUrl" class="empty-state">
      <FileText :size="64" class="empty-icon" />
      <p>Žádný výkres</p>
      <p class="empty-hint">PDF URL nebyla nalezena</p>
    </div>

    <!-- PDF load error -->
    <div v-else-if="loadError" class="empty-state">
      <AlertTriangle :size="64" class="empty-icon error-icon" />
      <p>Soubor výkresu nenalezen</p>
      <p class="empty-hint">PDF soubor neexistuje na serveru</p>
    </div>

    <!-- PDF Viewer -->
    <template v-else>
      <!-- Toolbar -->
      <div class="drawing-toolbar">
        <div class="toolbar-info">
          <span class="drawing-label">{{ displayFilename || 'Výkres' }}</span>
        </div>
        <button class="btn-download" @click="handleDownload" title="Download PDF">
          <Download :size="ICON_SIZE.SMALL" />
          Download
        </button>
      </div>

      <!-- PDF iframe -->
      <div class="pdf-viewer">
        <iframe
          :key="pdfUrl"
          :src="pdfUrl"
          class="pdf-iframe"
          title="PDF Drawing Viewer"
        ></iframe>
      </div>
    </template>
  </div>
</template>

<style scoped>
.estimation-pdf-window {
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

.error-icon {
  color: #f43f5e;
  opacity: 0.7;
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
