<template>
  <Modal
    v-model="isOpen"
    :title="title"
    size="sm"
    :close-on-backdrop="false"
    :close-on-esc="!loading"
  >
    <!-- Message -->
    <div class="confirm-message">
      {{ message }}
    </div>

    <!-- Footer with actions -->
    <template #footer>
      <Button
        variant="ghost"
        :disabled="loading"
        @click="handleCancel"
      >
        {{ cancelText }}
      </Button>

      <Button
        :variant="variant"
        :loading="loading"
        @click="handleConfirm"
      >
        {{ confirmText }}
      </Button>
    </template>
  </Modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import Modal from './Modal.vue';
import Button from './Button.vue';

interface Props {
  modelValue: boolean;
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'primary' | 'danger';
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Potvrdit akci',
  confirmText: 'Potvrdit',
  cancelText: 'Zrušit',
  variant: 'danger',
  loading: false
});

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  confirm: [];
  cancel: [];
}>();

const isOpen = ref(props.modelValue);

watch(() => props.modelValue, (value) => {
  isOpen.value = value;
});

watch(isOpen, (value) => {
  emit('update:modelValue', value);
});

const handleConfirm = () => {
  emit('confirm');
};

const handleCancel = () => {
  isOpen.value = false;
  emit('cancel');
};
</script>

<style scoped>
.confirm-message {
  font-size: var(--text-base);
  color: var(--text-base);
  line-height: var(--leading-relaxed);
  margin: var(--space-2) 0;
}
</style>
