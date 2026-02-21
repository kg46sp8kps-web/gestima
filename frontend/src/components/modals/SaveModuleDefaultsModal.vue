<script setup lang="ts">
/**
 * SaveModuleDefaultsModal - Confirm saving window size/layout as defaults
 * Shows changes summary and allows user to confirm or cancel
 */

import { computed, ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import Modal from '@/components/ui/Modal.vue'
import { ICON_SIZE } from '@/config/design'
import { Check, X } from 'lucide-vue-next'

interface Props {
  modelValue: boolean
  moduleLabel: string
  width: number
  height: number
  hasChangedSize: boolean
  hasChangedSplit: boolean
  hasChangedColumns: boolean
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm'): void
  (e: 'cancel'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Refs
const confirmButtonRef = ref<HTMLButtonElement | null>(null)

// Keyboard handler
const handleKeydown = (e: KeyboardEvent) => {
  if (!props.modelValue) return
  if (e.key === 'Escape') {
    handleCancel()
  } else if (e.key === 'Enter') {
    handleConfirm()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

// Auto-focus on confirm button when modal opens
watch(() => props.modelValue, (visible) => {
  if (visible) {
    nextTick(() => {
      confirmButtonRef.value?.focus()
    })
  }
})

// Computed
const hasAnyChanges = computed(() => {
  return props.hasChangedSize || props.hasChangedSplit || props.hasChangedColumns
})

// Actions
function handleConfirm() {
  emit('confirm')
  emit('update:modelValue', false)
}

function handleCancel() {
  emit('cancel')
  emit('update:modelValue', false)
}
</script>

<template>
  <Modal
    :model-value="modelValue"
    size="sm"
    :show-close="true"
    :close-on-backdrop="true"
    :close-on-esc="true"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <!-- Header -->
    <template #header>
      <h3 class="modal-title">Uložit jako výchozí?</h3>
    </template>

    <!-- Body -->
    <div class="modal-content">
      <p class="description">
        Chcete uložit tuto velikost a rozložení jako výchozí pro modul
        <strong class="module-name">{{ moduleLabel }}</strong>?
      </p>

      <!-- Changes List -->
      <div v-if="hasAnyChanges" class="changes-list">
        <div v-if="hasChangedSize" class="change-item">
          <Check :size="ICON_SIZE.SMALL" class="check-icon" />
          <span>Velikost okna: {{ width }} × {{ height }} px</span>
        </div>
        <div v-if="hasChangedSplit" class="change-item">
          <Check :size="ICON_SIZE.SMALL" class="check-icon" />
          <span>Pozice spliterů</span>
        </div>
        <div v-if="hasChangedColumns" class="change-item">
          <Check :size="ICON_SIZE.SMALL" class="check-icon" />
          <span>Šířky sloupců</span>
        </div>
      </div>

      <!-- No Changes -->
      <div v-else class="no-changes">
        <p class="info-text">Žádné změny k uložení.</p>
      </div>
    </div>

    <!-- Footer -->
    <template #footer>
      <div class="footer-actions">
        <button class="icon-btn icon-btn-cancel" @click="handleCancel" title="Zrušit (Escape)">
          <X :size="ICON_SIZE.STANDARD" />
        </button>
        <button
          ref="confirmButtonRef"
          class="icon-btn icon-btn-confirm"
          :disabled="!hasAnyChanges"
          @click="handleConfirm"
          title="Uložit (Enter)"
        >
          <Check :size="ICON_SIZE.STANDARD" />
        </button>
      </div>
    </template>
  </Modal>
</template>

<style scoped>
/* === MODAL CONTENT === */

.modal-title {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
}

.description {
  font-size: var(--text-base);
  color: var(--text-body);
  line-height: 1.5;
  margin: 0;
}

.module-name {
  color: var(--brand);
  font-weight: var(--font-semibold);
}

/* === CHANGES LIST === */
.changes-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--bg-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.change-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-body);
}

.check-icon {
  color: var(--status-ok);
  flex-shrink: 0;
}

/* === NO CHANGES === */
.no-changes {
  padding: var(--space-4);
  background: var(--bg-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  text-align: center;
}

.info-text {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin: 0;
}

/* === FOOTER ACTIONS === */
.footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

/* === ICON BUTTONS === */

</style>
