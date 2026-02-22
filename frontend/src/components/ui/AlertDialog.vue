<template>
  <Modal
    v-model="state.alert.visible"
    size="sm"
    :close-on-backdrop="false"
    :close-on-esc="false"
    :show-close="false"
  >
    <!-- Header with icon + title -->
    <template #header>
      <div class="alert-header">
        <div class="alert-icon" :class="`alert-icon-${options?.type}`">
          <XCircle v-if="options?.type === 'error'" :size="ICON_SIZE.STANDARD" :stroke-width="1.8" />
          <Check v-else-if="options?.type === 'success'" :size="ICON_SIZE.STANDARD" :stroke-width="1.8" />
          <Info v-else-if="options?.type === 'info'" :size="ICON_SIZE.STANDARD" :stroke-width="1.8" />
          <AlertTriangle v-else-if="options?.type === 'warning'" :size="ICON_SIZE.STANDARD" :stroke-width="1.8" />
        </div>
        <h3 class="alert-title">{{ options?.title }}</h3>
      </div>
    </template>

    <!-- Message only -->
    <div class="alert-message">{{ options?.message }}</div>

    <!-- Actions -->
    <template #footer>
      <button
        ref="okButtonRef"
        class="icon-btn"
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
import { ICON_SIZE } from '@/config/design'

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
/* === HEADER === */
.alert-header {
  display: flex;
  align-items: center;
  gap: var(--pad);
}

.alert-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--t1);
  margin: 0;
}

/* === ICON === */
.alert-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--r);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.alert-icon-error {
  background: rgba(248,113,113,0.1);
  color: var(--err);
}

.alert-icon-success {
  background: rgba(52,211,153,0.1);
  color: var(--ok);
}

.alert-icon-info {
  background: var(--red-10);
  color: rgba(229, 57, 53, 0.7);
}

.alert-icon-warning {
  background: rgba(251,191,36,0.1);
  color: var(--warn);
}

/* === MESSAGE === */
.alert-message {
  font-size: var(--fs);
  color: var(--t2);
  line-height: 1.65;
  white-space: pre-line;
}
</style>
