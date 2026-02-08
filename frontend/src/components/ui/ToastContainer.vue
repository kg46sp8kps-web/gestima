<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="toast in ui.toasts"
          :key="toast.id"
          :class="['toast', `toast-${toast.type}`]"
          data-testid="toast"
          @click="ui.removeToast(toast.id)"
        >
          <div class="toast-message">{{ toast.message }}</div>
          <button class="toast-close" @click.stop="ui.removeToast(toast.id)">
            <X :size="ICON_SIZE.SMALL" :stroke-width="2" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useUiStore } from '@/stores/ui'
import { X } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

const ui = useUiStore()
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 80px;
  right: 1rem;
  z-index: 10003;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 300px;
  max-width: 500px;
  padding: 1rem;
  background-color: #1f2937;
  color: #f9fafb;
  border-radius: 8px;
  border-left: 4px solid;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  pointer-events: all;
  cursor: pointer;
  transition: all 0.3s ease;
}

.toast:hover {
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
  transform: translateY(-2px);
}

/* Border colors by type */
.toast-success {
  border-left-color: var(--color-success);
}

.toast-error {
  border-left-color: var(--color-danger);
}

.toast-warning {
  border-left-color: var(--color-warning);
}

.toast-info {
  border-left-color: var(--color-info);
}

.toast-message {
  flex: 1;
  color: #f9fafb;
  font-size: var(--text-xl);
  line-height: 1.4;
}

.toast-close {
  flex-shrink: 0;
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
}

.toast-close:hover {
  color: #f9fafb;
}

/* Toast animations */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100px) scale(0.8);
}

.toast-move {
  transition: transform 0.3s ease;
}
</style>
