<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Part, PartUpdate } from '@/types/part'
import type { LinkingGroup } from '@/stores/windows'
import DrawingsManagementModal from './DrawingsManagementModal.vue'
import CopyPartModal from './CopyPartModal.vue'
import Input from '@/components/ui/Input.vue'
import Button from '@/components/ui/Button.vue'
import { updatePart } from '@/api/parts'
import { Package, Settings, DollarSign, FileText, AlertTriangle, Check, X, Edit, Copy } from 'lucide-vue-next'

interface Props {
  part: Part
  linkingGroup?: LinkingGroup
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'open-material': []
  'open-operations': []
  'open-pricing': []
  'open-drawing': [drawingId?: number]
  'refresh': []
}>()


// Drawings management modal
const showDrawingsModal = ref(false)

// Copy part modal
const showCopyModal = ref(false)

// Edit mode
const isEditMode = ref(false)

// Form data for inline editing
const formData = ref({
  article_number: '',
  drawing_number: '',
  name: '',
  customer_revision: ''
})

const isLoading = ref(false)
const errorMessage = ref('')

// Initialize form data when part changes
watch(() => props.part, (part) => {
  if (part) {
    formData.value = {
      article_number: part.article_number || '',
      drawing_number: part.drawing_number || '',
      name: part.name || '',
      customer_revision: part.customer_revision || ''
    }
  }
}, { immediate: true })

async function handleSave() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const updateData: PartUpdate = {
      article_number: formData.value.article_number || null,
      drawing_number: formData.value.drawing_number || null,
      name: formData.value.name,
      customer_revision: formData.value.customer_revision || null,
      version: props.part.version
    }

    await updatePart(props.part.part_number, updateData)
    emit('refresh')
    isEditMode.value = false // Exit edit mode after save
  } catch (error: any) {
    errorMessage.value = error.response?.data?.detail || 'Chyba při ukládání dílu'
    console.error('Failed to update part:', error)
  } finally {
    isLoading.value = false
  }
}

function handleEdit() {
  isEditMode.value = true
}

function handleCancel() {
  // Reset form data to original values
  formData.value = {
    article_number: props.part.article_number || '',
    drawing_number: props.part.drawing_number || '',
    name: props.part.name || '',
    customer_revision: props.part.customer_revision || ''
  }
  errorMessage.value = ''
  isEditMode.value = false
}

function handleDrawingButtonClick() {
  // Check if part has any drawings
  if (props.part.drawing_path) {
    // Has drawing = open primary drawing window
    emit('open-drawing')
  } else {
    // No drawing = open modal for upload
    showDrawingsModal.value = true
  }
}

function handleDrawingButtonRightClick(event: MouseEvent) {
  event.preventDefault()
  // Right-click = always open modal for management
  showDrawingsModal.value = true
}

function handleCopy() {
  showCopyModal.value = true
}

function handleCopySuccess() {
  // Modal handles the copy internally, just refresh the list
  emit('refresh')
}

function handleOpenDrawing(drawingId?: number) {
  emit('open-drawing', drawingId)
  showDrawingsModal.value = false
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('cs-CZ')
}
</script>

<template>
  <div class="part-detail-panel">
    <!-- Compact Header -->
    <div class="part-header-compact">
      <!-- View mode: Subtle buttons (bottom right) -->
      <div v-if="!isEditMode" class="view-toolbar">
        <button class="btn-edit" @click="handleCopy" title="Kopírovat díl">
          <Copy :size="14" />
        </button>
        <button class="btn-edit" @click="handleEdit" title="Upravit díl">
          <Edit :size="14" />
        </button>
      </div>

      <!-- Error message -->
      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>

      <!-- Fields - conditional: editable or read-only -->
      <div class="form-field">
        <label class="field-label">Artikl:</label>
        <Input
          v-if="isEditMode"
          v-model="formData.article_number"
          placeholder="Dodavatelské číslo"
          :disabled="isLoading"
        />
        <span v-else class="field-value">{{ part.article_number || '—' }}</span>
      </div>

      <div class="form-field">
        <label class="field-label">Číslo výkresu:</label>
        <Input
          v-if="isEditMode"
          v-model="formData.drawing_number"
          placeholder="Číslo výkresu"
          :disabled="isLoading"
        />
        <span v-else class="field-value">{{ part.drawing_number || '—' }}</span>
      </div>

      <div class="form-field">
        <label class="field-label">Název:</label>
        <Input
          v-if="isEditMode"
          v-model="formData.name"
          placeholder="Název dílu"
          :disabled="isLoading"
        />
        <span v-else class="field-value">{{ part.name || '—' }}</span>
      </div>

      <div class="form-field">
        <label class="field-label">Revize:</label>
        <Input
          v-if="isEditMode"
          v-model="formData.customer_revision"
          placeholder="Zákaznická revize"
          :disabled="isLoading"
        />
        <span v-else class="field-value">{{ part.customer_revision || '—' }}</span>
      </div>

      <!-- Edit mode: Toolbar (bottom right) -->
      <div v-if="isEditMode" class="edit-toolbar">
        <AlertTriangle :size="20" class="warning-icon" />
        <button class="btn-action btn-confirm" @click="handleSave" :disabled="isLoading" title="Potvrdit změny">
          <Check :size="18" />
        </button>
        <button class="btn-action btn-cancel" @click="handleCancel" :disabled="isLoading" title="Zrušit změny">
          <X :size="18" />
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
        class="action-button"
        @click="handleDrawingButtonClick"
        @contextmenu="handleDrawingButtonRightClick"
        title="Klikni = otevři výkres | Pravé tlačítko = správa výkresů"
      >
        <FileText :size="32" class="action-icon" />
        <span class="action-label">Výkres</span>
      </button>
    </div>

    <!-- Drawings Management Modal -->
    <DrawingsManagementModal
      v-model="showDrawingsModal"
      :part-number="part.part_number"
      @refresh="emit('refresh')"
      @open-drawing="handleOpenDrawing"
    />

    <!-- Copy Part Modal -->
    <CopyPartModal
      v-model="showCopyModal"
      :part-number="part.part_number"
      :source-part="part"
      @success="handleCopySuccess"
    />
  </div>
</template>

<style scoped>
/* Copy relevant styles from PartMainModule.vue DETAIL section */
.part-detail-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

/* Compact Header - Vertical Layout */
.part-header-compact {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  padding-bottom: calc(var(--space-3) + 32px); /* Extra space for toolbar */
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  position: relative;
}

/* View mode toolbar (bottom right) */
.view-toolbar {
  position: absolute;
  bottom: var(--space-3);
  right: var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  z-index: 1;
}

/* Subtle edit button */
.btn-edit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-tertiary);
  transition: var(--transition-fast);
  opacity: 0.5;
}

.btn-edit:hover {
  opacity: 1;
  color: var(--text-secondary);
  background: var(--bg-hover);
}

/* Edit mode toolbar (bottom right) */
.edit-toolbar {
  position: absolute;
  bottom: var(--space-3);
  right: var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  z-index: 1;
}

.warning-icon {
  color: var(--color-warning);
}

/* Action buttons - same subtle style as edit button */
.btn-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-fast);
  opacity: 0.5;
}

.btn-action:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.btn-action:not(:disabled):hover {
  opacity: 1;
  background: var(--bg-hover);
}

.btn-confirm {
  color: var(--color-success);
}

.btn-cancel {
  color: var(--color-error);
}

/* Error message */
.error-message {
  padding: var(--space-3);
  background: var(--color-error-bg);
  border: 1px solid var(--color-error-border);
  border-radius: var(--radius-md);
  color: var(--color-error-text);
  font-size: var(--text-sm);
}

/* Form fields */
.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.field-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.field-value {
  font-size: var(--text-base);
  color: var(--text-body);
  padding: var(--space-2) 0;
  line-height: 1.5;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
  transition: transform var(--transition-normal);
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

</style>
