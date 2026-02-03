<template>
  <Modal
    v-model="state.confirm.visible"
    size="sm"
    :close-on-backdrop="false"
    :close-on-esc="false"
    :show-close="false"
  >
    <!-- Header with icon + title -->
    <template #header>
      <div class="confirm-header">
        <div class="confirm-icon" :class="`confirm-icon-${options?.type}`">
          <Trash2 v-if="options?.type === 'danger'" :size="ICON_SIZE.STANDARD" :stroke-width="2" />
          <AlertTriangle v-else-if="options?.type === 'warning'" :size="ICON_SIZE.STANDARD" :stroke-width="2" />
          <Info v-else-if="options?.type === 'info'" :size="ICON_SIZE.STANDARD" :stroke-width="2" />
          <Check v-else-if="options?.type === 'success'" :size="ICON_SIZE.STANDARD" :stroke-width="2" />
        </div>
        <h3 class="confirm-title">{{ options?.title }}</h3>
      </div>
    </template>

    <!-- Message only -->
    <div class="confirm-message">{{ options?.message }}</div>

    <!-- Actions -->
    <template #footer>
      <button
        class="icon-btn icon-btn-cancel"
        @click="handleCancel"
        title="Zrušit (ESC)"
      >
        <X :size="ICON_SIZE.LARGE" :stroke-width="2" />
      </button>
      <button
        ref="confirmButtonRef"
        class="icon-btn icon-btn-confirm"
        :class="`icon-btn-${options?.type}`"
        @click="handleConfirm"
        :title="`${options?.confirmText} (ENTER)`"
      >
        <Check :size="ICON_SIZE.LARGE" :stroke-width="2" />
      </button>
    </template>
  </Modal>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'
import { Trash2, AlertTriangle, Info, Check, X } from 'lucide-vue-next'
import Modal from './Modal.vue'
import { useDialog } from '@/composables/useDialog'

// Icon size constant (from Librarian report)
const ICON_SIZE = {
  STANDARD: 20,
  LARGE: 24
}

const { state, closeConfirm } = useDialog()

const confirmButtonRef = ref<HTMLButtonElement | null>(null)

// Computed options with defaults
const options = computed(() => state.confirm.options)

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
/* === HEADER === */
.confirm-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.confirm-title {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
}

/* === ICON === */
.confirm-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
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
  font-size: var(--text-base);
  color: var(--text-body);
  line-height: var(--leading-relaxed);
  white-space: pre-line;
}

/* === ICON BUTTONS === */
.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.icon-btn:hover {
  background: var(--state-hover);
}

.icon-btn:focus-visible {
  outline: 2px solid var(--state-focus-border);
  outline-offset: 2px;
}

/* Cancel button */
.icon-btn-cancel {
  color: var(--text-secondary);
}

.icon-btn-cancel:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.05);
}

/* Confirm button - colors by type */
.icon-btn-confirm.icon-btn-danger {
  color: #f43f5e;
}

.icon-btn-confirm.icon-btn-danger:hover {
  background: rgba(244, 63, 94, 0.15);
}

.icon-btn-confirm.icon-btn-warning {
  color: #d97706;
}

.icon-btn-confirm.icon-btn-warning:hover {
  background: rgba(217, 119, 6, 0.15);
}

.icon-btn-confirm.icon-btn-info {
  color: #2563eb;
}

.icon-btn-confirm.icon-btn-info:hover {
  background: rgba(37, 99, 235, 0.15);
}

.icon-btn-confirm.icon-btn-success {
  color: #059669;
}

.icon-btn-confirm.icon-btn-success:hover {
  background: rgba(5, 150, 105, 0.15);
}
</style>
