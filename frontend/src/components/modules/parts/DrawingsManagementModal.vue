<script setup lang="ts">
/**
 * DrawingsManagementModal - Manage multiple PDF drawings for a part
 * Features: List, upload (drag & drop, multiple), set primary, delete, open in floating window
 */
import { ref, computed, watch } from 'vue'
import { FileText, Upload, Trash2, Star, Box, AlertTriangle } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import { drawingsApi } from '@/api/drawings'
import { useUiStore } from '@/stores/ui'
import { useDialog } from '@/composables/useDialog'
import type { Drawing } from '@/types/drawing'
import Modal from '@/components/ui/Modal.vue'
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
const { confirm } = useDialog()

// State
const drawings = ref<Drawing[]>([])
const loading = ref(false)
const uploadingDrawing = ref(false)
const isDragging = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const stepFileInputRef = ref<HTMLInputElement | null>(null)

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

const pdfDrawings = computed(() =>
  sortedDrawings.value.filter(d => d.file_type === 'pdf' || !d.file_type)
)

const stepDrawings = computed(() =>
  sortedDrawings.value.filter(d => d.file_type === 'step')
)

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

function openPdfFilePicker() {
  fileInputRef.value?.click()
}

function openStepFilePicker() {
  stepFileInputRef.value?.click()
}

async function handleFilesUpload(files: File[]) {
  if (files.length === 0) return

  // Separate by type
  const pdfFiles = files.filter(f => f.name.toLowerCase().endsWith('.pdf'))
  const stepFiles = files.filter(f =>
    f.name.toLowerCase().endsWith('.step') || f.name.toLowerCase().endsWith('.stp')
  )

  const validFiles = [...pdfFiles, ...stepFiles]
  if (validFiles.length === 0) {
    uiStore.showError('Pouze PDF a STEP soubory jsou podporovány')
    return
  }

  uploadingDrawing.value = true
  let successCount = 0
  let errorCount = 0

  try {
    // Upload all files in parallel
    const uploadPromises = validFiles.map(async (file) => {
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
      uiStore.showSuccess(`${successCount} souborů nahráno`)
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

async function confirmDelete(drawing: Drawing) {
  const confirmed = await confirm({
    title: 'Smazat výkres?',
    message: `Opravdu smazat ${drawing.filename}?`,
    type: 'danger'
  })
  if (!confirmed) return

  try {
    await drawingsApi.deleteDrawingById(props.partNumber, drawing.id)
    uiStore.showSuccess(`Výkres ${drawing.filename} smazán`)
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
    <!-- Loading -->
    <div v-if="loading" class="state">
      <Spinner />
      <p>Načítám výkresy...</p>
    </div>

    <!-- Content -->
    <template v-else>
      <!-- PDF DRAWINGS SECTION -->
      <div class="section">
        <h4 class="section-title">Výkresy</h4>

        <!-- PDF Upload Zone -->
        <div
          class="upload-zone"
          :class="{ dragging: isDragging, uploading: uploadingDrawing }"
          @dragenter="onDragEnter"
          @dragover="onDragOver"
          @dragleave="onDragLeave"
          @drop="onDrop"
          @click="openPdfFilePicker"
        >
          <input
            ref="fileInputRef"
            type="file"
            accept="application/pdf"
            multiple
            style="display: none"
            @change="onFileInputChange"
          />

          <Upload :size="ICON_SIZE.XLARGE" :stroke-width="1.5" />
          <p class="upload-label">
            {{ uploadingDrawing ? 'Nahrávám...' : 'PDF výkresy — přetáhněte sem nebo klikněte' }}
          </p>
        </div>

        <!-- PDF Count -->
        <div class="header">
          <span class="count">{{ pdfDrawings.length }} výkresů</span>
        </div>

        <!-- PDF Grid -->
        <div v-if="pdfDrawings.length > 0" class="grid">
          <div
            v-for="drawing in pdfDrawings"
            :key="drawing.id"
            class="card"
            :class="{ primary: drawing.is_primary, broken: !drawing.file_exists }"
          >
            <!-- Broken file warning -->
            <span v-if="!drawing.file_exists" class="badge badge-broken" title="Soubor chybí na disku">
              <AlertTriangle :size="ICON_SIZE.SMALL" />
              Chybí soubor
            </span>

            <!-- Thumbnail -->
            <div class="thumb" :class="{ disabled: !drawing.file_exists }" @click="drawing.file_exists && openDrawing(drawing)">
              <AlertTriangle v-if="!drawing.file_exists" :size="ICON_SIZE.XLARGE" />
              <FileText v-else :size="ICON_SIZE.XLARGE" />
            </div>

            <!-- Info -->
            <div class="info">
              <p class="name">{{ drawing.filename }}</p>
              <p class="rev">Rev {{ drawing.revision }}</p>
            </div>

            <!-- Primary badge -->
            <span v-if="drawing.is_primary && drawing.file_exists" class="badge">
              <Star :size="ICON_SIZE.SMALL" :fill="'currentColor'" />
              Primary
            </span>

            <!-- Actions -->
            <div class="actions">
              <button
                v-if="!drawing.is_primary && drawing.file_exists"
                class="icon-btn"
                @click="setPrimary(drawing)"
                title="Nastavit jako primární"
              >
                <Star :size="ICON_SIZE.STANDARD" />
              </button>
              <button
                class="icon-btn icon-btn-danger"
                @click="confirmDelete(drawing)"
                title="Smazat"
              >
                <Trash2 :size="ICON_SIZE.STANDARD" />
              </button>
            </div>
          </div>
        </div>
        <div v-else class="state-mini">
          <p>Žádné PDF výkresy</p>
        </div>
      </div>

      <!-- 3D DATA SECTION -->
      <div class="section">
        <h4 class="section-title">3D Data</h4>

        <!-- STEP Upload Zone -->
        <div
          class="upload-zone"
          :class="{ dragging: isDragging, uploading: uploadingDrawing }"
          @dragenter="onDragEnter"
          @dragover="onDragOver"
          @dragleave="onDragLeave"
          @drop="onDrop"
          @click="openStepFilePicker"
        >
          <input
            ref="stepFileInputRef"
            type="file"
            accept=".step,.stp"
            multiple
            style="display: none"
            @change="onFileInputChange"
          />

          <Upload :size="ICON_SIZE.XLARGE" :stroke-width="1.5" />
          <p class="upload-label">
            {{ uploadingDrawing ? 'Nahrávám...' : 'STEP soubory — přetáhněte sem nebo klikněte' }}
          </p>
        </div>

        <!-- STEP Count -->
        <div class="header">
          <span class="count">{{ stepDrawings.length }} 3D modelů</span>
        </div>

        <!-- STEP Grid -->
        <div v-if="stepDrawings.length > 0" class="grid">
          <div
            v-for="drawing in stepDrawings"
            :key="drawing.id"
            class="card"
            :class="{ primary: drawing.is_primary, broken: !drawing.file_exists }"
          >
            <!-- Broken file warning -->
            <span v-if="!drawing.file_exists" class="badge badge-broken" title="Soubor chybí na disku">
              <AlertTriangle :size="ICON_SIZE.SMALL" />
              Chybí soubor
            </span>

            <!-- Thumbnail -->
            <div class="thumb" :class="{ disabled: !drawing.file_exists }" @click="drawing.file_exists && openDrawing(drawing)">
              <AlertTriangle v-if="!drawing.file_exists" :size="ICON_SIZE.XLARGE" />
              <Box v-else :size="ICON_SIZE.XLARGE" />
            </div>

            <!-- Info -->
            <div class="info">
              <p class="name">{{ drawing.filename }}</p>
              <p class="rev">Rev {{ drawing.revision }}</p>
            </div>

            <!-- Primary badge -->
            <span v-if="drawing.is_primary && drawing.file_exists" class="badge">
              <Star :size="ICON_SIZE.SMALL" :fill="'currentColor'" />
              Primary
            </span>

            <!-- Actions -->
            <div class="actions">
              <button
                v-if="!drawing.is_primary && drawing.file_exists"
                class="icon-btn"
                @click="setPrimary(drawing)"
                title="Nastavit jako primární"
              >
                <Star :size="ICON_SIZE.STANDARD" />
              </button>
              <button
                class="icon-btn icon-btn-danger"
                @click="confirmDelete(drawing)"
                title="Smazat"
              >
                <Trash2 :size="ICON_SIZE.STANDARD" />
              </button>
            </div>
          </div>
        </div>
        <div v-else class="state-mini">
          <p>Žádné 3D modely</p>
        </div>
      </div>
    </template>

  </Modal>
</template>

<style scoped>
.section {
  margin-bottom: var(--space-6);
}

.section-title {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--space-3) 0;
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-default);
}

.state-mini {
  padding: var(--space-4);
  text-align: center;
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

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

.card.broken {
  border-color: var(--status-error);
  background: rgba(244, 63, 94, 0.05);
  opacity: 0.75;
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
  gap: var(--space-1);
  padding: var(--space-0\.5) var(--space-2);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-success);
  background: var(--bg-base);
  border: 1px solid var(--color-success);
  border-radius: var(--radius-sm);
}

.badge-broken {
  color: var(--status-error);
  border-color: var(--status-error);
  background: rgba(244, 63, 94, 0.1);
}

.thumb.disabled {
  cursor: not-allowed;
  opacity: 0.5;
  color: var(--status-error);
}

.thumb.disabled:hover {
  background: transparent;
  border-color: var(--border-default);
  color: var(--status-error);
}

.actions {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

/* Icon buttons use global .icon-btn classes from design-system.css */

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
