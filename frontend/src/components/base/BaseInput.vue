<script setup lang="ts">
/**
 * BaseInput - Form input with label, error, validation
 *
 * @example
 * <BaseInput
 *   v-model="name"
 *   label="Part Name"
 *   placeholder="Enter name..."
 *   :error="errors.name"
 *   required
 * />
 */

import { computed } from 'vue'

interface Props {
  modelValue?: string | number
  label?: string
  placeholder?: string
  error?: string
  type?: 'text' | 'number' | 'email' | 'password'
  disabled?: boolean
  required?: boolean
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'text',
  disabled: false,
  required: false,
  readonly: false
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
}>()

const hasError = computed(() => !!props.error)

function handleInput(event: Event) {
  const target = event.target as HTMLInputElement
  const value = props.type === 'number' ? parseFloat(target.value) || 0 : target.value
  emit('update:modelValue', value)
}
</script>

<template>
  <div class="base-input">
    <label v-if="label" class="base-input__label">
      {{ label }}
      <span v-if="required" class="required">*</span>
    </label>

    <input
      :value="modelValue"
      :type="type"
      :placeholder="placeholder"
      :disabled="disabled"
      :readonly="readonly"
      :class="{ 'has-error': hasError }"
      class="base-input__field"
      @input="handleInput"
    />

    <span v-if="error" class="base-input__error">{{ error }}</span>
  </div>
</template>

<style scoped>
.base-input {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.base-input__label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.required {
  color: var(--color-danger);
}

.base-input__field {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-base);
  font-family: var(--font-sans);
  color: var(--text-body);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  transition: var(--transition-fast);
}

.base-input__field:hover:not(:disabled) {
  border-color: var(--border-strong);
}

.base-input__field:focus {
  outline: none;
  background: var(--state-focus-bg);
  border-color: var(--state-focus-border);
}

.base-input__field.has-error {
  border-color: var(--color-danger);
}

.base-input__field:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.base-input__field:readonly {
  background: var(--bg-surface);
  cursor: default;
}

.base-input__error {
  font-size: var(--text-xs);
  color: var(--color-danger);
}

/* Remove number input arrows */
input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

input[type="number"] {
  -moz-appearance: textfield;
}
</style>
