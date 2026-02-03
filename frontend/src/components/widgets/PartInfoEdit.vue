<script setup lang="ts">
/**
 * PartInfoEdit.vue - Part information edit widget
 *
 * Inline edit form for part basic information.
 * Supports both view and edit modes with validation.
 *
 * @example
 * ```vue
 * <PartInfoEdit
 *   :context="{ part, isAdmin }"
 *   @action="handleAction"
 * />
 * ```
 */

import { ref, watch, computed } from 'vue'
import Input from '@/components/ui/Input.vue'
import { Edit, Copy, Trash2, AlertTriangle, Check, X } from 'lucide-vue-next'
import { confirm } from '@/composables/useDialog'

interface Props {
  context?: {
    part?: {
      article_number: string | null
      drawing_number: string | null
      name: string
      customer_revision: string | null
      part_number: string
    }
    isAdmin?: boolean
  }
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'action': [action: string, payload?: any]
}>()

// Edit mode state
const isEditMode = ref(false)

// Form data
const formData = ref({
  article_number: '',
  drawing_number: '',
  name: '',
  customer_revision: ''
})

const isLoading = ref(false)
const errorMessage = ref('')

// Watch part changes and update form
watch(() => props.context?.part, (part) => {
  if (part && !isEditMode.value) {
    formData.value = {
      article_number: part.article_number || '',
      drawing_number: part.drawing_number || '',
      name: part.name || '',
      customer_revision: part.customer_revision || ''
    }
  }
}, { immediate: true })

function handleEdit() {
  isEditMode.value = true
  emit('action', 'action:edit')
}

function handleCancel() {
  if (props.context?.part) {
    formData.value = {
      article_number: props.context.part.article_number || '',
      drawing_number: props.context.part.drawing_number || '',
      name: props.context.part.name || '',
      customer_revision: props.context.part.customer_revision || ''
    }
  }
  errorMessage.value = ''
  isEditMode.value = false
  emit('action', 'action:cancel')
}

function handleSave() {
  isLoading.value = true
  errorMessage.value = ''

  const payload = {
    article_number: formData.value.article_number || null,
    drawing_number: formData.value.drawing_number || null,
    name: formData.value.name,
    customer_revision: formData.value.customer_revision || null
  }

  emit('action', 'action:save', payload)
}

function handleCopy() {
  emit('action', 'action:copy')
}

async function handleDelete() {
  const confirmed = await confirm({
    title: 'Smazat díl?',
    message: `Opravdu chcete smazat díl ${props.context?.part?.part_number}?\n\nTato akce je nevratná!`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })

  if (confirmed) {
    emit('action', 'action:delete')
  }
}

// Expose method for parent to update loading state
defineExpose({
  setLoading: (loading: boolean) => {
    isLoading.value = loading
  },
  setError: (error: string) => {
    errorMessage.value = error
  },
  exitEditMode: () => {
    isEditMode.value = false
  }
})
</script>

<template>
  <div class="part-info-edit">
    <!-- View mode toolbar (bottom right) -->
    <div v-if="!isEditMode" class="view-toolbar">
      <button class="btn-edit" @click="handleCopy" title="Kopírovat díl">
        <Copy :size="15" />
      </button>
      <button
        v-if="context?.isAdmin"
        class="btn-edit btn-delete"
        @click="handleDelete"
        title="Smazat díl"
      >
        <Trash2 :size="15" />
      </button>
      <button class="btn-edit" @click="handleEdit" title="Upravit díl">
        <Edit :size="15" />
      </button>
    </div>

    <!-- Error message -->
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>

    <!-- Fields -->
    <div class="form-field">
      <label class="field-label">Artikl:</label>
      <Input
        v-if="isEditMode"
        v-model="formData.article_number"
        placeholder="Dodavatelské číslo"
        :disabled="isLoading"
      />
      <span v-else class="field-value">{{ context?.part?.article_number || '—' }}</span>
    </div>

    <div class="form-field">
      <label class="field-label">Číslo výkresu:</label>
      <Input
        v-if="isEditMode"
        v-model="formData.drawing_number"
        placeholder="Číslo výkresu"
        :disabled="isLoading"
      />
      <span v-else class="field-value">{{ context?.part?.drawing_number || '—' }}</span>
    </div>

    <div class="form-field">
      <label class="field-label">Název:</label>
      <Input
        v-if="isEditMode"
        v-model="formData.name"
        placeholder="Název dílu"
        :disabled="isLoading"
      />
      <span v-else class="field-value">{{ context?.part?.name || '—' }}</span>
    </div>

    <div class="form-field">
      <label class="field-label">Revize:</label>
      <Input
        v-if="isEditMode"
        v-model="formData.customer_revision"
        placeholder="Zákaznická revize"
        :disabled="isLoading"
      />
      <span v-else class="field-value">{{ context?.part?.customer_revision || '—' }}</span>
    </div>

    <!-- Edit mode toolbar (bottom right) -->
    <div v-if="isEditMode" class="edit-toolbar">
      <AlertTriangle :size="20" class="warning-icon" />
      <button
        class="btn-action btn-confirm"
        @click="handleSave"
        :disabled="isLoading"
        title="Potvrdit změny"
      >
        <Check :size="18" />
      </button>
      <button
        class="btn-action btn-cancel"
        @click="handleCancel"
        :disabled="isLoading"
        title="Zrušit změny"
      >
        <X :size="18" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.part-info-edit {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  padding-bottom: calc(var(--space-3) + 32px);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  position: relative;
  height: 100%;
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

.btn-delete:hover {
  color: var(--color-danger);
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

/* Action buttons */
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
</style>
