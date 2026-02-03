<template>
  <Modal
    v-model="state.confirm.visible"
    :title="options?.title"
    size="sm"
    :close-on-backdrop="false"
    :close-on-esc="false"
    :show-close="false"
  >
    <!-- Message with icon -->
    <div class="confirm-content">
      <div class="confirm-icon" :class="`confirm-icon-${options?.type}`">
        <Trash2 v-if="options?.type === 'danger'" :size="ICON_SIZE.STANDARD" :stroke-width="2" />
        <AlertTriangle v-else-if="options?.type === 'warning'" :size="ICON_SIZE.STANDARD" :stroke-width="2" />
        <Info v-else-if="options?.type === 'info'" :size="ICON_SIZE.STANDARD" :stroke-width="2" />
        <Check v-else-if="options?.type === 'success'" :size="ICON_SIZE.STANDARD" :stroke-width="2" />
      </div>

      <div class="confirm-message">{{ options?.message }}</div>
    </div>

    <!-- Actions -->
    <template #footer>
      <button
        class="btn btn-secondary"
        @click="handleCancel"
      >
        {{ options?.cancelText }}
      </button>
      <button
        ref="confirmButtonRef"
        class="btn"
        :class="buttonClass"
        @click="handleConfirm"
      >
        {{ options?.confirmText }}
      </button>
    </template>
  </Modal>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'
import { Trash2, AlertTriangle, Info, Check } from 'lucide-vue-next'
import Modal from './Modal.vue'
import { useDialog } from '@/composables/useDialog'

// Icon size constant (from Librarian report)
const ICON_SIZE = {
  STANDARD: 20
}

const { state, closeConfirm } = useDialog()

const confirmButtonRef = ref<HTMLButtonElement | null>(null)

// Computed options with defaults
const options = computed(() => state.confirm.options)

// Button class based on type
const buttonClass = computed(() => {
  const type = options.value?.type || 'warning'
  if (type === 'danger') return 'btn-danger'
  if (type === 'success') return 'btn-primary'
  return 'btn-primary'
})

// Handle confirm
function handleConfirm() {
  closeConfirm(true)
}

// Handle cancel
function handleCancel() {
  closeConfirm(false)
}

// Handle keyboard events
function handleKeydown(e: KeyboardEvent) {
  if (!state.confirm.visible) return

  if (e.key === 'Enter') {
    e.preventDefault()
    handleConfirm()
  } else if (e.key === 'Escape') {
    e.preventDefault()
    handleCancel()
  }
}

// Auto-focus confirm button when dialog opens
watch(() => state.confirm.visible, async (visible) => {
  if (visible) {
    await nextTick()
    confirmButtonRef.value?.focus()

    // Add keyboard listener
    document.addEventListener('keydown', handleKeydown)
  } else {
    // Remove keyboard listener
    document.removeEventListener('keydown', handleKeydown)
  }
}, { immediate: true })
</script>

<style scoped>
/* === CONFIRM CONTENT === */
.confirm-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
  text-align: center;
  padding: var(--space-4) 0;
}

/* === ICON === */
.confirm-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.confirm-icon-danger {
  background: rgba(244, 63, 94, 0.15);
  color: #f43f5e;
}

.confirm-icon-warning {
  background: rgba(217, 119, 6, 0.15);
  color: #d97706;
}

.confirm-icon-info {
  background: rgba(37, 99, 235, 0.15);
  color: #2563eb;
}

.confirm-icon-success {
  background: rgba(5, 150, 105, 0.15);
  color: #059669;
}

/* === MESSAGE === */
.confirm-message {
  font-size: var(--text-lg);
  color: var(--text-body);
  line-height: var(--leading-relaxed);
  white-space: pre-line;
  max-width: 400px;
}
</style>
