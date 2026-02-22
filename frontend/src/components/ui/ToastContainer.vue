<script setup lang="ts">
import { XIcon } from 'lucide-vue-next'
import { useUiStore } from '@/stores/ui'
import { ICON_SIZE_SM } from '@/config/design'

const ui = useUiStore()
</script>

<template>
  <Teleport to="body">
    <div class="toast-container" aria-live="polite">
      <TransitionGroup name="toast" tag="div" class="toast-list">
        <div
          v-for="toast in ui.toasts"
          :key="toast.id"
          :class="['toast', `toast-${toast.type}`]"
          role="alert"
        >
          <span class="toast-message">{{ toast.message }}</span>
          <button
            class="icon-btn icon-btn-sm"
            :aria-label="'Zavřít'"
            data-testid="toast-close"
            @click="ui.removeToast(toast.id)"
          >
            <XIcon :size="ICON_SIZE_SM" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9500;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.toast-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toast {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--raised);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  border-left-width: 3px;
  min-width: 280px;
  max-width: 420px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5);
  pointer-events: auto;
}

.toast-success { border-left-color: var(--ok); }
.toast-error   { border-left-color: var(--err); }
.toast-warning { border-left-color: var(--warn); }
.toast-info    { border-left-color: var(--b3); }

.toast-message {
  flex: 1;
  font-size: var(--fs);
  color: var(--t1);
  line-height: 1.4;
}
</style>

<style>
.toast-enter-active,
.toast-leave-active {
  transition: all 200ms var(--ease);
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(20px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
