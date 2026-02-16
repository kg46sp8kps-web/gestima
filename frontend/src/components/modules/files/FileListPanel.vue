<script setup lang="ts">
/**
 * File List Panel - Seznam souborů s filtry a vyhledáváním
 */

import { ref, computed, watch } from 'vue'
import { useFilesStore } from '@/stores/files'
import type { FileWithLinks } from '@/types/file'
import { Upload } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import FileItem from './FileItem.vue'

interface Props {
  selectedFile: FileWithLinks | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'select-file': [file: FileWithLinks]
  'file-updated': []
}>()

const filesStore = useFilesStore()
const searchQuery = ref('')
const fileTypeFilter = ref<string>('all')
const statusFilter = ref<string>('all')
const showOrphans = ref(false)

// Filtered files
const filteredFiles = computed(() => {
  let list = [...filesStore.files]

  // Search filter
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    list = list.filter(f =>
      f.original_filename.toLowerCase().includes(query) ||
      f.file_path.toLowerCase().includes(query)
    )
  }

  // File type filter
  if (fileTypeFilter.value !== 'all') {
    list = list.filter(f => f.file_type === fileTypeFilter.value)
  }

  // Status filter
  if (statusFilter.value !== 'all') {
    list = list.filter(f => f.status === statusFilter.value)
  }

  return list
})

// Handle file click
function handleFileClick(file: FileWithLinks) {
  emit('select-file', file)
}

// Handle file type filter change
async function handleFileTypeChange() {
  await filesStore.fetchFiles({
    ...filesStore.filters,
    file_type: fileTypeFilter.value === 'all' ? undefined : fileTypeFilter.value
  })
}

// Handle orphans toggle
watch(showOrphans, async (value) => {
  if (value) {
    await filesStore.fetchOrphans()
  } else {
    await filesStore.fetchFiles()
  }
})

// Handle file upload
async function handleFileUpload(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return

  const file = input.files[0]
  if (!file) return

  await filesStore.uploadFile(file, { directory: 'loose' })
  emit('file-updated')

  // Reset input
  input.value = ''
}
</script>

<template>
  <div class="file-list-panel">
    <!-- Header -->
    <div class="list-header">
      <h3>File Manager</h3>
    </div>

    <!-- Search -->
    <div class="search-row">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Hledat soubory..."
        class="search-input"
      />
    </div>

    <!-- Filters -->
    <div class="filters-row">
      <select v-model="fileTypeFilter" @change="handleFileTypeChange" class="filter-select">
        <option value="all">Všechny typy</option>
        <option value="pdf">PDF</option>
        <option value="step">STEP</option>
        <option value="nc">NC</option>
        <option value="xlsx">XLSX</option>
      </select>

      <label class="checkbox-label">
        <input v-model="showOrphans" type="checkbox" />
        Orphans
      </label>
    </div>

    <!-- File list -->
    <div class="file-list">
      <!-- Loading state -->
      <div v-if="filesStore.loading" class="loading-state">
        <div class="spinner"></div>
        <p>Načítám soubory...</p>
      </div>

      <!-- Empty state -->
      <div v-else-if="!filesStore.hasFiles" class="empty-state">
        <Upload :size="ICON_SIZE.HERO" class="empty-icon" />
        <p>Žádné soubory</p>
        <p class="hint">Nahrajte soubory pomocí drag & drop níže</p>
      </div>

      <!-- File items -->
      <FileItem
        v-else
        v-for="file in filteredFiles"
        :key="file.id"
        :file="file"
        :selected="selectedFile?.id === file.id"
        @click="handleFileClick"
      />
    </div>

    <!-- Upload zone -->
    <div class="upload-zone">
      <label for="file-upload" class="upload-label">
        <Upload :size="ICON_SIZE.STANDARD" />
        <span>Drop files here or click to upload</span>
      </label>
      <input
        id="file-upload"
        type="file"
        class="upload-input"
        @change="handleFileUpload"
        accept=".pdf,.step,.stp,.nc,.xlsx"
      />
    </div>
  </div>
</template>

<style scoped>
.file-list-panel { display: flex; flex-direction: column; gap: var(--space-3); height: 100%; overflow: hidden; }
.list-header { flex-shrink: 0; }
.list-header h3 { margin: 0; font-size: var(--text-lg); font-weight: var(--font-semibold); color: var(--text-primary); }
.search-row { flex-shrink: 0; }
.search-input { width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--border-default); border-radius: var(--radius-md); font-size: var(--text-sm); background: var(--bg-input); color: var(--text-body); }
.search-input:focus { outline: none; background: var(--focus-bg); border-color: var(--focus-ring); box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1); }
.filters-row { display: flex; gap: var(--space-2); align-items: center; flex-shrink: 0; }
.filter-select { flex: 1; padding: var(--space-2) var(--space-3); border: 1px solid var(--border-default); border-radius: var(--radius-md); font-size: var(--text-sm); background: var(--bg-input); color: var(--text-body); }
.checkbox-label { display: flex; align-items: center; gap: var(--space-1); font-size: var(--text-sm); color: var(--text-secondary); cursor: pointer; white-space: nowrap; }
.checkbox-label input[type="checkbox"] { cursor: pointer; }
.file-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: var(--space-2); }
.loading-state, .empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: var(--space-8); text-align: center; color: var(--text-secondary); }
.spinner { width: 32px; height: 32px; border: 2px solid var(--border-default); border-top-color: var(--brand); border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: var(--space-3); }
@keyframes spin { to { transform: rotate(360deg); } }
.empty-icon { margin-bottom: var(--space-3); opacity: 0.5; }
.hint { font-size: var(--text-xs); color: var(--text-tertiary); margin-top: var(--space-1); }
.upload-zone { flex-shrink: 0; margin-top: auto; padding-top: var(--space-3); border-top: 1px solid var(--border-default); }
.upload-label { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); padding: var(--space-4); background: var(--bg-surface); border: 2px dashed var(--border-default); border-radius: var(--radius-md); cursor: pointer; transition: all var(--duration-fast); font-size: var(--text-sm); color: var(--text-secondary); text-align: center; }
.upload-label:hover { border-color: var(--border-strong); background: var(--bg-raised); }
.upload-input { display: none; }
</style>
