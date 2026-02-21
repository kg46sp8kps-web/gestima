<script setup lang="ts">
import { ref, watch } from 'vue'

interface Props {
  show: boolean
  title: string
  defaultName: string
}

interface Emits {
  (e: 'close'): void
  (e: 'confirm', name: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const layoutName = ref('')

watch(() => props.show, (newVal) => {
  if (newVal) {
    layoutName.value = props.defaultName
  }
})

function handleConfirm() {
  emit('confirm', layoutName.value)
}

function handleKeyup(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    handleConfirm()
  }
}
</script>

<template>
  <Transition name="backdrop-fade">
    <div v-if="show" class="modal-overlay" @click="emit('close')">
      <div class="modal" @click.stop>
        <h3>{{ title }}</h3>
        <input
          v-model="layoutName"
          type="text"
          placeholder="Layout name..."
          class="input-layout-name"
          @keyup="handleKeyup"
        />
        <div class="modal-actions">
          <button @click="handleConfirm" class="save-btn">Save</button>
          <button @click="emit('close')" class="cancel-btn">Cancel</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>

.modal {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  width: 400px;
  box-shadow: var(--shadow-xl);
}

.modal h3 {
  margin: 0 0 var(--space-4) 0;
  color: var(--text-primary);
  font-size: var(--text-xl);
}

.input-layout-name {
  width: 100%;
  padding: var(--space-3);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-base);
  margin-bottom: var(--space-4);
  transition: all var(--duration-fast) var(--ease-out);
}

.input-layout-name:focus {
  outline: none;
  border-color: var(--primary-color);
}

.modal-actions {
  display: flex;
  gap: var(--space-2);
  justify-content: flex-end;
}

.save-btn,
.cancel-btn {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.save-btn {
  background: var(--primary-color);
  color: white;
  border: none;
}

.save-btn:hover {
  opacity: 0.9;
}

.cancel-btn {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

.cancel-btn:hover {
  background: var(--state-hover);
}

.backdrop-fade-enter-active,
.backdrop-fade-leave-active {
  transition: opacity 0.3s ease;
}

.backdrop-fade-enter-from,
.backdrop-fade-leave-to {
  opacity: 0;
}
</style>
