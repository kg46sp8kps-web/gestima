<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="modelValue"
        class="modal-backdrop"
        @click="handleBackdropClick"
      >
        <Transition name="modal-slide">
          <div
            v-if="modelValue"
            class="modal"
            :class="modalClasses"
            role="dialog"
            aria-modal="true"
          >
            <!-- Header -->
            <div v-if="$slots.header || title" class="modal-header">
              <slot name="header">
                <h3 class="modal-title">{{ title }}</h3>
              </slot>
              <button
                v-if="showClose"
                class="modal-close"
                @click="close"
                aria-label="Close modal"
              >
                <X :size="ICON_SIZE.STANDARD" :stroke-width="2" />
              </button>
            </div>

            <!-- Body -->
            <div class="modal-body">
              <slot></slot>
            </div>

            <!-- Footer -->
            <div v-if="$slots.footer" class="modal-footer">
              <slot name="footer"></slot>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { watch, onMounted, onUnmounted } from 'vue';
import { X } from 'lucide-vue-next';
import { ICON_SIZE } from '@/config/design';

interface Props {
  modelValue: boolean;
  title?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showClose?: boolean;
  closeOnBackdrop?: boolean;
  closeOnEsc?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
  showClose: true,
  closeOnBackdrop: true,
  closeOnEsc: true
});

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  close: [];
}>();

const modalClasses = [`modal-${props.size}`];

const close = () => {
  emit('update:modelValue', false);
  emit('close');
};

const handleBackdropClick = (event: MouseEvent) => {
  if (props.closeOnBackdrop && event.target === event.currentTarget) {
    close();
  }
};

const handleEscKey = (event: KeyboardEvent) => {
  if (props.closeOnEsc && event.key === 'Escape' && props.modelValue) {
    close();
  }
};

// Prevent body scroll when modal is open
watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    document.body.style.overflow = 'hidden';
  } else {
    document.body.style.overflow = '';
  }
});

onMounted(() => {
  document.addEventListener('keydown', handleEscKey);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscKey);
  document.body.style.overflow = '';
});
</script>

<style scoped>
/* === BACKDROP === */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--space-4);
}

/* === MODAL === */
.modal {
  background: var(--bg-raised);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 90%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Sizes */
.modal-sm { max-width: 400px; }
.modal-md { max-width: 600px; }
.modal-lg { max-width: 800px; }
.modal-xl { max-width: 1200px; }

/* === HEADER === */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-5);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.modal-title {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
}

.modal-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: var(--text-xl);
  cursor: pointer;
  transition: var(--transition-fast);
  flex-shrink: 0;
}

.modal-close:hover {
  background: var(--state-hover);
  color: var(--text-primary);
}

/* === BODY === */
.modal-body {
  padding: var(--space-5);
  overflow-y: auto;
  flex: 1;
}

/* === FOOTER === */
.modal-footer {
  padding: var(--space-5);
  border-top: 1px solid var(--border-default);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  flex-shrink: 0;
}

/* === TRANSITIONS === */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity var(--duration-normal) var(--ease-out);
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-slide-enter-active,
.modal-slide-leave-active {
  transition: transform var(--duration-normal) var(--ease-out),
              opacity var(--duration-normal) var(--ease-out);
}

.modal-slide-enter-from {
  transform: translateY(-20px);
  opacity: 0;
}

.modal-slide-leave-to {
  transform: translateY(20px);
  opacity: 0;
}
</style>
