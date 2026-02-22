<template>
  <div class="select-wrapper">
    <label v-if="label" class="select-label">
      {{ label }}
      <span v-if="required" class="select-required">*</span>
    </label>

    <div class="select-container">
      <select
        ref="selectRef"
        :value="modelValue"
        :disabled="disabled"
        :class="selectClasses"
        @change="handleChange"
        @focus="handleFocus"
        @blur="handleBlur"
      >
        <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
        <option
          v-for="option in options"
          :key="option.value"
          :value="option.value"
        >
          {{ option.label }}
        </option>
      </select>

      <span class="select-arrow">▼</span>
    </div>

    <span v-if="error" class="select-error">{{ error }}</span>
    <span v-else-if="hint" class="select-hint">{{ hint }}</span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

interface SelectOption {
  value: string | number;
  label: string;
}

interface Props {
  modelValue: string | number;
  label?: string;
  options: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  error?: string;
  hint?: string;
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  required: false
});

const emit = defineEmits<{
  'update:modelValue': [value: string | number];
  focus: [event: FocusEvent];
  blur: [event: FocusEvent];
  change: [value: string | number];
}>();

const selectRef = ref<HTMLSelectElement | null>(null);
const isFocused = ref(false);

const selectClasses = computed(() => [
  'select',
  {
    'select-error-state': props.error,
    'select-disabled': props.disabled
  }
]);

const handleChange = (event: Event) => {
  const target = event.target as HTMLSelectElement;
  const value = target.value;

  // Convert to number if original modelValue was number
  const convertedValue = typeof props.modelValue === 'number' ? Number(value) : value;

  emit('update:modelValue', convertedValue);
  emit('change', convertedValue);
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
  focus: () => selectRef.value?.focus(),
  blur: () => selectRef.value?.blur()
});
</script>

<style scoped>
/* === SELECT WRAPPER === */
.select-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* === LABEL === */
.select-label {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t2);
}

.select-required {
  color: var(--err);
  margin-left: 4px;
}

/* === SELECT CONTAINER === */
.select-container {
  position: relative;
  width: 100%;
}

/* === SELECT (Refined & Subtle) === */
.select {
  padding: 6px var(--pad);
  padding-right: 24px; /* Space for arrow */
  background: var(--ground);
  border: 1px solid var(--b2); /* Subtle border */
  border-radius: var(--r);
  color: var(--t2);
  font-family: var(--font);
  font-size: var(--fs);
  transition: all 100ms var(--ease);
  width: 100%;
  cursor: pointer;
  appearance: none; /* Remove default arrow */
}

.select:hover:not(:disabled) {
  border-color: var(--b3);
}

/* FOCUS STATE (MODRÁ!) */
.select:focus {
  outline: none;
  background: rgba(255,255,255,0.03);
  border-color: rgba(255,255,255,0.5);
  box-shadow: none;
}

/* ERROR STATE */
.select-error-state {
  border-color: var(--err);
}

.select-error-state:focus {
  border-color: var(--err);
  background: rgba(248,113,113,0.15);
}

/* DISABLED STATE */
.select-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--surface);
}

/* === CUSTOM ARROW === */
.select-arrow {
  position: absolute;
  right: var(--pad);
  top: 50%;
  transform: translateY(-50%);
  font-size: var(--fs);
  color: var(--t3);
  pointer-events: none;
  transition: all 100ms var(--ease);
}

.select:focus ~ .select-arrow {
  color: rgba(255,255,255,0.5);
}

.select-disabled ~ .select-arrow {
  opacity: 0.5;
}

/* === MESSAGES === */
.select-error {
  font-size: var(--fs);
  color: var(--err);
  margin-top: calc(-1 * 4px);
}

.select-hint {
  font-size: var(--fs);
  color: var(--t3);
  margin-top: calc(-1 * 4px);
}

/* === OPTION STYLING (limited browser support) === */
.select option {
  background: var(--surface);
  color: var(--t2);
  padding: 6px;
}

.select option:disabled {
  color: var(--t3);
}
</style>
