<script setup lang="ts">
/**
 * Delete Operation Confirmation Modal
 */

import type { Operation } from '@/types/operation'

interface Props {
  show: boolean
  operation: Operation | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'confirm': []
  'cancel': []
}>()

function handleConfirm() {
  emit('confirm')
}

function handleCancel() {
  emit('cancel')
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="modal-overlay" @click.self="handleCancel">
      <div class="modal-content">
        <h3>Smazat operaci?</h3>
        <p>Opravdu chcete smazat operaci <strong>{{ operation?.name }}</strong>?</p>
        <div class="modal-actions">
          <button class="btn-secondary" @click="handleCancel">Zrušit</button>
          <button class="btn-danger" @click="handleConfirm">Smazat</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-surface);
  padding: var(--space-6);
  border-radius: var(--radius-xl);
  max-width: 400px;
  width: 90%;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.modal-content h3 {
  margin: 0 0 var(--space-4) 0;
  font-size: var(--text-xl);
  color: var(--text-primary);
}

.modal-content p {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.5;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  margin-top: var(--space-6);
}

.btn-secondary,
.btn-danger {
  padding: var(--space-2) var(--space-4);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-secondary {
  background: var(--bg-surface);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

.btn-secondary:hover {
  background: var(--state-hover);
}

.btn-danger {
  background: var(--color-danger-subtle, #fee2e2);
  color: var(--color-danger, #dc2626);
}

.btn-danger:hover {
  background: var(--color-danger-subtle-hover, #fecaca);
}
</style>
