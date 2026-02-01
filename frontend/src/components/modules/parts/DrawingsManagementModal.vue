<script setup lang="ts">
/**
 * DrawingsManagementModal - Manage multiple PDF drawings for a part
 * Features: List, upload, set primary, delete, open in floating window
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

async function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  // Get revision from prompt
  const revision = prompt('Zadejte revizi (volitelné, 1-2 velká písmena A-Z):')
  if (revision !== null && revision && !/^[A-Z]{1,2}$/.test(revision)) {
    uiStore.showError('Revize musí být 1-2 velká písmena (A-Z)')
    input.value = ''
    return
  }

  uploadingDrawing.value = true
  try {
    await drawingsApi.uploadDrawing(
      props.partNumber,
      file,
      revision || undefined
    )
    uiStore.showSuccess('Výkres nahrán')
    await loadDrawings()
    emit('refresh')
  } catch (error: any) {
    uiStore.showError(`Nepodařilo se nahrát výkres: ${error.message}`)
  } finally {
    uploadingDrawing.value = false
    input.value = ''
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
    <!-- Header with upload -->
    <div class="header">
      <span class="count">{{ drawings.length }} výkresů</span>
      <label class="btn-primary" :class="{ disabled: uploadingDrawing }">
        <Upload :size="16" />
        {{ uploadingDrawing ? 'Nahrávám...' : 'Nahrát výkres' }}
        <input
          type="file"
          accept="application/pdf"
          style="display: none"
          :disabled="uploadingDrawing"
          @change="handleFileSelect"
        />
      </label>
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
</style>
