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
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: 8px;
  padding: 20px;
  width: 400px;
  box-shadow: 0 12px 40px rgba(0,0,0,0.7);
}

.modal h3 {
  margin: 0 0 12px 0;
  color: var(--t1);
  font-size: 16px;
}

.input-layout-name {
  width: 100%;
  padding: var(--pad);
  background: var(--base);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  color: var(--t1);
  font-size: var(--fs);
  margin-bottom: 12px;
  transition: all 100ms cubic-bezier(0,0,0.2,1);
}

.input-layout-name:focus {
  outline: none;
  border-color: var(--red);
}

.modal-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}

.save-btn,
.cancel-btn {
  padding: 6px 12px;
  border-radius: var(--r);
  font-size: var(--fs);
  font-weight: 500;
  cursor: pointer;
  transition: all 100ms cubic-bezier(0,0,0.2,1);
}

.save-btn {
  background: var(--red);
  color: white;
  border: none;
}

.save-btn:hover {
  opacity: 0.9;
}

.cancel-btn {
  background: transparent;
  color: var(--t1);
  border: 1px solid var(--b2);
}

.cancel-btn:hover {
  background: var(--b1);
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
