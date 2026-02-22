<script setup lang="ts">
/**
 * File Manager Module - Split-pane coordinator
 *
 * LEFT: FileListPanel (320px resizable)
 * RIGHT: FilePreviewPanel
 *
 * @see docs/ADR/044-file-manager.md
 */

import { ref, computed, onMounted } from 'vue'
import { useFilesStore } from '@/stores/files'
import type { FileWithLinks } from '@/types/file'

import FileListPanel from './FileListPanel.vue'
import FilePreviewPanel from './FilePreviewPanel.vue'

const filesStore = useFilesStore()
const selectedFile = computed(() => filesStore.selectedFile)

// Panel size state
const panelSize = ref(320)
const isDragging = ref(false)

async function handleSelectFile(file: FileWithLinks) {
  await filesStore.selectFile(file.id)
}

function handleFileUpdated() {
  filesStore.fetchFiles()
  if (selectedFile.value) {
    filesStore.selectFile(selectedFile.value.id)
  }
}

function handleFileDeleted() {
  filesStore.fetchFiles()
}

// Resize handler
function startResize(event: MouseEvent) {
  event.preventDefault()
  isDragging.value = true

  const startPos = event.clientX
  const startSize = panelSize.value

  const handleMove = (e: MouseEvent) => {
    const delta = e.clientX - startPos
    const newSize = Math.max(280, Math.min(600, startSize + delta))
    panelSize.value = newSize
  }

  const handleUp = () => {
    isDragging.value = false
    localStorage.setItem('fileManagerPanelSize', String(panelSize.value))
    document.removeEventListener('mousemove', handleMove)
    document.removeEventListener('mouseup', handleUp)
  }

  document.addEventListener('mousemove', handleMove)
  document.addEventListener('mouseup', handleUp)
}

const panelStyle = computed(() => ({
  width: `${panelSize.value}px`
}))

onMounted(() => {
  // Load saved panel size
  const stored = localStorage.getItem('fileManagerPanelSize')
  if (stored) {
    const size = parseInt(stored, 10)
    if (!isNaN(size) && size >= 280 && size <= 600) {
      panelSize.value = size
    }
  }

  if (!filesStore.loaded) {
    filesStore.fetchFiles()
  }
})
</script>

<template>
  <div class="file-manager-module">
    <!-- LEFT PANEL: File List (resizable) -->
    <div class="left-panel" :style="panelStyle">
      <FileListPanel
        :selected-file="selectedFile"
        @select-file="handleSelectFile"
        @file-updated="handleFileUpdated"
      />
    </div>

    <!-- RESIZE HANDLE -->
    <div
      class="resize-handle"
      :class="{ dragging: isDragging }"
      @mousedown="startResize"
    ></div>

    <!-- RIGHT PANEL: Preview -->
    <div class="right-panel">
      <FilePreviewPanel
        :file="selectedFile"
        @updated="handleFileUpdated"
        @deleted="handleFileDeleted"
      />
    </div>
  </div>
</template>

<style scoped>
.file-manager-module {
  display: flex;
  gap: 0;
  height: 100%;
  overflow: hidden;
}

.left-panel,
.right-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.left-panel {
  flex-shrink: 0;
  padding: var(--pad);
}

.right-panel {
  flex: 1;
  overflow: hidden;
}

.resize-handle {
  flex-shrink: 0;
  width: 4px;
  background: var(--b2);
  transition: background 100ms;
  cursor: col-resize;
  position: relative;
  z-index: 10;
}

.resize-handle:hover,
.resize-handle.dragging {
  background: var(--red);
}
</style>
