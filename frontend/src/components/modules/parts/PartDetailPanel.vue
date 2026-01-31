<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Part } from '@/types/part'
import type { LinkingGroup } from '@/stores/windows'
import { drawingsApi } from '@/api/drawings'
import { useUiStore } from '@/stores/ui'
import DragDropZone from '@/components/ui/DragDropZone.vue'
import { Package, Settings, DollarSign, Trash2, FileText } from 'lucide-vue-next'

const uiStore = useUiStore()

interface Props {
  part: Part
  linkingGroup?: LinkingGroup
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'open-material': []
  'open-operations': []
  'open-pricing': []
  'open-drawing': []
  'refresh': []
}>()

// Drawing state
const uploadingDrawing = ref(false)
const uploadError = ref<string | null>(null)

const hasDrawing = computed(() => !!props.part.drawing_path)
const drawingUrl = computed(() => {
  if (!hasDrawing.value) return ''
  return drawingsApi.getDrawingUrl(props.part.part_number)
})

// Upload drawing
async function handleDrawingUpload(file: File) {
  uploadingDrawing.value = true
  uploadError.value = null

  try {
    await drawingsApi.uploadToPart(props.part.part_number, file)
    // Refresh part data to get updated drawing_path
    emit('refresh')
    uiStore.addToast({
      type: 'success',
      message: `Výkres nahrán: ${file.name}`
    })
  } catch (error: any) {
    const errorMsg = error.message || 'Nepodařilo se nahrát výkres'
    uploadError.value = errorMsg
    uiStore.addToast({
      type: 'error',
      message: errorMsg
    })
  } finally {
    uploadingDrawing.value = false
  }
}

function handleDrawingError(message: string) {
  uploadError.value = message
}

// Delete drawing
async function handleDeleteDrawing() {
  if (!confirm('Smazat výkres?')) return

  try {
    await drawingsApi.deleteDrawing(props.part.part_number)
    emit('refresh')
    uiStore.addToast({
      type: 'success',
      message: 'Výkres smazán'
    })
  } catch (error: any) {
    uiStore.addToast({
      type: 'error',
      message: `Nepodařilo se smazat výkres: ${error.message}`
    })
  }
}

// Open drawing in floating window
function handleOpenDrawing() {
  emit('open-drawing')
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('cs-CZ')
}
</script>

<template>
  <div class="part-detail-panel">
    <!-- Compact Header -->
    <div class="part-header-compact">
      <div class="header-item">
        <span class="header-label">Artikl:</span>
        <span class="header-value">{{ part.article_number || '—' }}</span>
      </div>
      <div class="header-item">
        <span class="header-label">Výkres:</span>
        <span class="header-value">{{ part.drawing_path || '—' }}</span>
      </div>
      <div class="header-item">
        <span class="header-label">Název:</span>
        <span class="header-value">{{ part.name }}</span>
      </div>
      <div class="header-item">
        <span class="header-label">Revize:</span>
        <span class="header-value">{{ part.customer_revision || '—' }}</span>
      </div>
      <div class="header-item full-width" v-if="part.notes">
        <span class="header-label">Poznámky:</span>
        <span class="header-value">{{ part.notes }}</span>
      </div>
      <div class="header-item">
        <span class="part-number-badge">{{ part.part_number }}</span>
      </div>
    </div>

    <!-- Drawing Section -->
    <div class="drawing-section">
      <h3 class="section-title">Výkres</h3>

      <!-- No drawing - show upload zone -->
      <div v-if="!hasDrawing">
        <DragDropZone
          :model-value="null"
          accept="application/pdf"
          :max-size="10 * 1024 * 1024"
          label="Nahrajte PDF výkres"
          :loading="uploadingDrawing"
          @upload="handleDrawingUpload"
          @error="handleDrawingError"
        />
        <p v-if="uploadError" class="upload-error">{{ uploadError }}</p>
      </div>

      <!-- Has drawing - show info + delete -->
      <div v-else class="drawing-exists">
        <p class="drawing-filename">
          <FileText :size="16" style="display: inline; vertical-align: middle;" />
          {{ part.part_number }}.pdf
        </p>
        <button class="btn-sm btn-danger" @click="handleDeleteDrawing">
          <Trash2 :size="14" />
          Smazat
        </button>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="actions-grid">
      <button class="action-button" @click="emit('open-material')">
        <Package :size="32" class="action-icon" />
        <span class="action-label">Materiál</span>
      </button>
      <button class="action-button" @click="emit('open-operations')">
        <Settings :size="32" class="action-icon" />
        <span class="action-label">Operace</span>
      </button>
      <button class="action-button" @click="emit('open-pricing')">
        <DollarSign :size="32" class="action-icon" />
        <span class="action-label">Ceny</span>
      </button>
      <button
        v-if="hasDrawing"
        class="action-button"
        @click="handleOpenDrawing"
      >
        <FileText :size="32" class="action-icon" />
        <span class="action-label">Výkres</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
/* Copy relevant styles from PartMainModule.vue DETAIL section */
.part-detail-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

/* Compact Header Grid */
.part-header-compact {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}

.header-item {
  display: flex;
  gap: var(--space-2);
  align-items: baseline;
}

.header-item.full-width {
  grid-column: 1 / -1;
}

.header-label {
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  white-space: nowrap;
}

.header-value {
  color: var(--text-body);
}

.part-number-badge {
  padding: var(--space-1) var(--space-2);
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  justify-self: end;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}

.action-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 2px solid var(--border-default);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: var(--transition-normal);
}

.action-button:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.action-icon {
  color: var(--color-primary);
}

.action-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-body);
}

/* Drawing section */
.drawing-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.section-title {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.upload-error {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-danger);
  background: rgba(244, 63, 94, 0.05);
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-sm);
}

.drawing-preview-container {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.drawing-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
</style>
