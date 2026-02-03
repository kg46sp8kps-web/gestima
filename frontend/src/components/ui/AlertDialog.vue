<template>
  <Modal
    v-model="state.alert.visible"
    :title="options?.title"
    size="sm"
    :close-on-backdrop="false"
    :close-on-esc="false"
    :show-close="false"
  >
    <!-- Message with icon -->
    <div class="alert-content">
      <div class="alert-icon" :class="`alert-icon-${options?.type}`">
        <XCircle v-if="options?.type === 'error'" :size="ICON_SIZE.STANDARD" :stroke-width="2" />
        <Check v-else-if="options?.type === 'success'" :size="ICON_SIZE.STANDARD" :stroke-width="2" />
        <Info v-else-if="options?.type === 'info'" :size="ICON_SIZE.STANDARD" :stroke-width="2" />
        <AlertTriangle v-else-if="options?.type === 'warning'" :size="ICON_SIZE.STANDARD" :stroke-width="2" />
      </div>

      <div class="alert-message">{{ options?.message }}</div>
    </div>

    <!-- Actions -->
    <template #footer>
      <button
        ref="okButtonRef"
        class="icon-btn icon-btn-close"
        @click="handleClose"
        title="Zavřít (ENTER/ESC)"
      >
        <X :size="ICON_SIZE.LARGE" :stroke-width="2" />
      </button>
    </template>
  </Modal>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'
import { XCircle, Check, Info, AlertTriangle, X } from 'lucide-vue-next'
import Modal from './Modal.vue'
import { useDialog } from '@/composables/useDialog'

// Icon size constant (from Librarian report)
const ICON_SIZE = {
  STANDARD: 20,
  LARGE: 24
}

const { state, closeAlert } = useDialog()

const okButtonRef = ref<HTMLButtonElement | null>(null)

// Computed options with defaults
const options = computed(() => state.alert.options)

// Handle close
function handleClose() {
  closeAlert()
}

// Handle keyboard events
function handleKeydown(e: KeyboardEvent) {
  if (!state.alert.visible) return

  if (e.key === 'Enter' || e.key === 'Escape') {
    e.preventDefault()
    handleClose()
  }
}

// Auto-focus OK button when dialog opens
watch(() => state.alert.visible, async (visible) => {
  if (visible) {
    await nextTick()
    okButtonRef.value?.focus()

    // Add keyboard listener
    document.addEventListener('keydown', handleKeydown)
  } else {
    // Remove keyboard listener
    document.removeEventListener('keydown', handleKeydown)
  }
}, { immediate: true })
</script>

<style scoped>
/* === ALERT CONTENT === */
.alert-content {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: var(--space-4);
  padding: var(--space-2) 0;
}

/* === ICON === */
.alert-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.alert-icon-error {
  background: rgba(244, 63, 94, 0.15);
  color: #f43f5e;
}

.alert-icon-success {
  background: rgba(5, 150, 105, 0.15);
  color: #059669;
}

.alert-icon-info {
  background: rgba(37, 99, 235, 0.15);
  color: #2563eb;
}

.alert-icon-warning {
  background: rgba(217, 119, 6, 0.15);
  color: #d97706;
}

/* === MESSAGE === */
.alert-message {
  flex: 1;
  font-size: var(--text-base);
  color: var(--text-body);
  line-height: var(--leading-relaxed);
  white-space: pre-line;
  text-align: left;
}

/* === ICON BUTTON === */
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
  color: var(--text-primary);
}

.icon-btn:focus-visible {
  outline: 2px solid var(--state-focus-border);
  outline-offset: 2px;
}

.icon-btn-close {
  color: var(--text-secondary);
}

.icon-btn-close:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.05);
}
</style>
