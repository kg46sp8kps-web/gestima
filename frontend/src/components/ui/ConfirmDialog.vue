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
          <Trash2 v-if="options?.type === 'danger'" :size="ICON_SIZE.STANDARD" :stroke-width="1.8" />
          <AlertTriangle v-else-if="options?.type === 'warning'" :size="ICON_SIZE.STANDARD" :stroke-width="1.8" />
          <Info v-else-if="options?.type === 'info'" :size="ICON_SIZE.STANDARD" :stroke-width="1.8" />
          <Check v-else-if="options?.type === 'success'" :size="ICON_SIZE.STANDARD" :stroke-width="1.8" />
        </div>
        <h3 class="confirm-title">{{ options?.title }}</h3>
      </div>
    </template>

    <!-- Message only -->
    <div class="confirm-message">{{ options?.message }}</div>

    <!-- Actions -->
    <template #footer>
      <button
        class="icon-btn"
        @click="handleCancel"
        title="Zrušit (ESC)"
      >
        <X :size="ICON_SIZE.LARGE" :stroke-width="2" />
      </button>
      <button
        ref="confirmButtonRef"
        class="icon-btn"
        :class="`icon-btn-${options?.type === 'danger' ? 'danger' : 'brand'}`"
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
import { ICON_SIZE } from '@/config/design'

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
  font-size: var(--text-md);
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
  background: rgba(239, 68, 68, 0.1);
  color: var(--status-error);
}

.confirm-icon-warning {
  background: rgba(234, 179, 8, 0.1);
  color: var(--status-warn);
}

.confirm-icon-info {
  background: var(--brand-subtle);
  color: var(--brand-text);
}

.confirm-icon-success {
  background: rgba(34, 197, 94, 0.1);
  color: var(--status-ok);
}

/* === MESSAGE === */
.confirm-message {
  font-size: var(--text-base);
  color: var(--text-body);
  line-height: var(--leading-relaxed);
  white-space: pre-line;
}
</style>
