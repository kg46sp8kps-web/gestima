<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { X, Check } from 'lucide-vue-next'
import { usePartsStore } from '@/stores/parts'
import { ICON_SIZE } from '@/config/design'
import type { Part } from '@/types/part'

interface Props {
  modelValue: boolean
  partNumber: string
  sourcePart: Part
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'success': []
}>()

const partsStore = usePartsStore()

// Refs
const confirmButtonRef = ref<HTMLButtonElement | null>(null)

// Form data
const articleNumber = ref('')
const copyOperations = ref(true)
const copyMaterial = ref(true)
const copyBatches = ref(false)
const isLoading = ref(false)
const errorMessage = ref('')

// Reset form when modal opens + auto-focus
watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    articleNumber.value = ''
    copyOperations.value = true
    copyMaterial.value = true
    copyBatches.value = false
    errorMessage.value = ''
    // Auto-focus confirm button after modal opens
    nextTick(() => {
      confirmButtonRef.value?.focus()
    })
  }
})

// Keyboard handler
const handleKeydown = (e: KeyboardEvent) => {
  if (!props.modelValue) return
  if (e.key === 'Escape') {
    handleClose()
  } else if (e.key === 'Enter' && !isLoading.value) {
    handleConfirm()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

function handleClose() {
  if (isLoading.value) return
  emit('update:modelValue', false)
}

async function handleConfirm() {
  if (!articleNumber.value.trim()) {
    errorMessage.value = 'Artikl je povinný'
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    // Create new part with data from source part
    const newPartData = {
      article_number: articleNumber.value,
      name: props.sourcePart.name,
      customer_revision: props.sourcePart.customer_revision,
      drawing_number: props.sourcePart.drawing_number,
      notes: props.sourcePart.notes
    }

    const copyFrom = {
      sourcePartNumber: props.partNumber,
      copyOperations: copyOperations.value,
      copyMaterial: copyMaterial.value,
      copyBatches: copyBatches.value
    }

    await partsStore.createPart(newPartData, copyFrom)

    emit('update:modelValue', false)
    emit('success')
  } catch (error: any) {
    errorMessage.value = error.response?.data?.detail || 'Chyba při kopírování dílu'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div v-if="modelValue" class="modal-overlay" @click.self="handleClose">
    <div class="modal-content">
      <div class="modal-header">
        <h3>Kopírovat díl {{ partNumber }}</h3>
        <button class="btn-close" @click="handleClose" title="Zavřít">
          <X :size="ICON_SIZE.STANDARD" />
        </button>
      </div>

      <div class="modal-body">
        <!-- Article number input -->
        <div class="form-field">
          <label class="field-label">Artikl nového dílu *</label>
          <input
            v-model="articleNumber"
            type="text"
            class="field-input"
            placeholder="Zadejte nový artikl"
            :disabled="isLoading"
            autofocus
          />
        </div>

        <!-- Error message -->
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <div class="divider"></div>

        <p class="info-text">
          Vyberte co chcete zkopírovat:
        </p>

        <div class="checkbox-group">
          <label class="checkbox-item">
            <input type="checkbox" v-model="copyOperations" :disabled="isLoading" />
            <span>Kopírovat operace</span>
          </label>

          <label class="checkbox-item">
            <input type="checkbox" v-model="copyMaterial" :disabled="isLoading" />
            <span>Kopírovat materiál</span>
          </label>

          <label class="checkbox-item">
            <input type="checkbox" v-model="copyBatches" :disabled="isLoading" />
            <span>Kopírovat dávky</span>
          </label>
        </div>
      </div>

      <div class="modal-footer">
        <button class="icon-btn icon-btn-danger" @click="handleClose" :disabled="isLoading" title="Zrušit (Escape)">
          <X :size="ICON_SIZE.STANDARD" />
        </button>
        <button ref="confirmButtonRef" class="icon-btn icon-btn-success" @click="handleConfirm" :disabled="isLoading" title="Kopírovat díl (Enter)">
          <Check :size="ICON_SIZE.STANDARD" />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-default);
}

.modal-header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.btn-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-secondary);
  transition: var(--transition-fast);
}

.btn-close:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.modal-body {
  padding: var(--space-4);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.info-text {
  margin: 0;
  font-size: var(--text-base);
  color: var(--text-body);
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  padding: var(--space-2);
  border-radius: var(--radius-sm);
  transition: var(--transition-fast);
}

.checkbox-item:hover {
  background: var(--bg-hover);
}

.checkbox-item input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.checkbox-item span {
  font-size: var(--text-base);
  color: var(--text-body);
  user-select: none;
}

/* Form field */
.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.field-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.field-input {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  background: var(--bg-input);
  color: var(--text-body);
  transition: var(--transition-fast);
}

.field-input:focus {
  outline: none;
  background: var(--state-focus-bg);
  border-color: var(--state-focus-border);
}

.field-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Error message */
.error-message {
  padding: var(--space-2) var(--space-3);
  background: var(--color-error-bg);
  border: 1px solid var(--color-error-border);
  border-radius: var(--radius-md);
  color: var(--color-error-text);
  font-size: var(--text-sm);
}

/* Divider */
.divider {
  height: 1px;
  background: var(--border-default);
  margin: var(--space-2) 0;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
  padding: var(--space-4);
  border-top: 1px solid var(--border-default);
}

/* Icon buttons use global .icon-btn classes from design-system.css */
</style>
