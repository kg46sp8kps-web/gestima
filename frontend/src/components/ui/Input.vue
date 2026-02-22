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
  gap: 6px;
}

/* === LABEL === */
.input-label {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t2);
}

.input-required {
  color: var(--err);
  margin-left: 4px;
}

/* === INPUT (Refined & Subtle) === */
.input {
  padding: 6px var(--pad);
  background: var(--ground);
  border: 1px solid var(--b2); /* Subtle border */
  border-radius: var(--r);
  color: var(--t2);
  font-family: var(--font);
  font-size: var(--fs);
  transition: all 100ms var(--ease);
  width: 100%;
}

.input:hover:not(:disabled):not(:readonly) {
  border-color: var(--b3);
}

/* FOCUS STATE (MODRÁ!) */
.input:focus {
  outline: none;
  background: rgba(255,255,255,0.03);
  border-color: rgba(255,255,255,0.5);
  box-shadow: none;
}

/* MONOSPACE (for precision data) */
.input-mono {
  font-family: var(--mono);
}

/* ERROR STATE */
.input-error-state {
  border-color: var(--err);
}

.input-error-state:focus {
  border-color: var(--err);
  background: rgba(248,113,113,0.15);
}

/* DISABLED STATE */
.input-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--surface);
}

/* READONLY STATE */
.input:read-only {
  background: var(--surface);
  cursor: default;
}

/* COLLABORATIVE EDITING STATES */
.editing-self {
  background: rgba(37,99,235,0.2);
  border-color: var(--t3);
}

.editing-other {
  background: var(--red-20);
  border-color: var(--red);
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
  font-size: var(--fs);
  color: var(--err);
  margin-top: calc(-1 * 4px);
}

.input-hint {
  font-size: var(--fs);
  color: var(--t3);
  margin-top: calc(-1 * 4px);
}
</style>
