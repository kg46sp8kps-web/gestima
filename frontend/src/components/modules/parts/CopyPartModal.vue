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
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } } }
    errorMessage.value = err.response?.data?.detail || 'Chyba při kopírování dílu'
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

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid var(--b2);
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--t1);
}

.btn-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: var(--rs);
  cursor: pointer;
  color: var(--t3);
  transition: all 100ms var(--ease);
}

.btn-close:hover {
  background: var(--b1);
  color: var(--t1);
}

.modal-body {
  padding: 12px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-text {
  margin: 0;
  font-size: var(--fs);
  color: var(--t2);
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: var(--pad);
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 6px;
  border-radius: var(--rs);
  transition: all 100ms var(--ease);
}

.checkbox-item:hover {
  background: var(--b1);
}

.checkbox-item input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.checkbox-item span {
  font-size: var(--fs);
  color: var(--t2);
  user-select: none;
}

/* Form field */
.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t3);
}

.field-input {
  padding: 6px var(--pad);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  font-size: var(--fs);
  background: var(--ground);
  color: var(--t2);
  transition: all 100ms var(--ease);
}

.field-input:focus {
  outline: none;
  background: rgba(255,255,255,0.03);
  border-color: rgba(255,255,255,0.5);
}

.field-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Error message */
.error-message {
  padding: 6px var(--pad);
  background: rgba(248,113,113,0.1);
  border: 1px solid var(--err);
  border-radius: var(--r);
  color: var(--err);
  font-size: var(--fs);
}

/* Divider */
.divider {
  height: 1px;
  background: var(--b2);
  margin: 6px 0;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  padding: 12px;
  border-top: 1px solid var(--b2);
}

/* Icon buttons use global .icon-btn classes from design-system.css */
</style>
