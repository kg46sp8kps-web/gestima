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
          <div class="toast-icon">
            <CheckCircle2 v-if="toast.type === 'success'" :size="ICON_SIZE.STANDARD" :stroke-width="1.8" />
            <XCircle v-else-if="toast.type === 'error'" :size="ICON_SIZE.STANDARD" :stroke-width="1.8" />
            <AlertTriangle v-else-if="toast.type === 'warning'" :size="ICON_SIZE.STANDARD" :stroke-width="1.8" />
            <Info v-else :size="ICON_SIZE.STANDARD" :stroke-width="1.8" />
          </div>
          <div class="toast-content">
            <div v-if="toast.title" class="toast-title">{{ toast.title }}</div>
            <div class="toast-message">{{ toast.message }}</div>
          </div>
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
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from 'lucide-vue-next'
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
  gap: 6px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: var(--pad);
  min-width: 300px;
  max-width: 500px;
  padding: var(--pad) 12px;
  background: var(--raised);
  color: var(--t2);
  border-radius: 8px;
  border: 1px solid var(--b2);
  border-left: 3px solid var(--b3);
  box-shadow: 0 8px 24px rgba(0,0,0,0.6);
  pointer-events: all;
  cursor: pointer;
  transition: all 100ms var(--ease);
}

.toast:hover {
  box-shadow: 0 12px 40px rgba(0,0,0,0.7);
  transform: translateY(-1px);
}

/* Border-left colors by type */
.toast-success { border-left-color: var(--ok); }
.toast-error { border-left-color: var(--err); }
.toast-warning { border-left-color: var(--warn); }
.toast-info { border-left-color: var(--t3); }

/* Icon colors */
.toast-icon {
  flex-shrink: 0;
  margin-top: 1px;
  color: var(--t3);
}
.toast-success .toast-icon { color: var(--ok); }
.toast-error .toast-icon { color: var(--err); }
.toast-warning .toast-icon { color: var(--warn); }

.toast-content {
  flex: 1;
  min-width: 0;
}

.toast-title {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
  line-height: 1.3;
}

.toast-message {
  font-size: var(--fs);
  color: var(--t3);
  line-height: 1.4;
}

.toast-close {
  flex-shrink: 0;
  background: none;
  border: none;
  color: var(--t4);
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 100ms var(--ease);
}

.toast-close:hover {
  color: var(--t1);
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
