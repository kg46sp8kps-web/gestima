<script setup lang="ts">
/**
 * SaveModuleDefaultsModal - Confirm saving window size/layout as defaults
 * Shows changes summary and allows user to confirm or cancel
 */

import { computed } from 'vue'
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
      <button class="btn btn-secondary" @click="handleCancel">
        <X :size="ICON_SIZE.STANDARD" />
        <span>Zrušit</span>
      </button>
      <button
        class="btn btn-primary"
        :disabled="!hasAnyChanges"
        @click="handleConfirm"
      >
        <Check :size="ICON_SIZE.STANDARD" />
        <span>Uložit</span>
      </button>
    </template>
  </Modal>
</template>

<style scoped>
/* === MODAL CONTENT === */
.modal-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

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
  color: var(--palette-primary);
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
  color: var(--palette-success);
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

/* === BUTTONS === */
.btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.btn:focus-visible {
  outline: 2px solid var(--state-focus-border);
  outline-offset: 2px;
}

/* Primary Button */
.btn-primary {
  background: var(--palette-primary);
  color: white;
  border-color: var(--palette-primary);
}

.btn-primary:hover:not(:disabled) {
  background: var(--palette-primary-hover);
  border-color: var(--palette-primary-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  color: var(--text-body);
  border-color: var(--border-default);
}

.btn-secondary:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
}
</style>
