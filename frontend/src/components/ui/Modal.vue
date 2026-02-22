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
  padding: 12px;
}

/* === MODAL === */
.modal {
  background: var(--raised);
  border: 1px solid var(--b3);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.6);
  width: 90%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Sizes */
.modal-sm { max-width: 460px; }
.modal-md { max-width: 600px; }
.modal-lg { max-width: 800px; }
.modal-xl { max-width: 1200px; }

/* === HEADER === */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--pad) 12px;
  border-bottom: 1px solid var(--b2);
  flex-shrink: 0;
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--t1);
  margin: 0;
}

.modal-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--r);
  color: var(--t3);
  cursor: pointer;
  transition: all 100ms var(--ease);
  flex-shrink: 0;
}

.modal-close:hover {
  background: var(--b1);
  color: var(--t1);
  border-color: var(--b2);
}

/* === BODY === */
.modal-body {
  padding: 12px;
  overflow-y: auto;
  flex: 1;
}

/* === FOOTER === */
.modal-footer {
  padding: var(--pad) 12px;
  border-top: 1px solid var(--b2);
  display: flex;
  justify-content: flex-end;
  gap: var(--pad);
  flex-shrink: 0;
}

/* === TRANSITIONS === */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 150ms cubic-bezier(0,0,0.2,1);
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-slide-enter-active,
.modal-slide-leave-active {
  transition: transform 150ms cubic-bezier(0,0,0.2,1),
              opacity 150ms cubic-bezier(0,0,0.2,1);
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
