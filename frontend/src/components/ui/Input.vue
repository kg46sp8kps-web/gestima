<template>
  <div class="input-wrapper">
    <label v-if="label" class="input-label">
      {{ label }}
      <span v-if="required" class="input-required">*</span>
    </label>

    <input
      ref="inputRef"
      v-select-on-focus
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :readonly="readonly"
      :class="inputClasses"
      @input="handleInput"
      @focus="handleFocus"
      @blur="handleBlur"
    />

    <span v-if="error" class="input-error">{{ error }}</span>
    <span v-else-if="hint" class="input-hint">{{ hint }}</span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

interface Props {
  modelValue: string | number;
  label?: string;
  type?: 'text' | 'number' | 'email' | 'password' | 'tel';
  placeholder?: string;
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  error?: string;
  hint?: string;
  mono?: boolean;
  editingState?: 'self' | 'other' | null;
}

const props = withDefaults(defineProps<Props>(), {
  type: 'text',
  disabled: false,
  readonly: false,
  required: false,
  mono: false,
  editingState: null
});

const emit = defineEmits<{
  'update:modelValue': [value: string | number];
  focus: [event: FocusEvent];
  blur: [event: FocusEvent];
}>();

const inputRef = ref<HTMLInputElement | null>(null);
const isFocused = ref(false);

const inputClasses = computed(() => [
  'input',
  {
    'input-mono': props.mono,
    'input-error-state': props.error,
    'input-disabled': props.disabled,
    'editing-self': props.editingState === 'self',
    'editing-other': props.editingState === 'other'
  }
]);

const handleInput = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const value = props.type === 'number' ? Number(target.value) : target.value;
  emit('update:modelValue', value);
};

const handleFocus = (event: FocusEvent) => {
  isFocused.value = true;
  emit('focus', event);
};

const handleBlur = (event: FocusEvent) => {
  isFocused.value = false;
  emit('blur', event);
};

// Expose for parent access
defineExpose({
  focus: () => inputRef.value?.focus(),
  blur: () => inputRef.value?.blur(),
  select: () => inputRef.value?.select()
});
</script>

<style scoped>
/* === INPUT WRAPPER === */
.input-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

/* === LABEL === */
.input-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-body);
}

.input-required {
  color: var(--color-danger);
  margin-left: var(--space-1);
}

/* === INPUT (Refined & Subtle) === */
.input {
  padding: var(--space-2) var(--space-3);
  background: var(--bg-input);
  border: 1px solid var(--border-default); /* Subtle border */
  border-radius: var(--radius-md);
  color: var(--text-body);
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  transition: var(--transition-fast);
  width: 100%;
}

.input:hover:not(:disabled):not(:readonly) {
  border-color: var(--border-strong);
}

/* FOCUS STATE (MODRÁ!) */
.input:focus {
  outline: none;
  background: var(--state-focus-bg);
  border-color: var(--state-focus-border);
  box-shadow: none;
}

/* MONOSPACE (for precision data) */
.input-mono {
  font-family: var(--font-mono);
}

/* ERROR STATE */
.input-error-state {
  border-color: var(--color-danger);
}

.input-error-state:focus {
  border-color: var(--color-danger);
  background: var(--palette-danger-light);
}

/* DISABLED STATE */
.input-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--bg-surface);
}

/* READONLY STATE */
.input:read-only {
  background: var(--bg-surface);
  cursor: default;
}

/* COLLABORATIVE EDITING STATES */
.editing-self {
  background: var(--state-editing-self);
  border-color: var(--color-info);
}

.editing-other {
  background: var(--state-editing-other);
  border-color: var(--color-primary);
}

/* === REMOVE NUMBER INPUT ARROWS (NEVER!) === */
input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

input[type="number"] {
  -moz-appearance: textfield;
}

/* === HIDE SELECTION HIGHLIGHT (click = select all, but invisible) === */
.input::selection {
  background: transparent;
  color: inherit;
}

/* === MESSAGES === */
.input-error {
  font-size: var(--text-sm);
  color: var(--color-danger);
  margin-top: calc(-1 * var(--space-1));
}

.input-hint {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-top: calc(-1 * var(--space-1));
}
</style>
