<script setup lang="ts">
/**
 * DrawingsManagementModal - Manage multiple PDF drawings for a part
 * Features: List, upload (drag & drop, multiple), set primary, delete, open in floating window
 */
import { ref, computed, watch } from 'vue'
import { FileText, Upload, Trash2, Star } from 'lucide-vue-next'
import { drawingsApi } from '@/api/drawings'
import { useUiStore } from '@/stores/ui'
import type { Drawing } from '@/types/drawing'
import Modal from '@/components/ui/Modal.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import Spinner from '@/components/ui/Spinner.vue'

interface Props {
  modelValue: boolean
  partNumber: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'refresh': []
  'open-drawing': [drawingId: number]
}>()

const uiStore = useUiStore()

// State
const drawings = ref<Drawing[]>([])
const loading = ref(false)
const showDeleteConfirm = ref(false)
const deleteTarget = ref<Drawing | null>(null)
const uploadingDrawing = ref(false)
const isDragging = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

// Computed
const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const sortedDrawings = computed(() => {
  return [...drawings.value].sort((a, b) => {
    if (a.is_primary) return -1
    if (b.is_primary) return 1
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })
})

// Load drawings when modal opens
watch(isOpen, async (open) => {
  if (open) await loadDrawings()
})

async function loadDrawings() {
  loading.value = true
  try {
    const response = await drawingsApi.listDrawings(props.partNumber)
    drawings.value = response.drawings
  } catch (error: any) {
    uiStore.showError(`Nepodařilo se načíst výkresy: ${error.message}`)
  } finally {
    loading.value = false
  }
}

// Drag & drop handlers
function onDragEnter(e: DragEvent) {
  e.preventDefault()
  isDragging.value = true
}

function onDragOver(e: DragEvent) {
  e.preventDefault()
}

function onDragLeave(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false

  const files = Array.from(e.dataTransfer?.files || [])
  handleFilesUpload(files)
}

function onFileInputChange(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  handleFilesUpload(files)
  input.value = '' // Reset for re-upload
}

function openFilePicker() {
  fileInputRef.value?.click()
}

async function handleFilesUpload(files: File[]) {
  if (files.length === 0) return

  // Filter only PDFs
  const pdfFiles = files.filter(f => f.type === 'application/pdf')
  if (pdfFiles.length === 0) {
    uiStore.showError('Pouze PDF soubory jsou podporovány')
    return
  }

  uploadingDrawing.value = true
  let successCount = 0
  let errorCount = 0

  try {
    // Upload all files in parallel
    const uploadPromises = pdfFiles.map(async (file) => {
      try {
        await drawingsApi.uploadDrawing(
          props.partNumber,
          file,
          'A' // Default revision
        )
        successCount++
      } catch (error: any) {
        errorCount++
        console.error(`Failed to upload ${file.name}:`, error)
      }
    })

    await Promise.all(uploadPromises)

    // Show results
    if (successCount > 0) {
      uiStore.showSuccess(`${successCount} výkresů nahráno`)
    }
    if (errorCount > 0) {
      uiStore.showError(`${errorCount} souborů se nepodařilo nahrát`)
    }

    await loadDrawings()
    emit('refresh')
  } finally {
    uploadingDrawing.value = false
  }
}

async function setPrimary(drawing: Drawing) {
  try {
    await drawingsApi.setPrimaryDrawing(props.partNumber, drawing.id)
    uiStore.showSuccess(`Výkres ${drawing.filename} nastaven jako primární`)
    await loadDrawings()
    emit('refresh')
  } catch (error: any) {
    uiStore.showError(`Nelze nastavit primární: ${error.message}`)
  }
}

function confirmDelete(drawing: Drawing) {
  deleteTarget.value = drawing
  showDeleteConfirm.value = true
}

async function handleDelete() {
  if (!deleteTarget.value) return
  try {
    await drawingsApi.deleteDrawingById(props.partNumber, deleteTarget.value.id)
    uiStore.showSuccess(`Výkres ${deleteTarget.value.filename} smazán`)
    showDeleteConfirm.value = false
    deleteTarget.value = null
    await loadDrawings()
    emit('refresh')
  } catch (error: any) {
    uiStore.showError(`Nepodařilo se smazat: ${error.message}`)
  }
}

function openDrawing(drawing: Drawing) {
  emit('open-drawing', drawing.id)
}
</script>

<template>
  <Modal v-model="isOpen" :title="`Správa výkresů - ${partNumber}`" size="xl">
    <!-- Drag & Drop Upload Zone -->
    <div
      class="upload-zone"
      :class="{ dragging: isDragging, uploading: uploadingDrawing }"
      @dragenter="onDragEnter"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
      @click="openFilePicker"
    >
      <input
        ref="fileInputRef"
        type="file"
        accept="application/pdf"
        multiple
        style="display: none"
        @change="onFileInputChange"
      />

      <Upload :size="32" :stroke-width="1.5" />
      <p class="upload-label">
        {{ uploadingDrawing ? 'Nahrávám...' : 'Přetáhněte PDF výkresy sem nebo klikněte pro výběr' }}
      </p>
      <p class="upload-hint">Podporuje více souborů najednou</p>
    </div>

    <!-- Count -->
    <div class="header">
      <span class="count">{{ drawings.length }} výkresů</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="state">
      <Spinner />
      <p>Načítám výkresy...</p>
    </div>

    <!-- Empty -->
    <div v-else-if="drawings.length === 0" class="state">
      <FileText :size="48" :stroke-width="1.5" />
      <p>Žádné výkresy. Nahrajte první výkres.</p>
    </div>

    <!-- Grid -->
    <div v-else class="grid">
      <div
        v-for="drawing in sortedDrawings"
        :key="drawing.id"
        class="card"
        :class="{ primary: drawing.is_primary }"
      >
        <!-- Thumbnail -->
        <div class="thumb" @click="openDrawing(drawing)">
          <FileText :size="32" />
        </div>

        <!-- Info -->
        <div class="info">
          <p class="name">{{ drawing.filename }}</p>
          <p class="rev">Rev {{ drawing.revision }}</p>
        </div>

        <!-- Primary badge -->
        <span v-if="drawing.is_primary" class="badge">
          <Star :size="12" :fill="'currentColor'" />
          Primary
        </span>

        <!-- Actions -->
        <div class="actions">
          <button
            v-if="!drawing.is_primary"
            class="btn-icon"
            @click="setPrimary(drawing)"
            title="Nastavit jako primární"
          >
            <Star :size="16" />
          </button>
          <button
            class="btn-icon btn-danger"
            @click="confirmDelete(drawing)"
            title="Smazat"
          >
            <Trash2 :size="16" />
          </button>
        </div>
      </div>
    </div>

    <!-- Delete confirm -->
    <ConfirmDialog
      v-model="showDeleteConfirm"
      title="Smazat výkres?"
      :message="`Opravdu smazat ${deleteTarget?.filename}?`"
      @confirm="handleDelete"
    />
  </Modal>
</template>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border-default);
}

.count {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-8);
  text-align: center;
  color: var(--text-secondary);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--space-3);
}

.card {
  position: relative;
  padding: var(--space-3);
  background: var(--bg-surface);
  border: 2px solid var(--border-default);
  border-radius: var(--radius-md);
  transition: var(--transition-fast);
}

.card:hover {
  border-color: var(--color-primary);
}

.card.primary {
  border-color: var(--color-success);
  background: rgba(5, 150, 105, 0.05);
}

.thumb {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100px;
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-fast);
  color: var(--text-secondary);
}

.thumb:hover {
  background: var(--state-hover);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.info {
  margin-top: var(--space-2);
}

.name {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rev {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.badge {
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px var(--space-2);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-success);
  background: var(--bg-base);
  border: 1px solid var(--color-success);
  border-radius: var(--radius-sm);
}

.actions {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.btn-icon {
  padding: var(--space-2);
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-fast);
  color: var(--text-secondary);
}

.btn-icon:hover {
  background: var(--state-hover);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.btn-icon.btn-danger:hover {
  border-color: var(--color-danger);
  color: var(--color-danger);
}

@media (max-width: 768px) {
  .grid {
    grid-template-columns: 1fr;
  }
}

/* Upload Zone */
.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-6);
  margin-bottom: var(--space-4);
  border: 2px dashed var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  cursor: pointer;
  transition: var(--transition-fast);
  color: var(--text-secondary);
}

.upload-zone:hover {
  border-color: var(--color-primary);
  background: var(--bg-raised);
  color: var(--color-primary);
}

.upload-zone.dragging {
  border-color: var(--color-success);
  background: rgba(5, 150, 105, 0.1);
  transform: scale(1.02);
}

.upload-zone.uploading {
  pointer-events: none;
  opacity: 0.6;
}

.upload-label {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  text-align: center;
}

.upload-hint {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--text-secondary);
}
</style>
