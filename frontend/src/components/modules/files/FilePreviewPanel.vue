<script setup lang="ts">
/**
 * File Preview Panel - Náhled souboru, metadata, vazby, akce
 */

import { computed } from 'vue'
import { useFilesStore } from '@/stores/files'
import type { FileWithLinks, FileLink } from '@/types/file'
import { Download, Trash2, FileText } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import { confirm } from '@/composables/useDialog'
import { filesApi } from '@/api/files'
import FileMetadata from './FileMetadata.vue'
import FileLinksList from './FileLinksList.vue'

interface Props {
  file: FileWithLinks | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  updated: []
  deleted: []
}>()

const filesStore = useFilesStore()

// Preview URL (no auth — for iframe/pdf.js)
// #view=Fit tells the browser PDF viewer to fit the whole page in the viewport
const previewUrl = computed(() => {
  if (!props.file) return null
  if (props.file.file_type === 'pdf') {
    return `${filesApi.getPreviewUrl(props.file.id)}#view=Fit`
  }
  return null
})

// Download URL (with auth — for explicit download action)
const downloadUrl = computed(() => {
  if (!props.file) return null
  return filesApi.getDownloadUrl(props.file.id)
})

// Handle download
function handleDownload() {
  if (downloadUrl.value) {
    window.open(downloadUrl.value, '_blank')
  }
}

// Handle delete
async function handleDelete() {
  if (!props.file) return

  const confirmed = await confirm({
    title: 'Smazat soubor?',
    message: `Opravdu chcete smazat soubor "${props.file.original_filename}"?\n\nTato akce je nevratná!`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  await filesStore.deleteFile(props.file.id)
  emit('deleted')
}

// Handle unlink
async function handleUnlink(link: FileLink) {
  if (!props.file) return

  const confirmed = await confirm({
    title: 'Odpojit vazbu?',
    message: `Odpojit soubor od ${link.entity_type} #${link.entity_id}?`,
    type: 'warning',
    confirmText: 'Odpojit',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  await filesStore.unlinkFile(props.file.id, link.entity_type, link.entity_id)
  emit('updated')
}

// Check if file is PDF
const isPdf = computed(() => props.file?.file_type === 'pdf')
</script>

<template>
  <div class="file-preview-panel">
    <!-- Empty state -->
    <div v-if="!file" class="empty-state">
      <FileText :size="ICON_SIZE.HERO" class="empty-icon" />
      <p>Žádný soubor není vybrán</p>
      <p class="hint">Vyberte soubor ze seznamu vlevo</p>
    </div>

    <!-- File preview -->
    <div v-else class="preview-content">
      <!-- PDF Preview -->
      <div v-if="isPdf" class="preview-frame">
        <iframe
          :src="previewUrl || undefined"
          class="pdf-iframe"
          title="PDF Preview"
        ></iframe>
      </div>

      <!-- Non-PDF (just metadata) -->
      <div v-else class="preview-placeholder">
        <FileText :size="ICON_SIZE.HERO" class="placeholder-icon" />
        <p class="file-type-label">{{ file.file_type.toUpperCase() }} soubor</p>
        <p class="hint">Preview není k dispozici</p>
      </div>

      <!-- Metadata Section -->
      <FileMetadata :file="file" />

      <!-- Links Section -->
      <FileLinksList :links="file.links" @unlink="handleUnlink" />

      <!-- Actions Section -->
      <div class="actions-section">
        <button class="btn btn-primary" @click="handleDownload">
          <Download :size="ICON_SIZE.STANDARD" />
          <span>Download</span>
        </button>
        <button class="btn btn-secondary" @click="handleDelete">
          <Trash2 :size="ICON_SIZE.STANDARD" />
          <span>Delete</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.file-preview-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: var(--space-8);
  text-align: center;
  color: var(--text-secondary);
}

.empty-icon {
  margin-bottom: var(--space-4);
  opacity: 0.5;
}

.hint {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin-top: var(--space-1);
}

.preview-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.preview-frame {
  flex: 1;
  min-height: 0;
  background: var(--bg-base);
  border-bottom: 1px solid var(--border-default);
  overflow: hidden;
}

.pdf-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.preview-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
}

.placeholder-icon {
  margin-bottom: var(--space-3);
  opacity: 0.3;
  color: var(--text-tertiary);
}

.file-type-label {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-1);
}

.actions-section {
  flex-shrink: 0;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  gap: var(--space-3);
  margin-top: auto;
}

.btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all var(--duration-fast);
  background: transparent;
}

.btn-primary {
  color: var(--text-primary);
  border-color: var(--border-default);
}

.btn-primary:hover {
  border-color: var(--color-primary);
  background: var(--bg-raised);
}

.btn-secondary {
  color: var(--color-danger);
  border-color: var(--color-danger);
}

.btn-secondary:hover {
  background: rgba(244, 63, 94, 0.1);
}

</style>
