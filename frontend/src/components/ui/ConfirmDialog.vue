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
  gap: var(--pad);
}

.confirm-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--t1);
  margin: 0;
}

/* === ICON === */
.confirm-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--r);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.confirm-icon-danger {
  background: rgba(248,113,113,0.1);
  color: var(--err);
}

.confirm-icon-warning {
  background: rgba(251,191,36,0.1);
  color: var(--warn);
}

.confirm-icon-info {
  background: var(--red-10);
  color: rgba(229, 57, 53, 0.7);
}

.confirm-icon-success {
  background: rgba(52,211,153,0.1);
  color: var(--ok);
}

/* === MESSAGE === */
.confirm-message {
  font-size: var(--fs);
  color: var(--t2);
  line-height: 1.65;
  white-space: pre-line;
}
</style>
