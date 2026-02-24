<script setup lang="ts">
defineOptions({ inheritAttrs: false })

interface Props {
  modelValue: string | number | null
  label?: string
  type?: 'text' | 'number' | 'password' | 'email' | 'search'
  placeholder?: string
  error?: string
  hint?: string
  disabled?: boolean
  required?: boolean
  autofocus?: boolean
  min?: number
  max?: number
  step?: number
  testid?: string
  bare?: boolean
}

withDefaults(defineProps<Props>(), {
  type: 'text',
  disabled: false,
  required: false,
  autofocus: false,
  testid: 'input',
  bare: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number | null]
  'enter': []
  'blur': [event: FocusEvent]
}>()

function onInput(e: Event) {
  const target = e.target as HTMLInputElement
  const raw = target.value
  emit('update:modelValue', raw === '' ? null : raw)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') emit('enter')
}
</script>

<template>
  <!-- bare mode: just the input, no wrapper — for toolbar search bars -->
  <input
    v-if="bare"
    v-bind="$attrs"
    :value="modelValue ?? ''"
    :type="type"
    :placeholder="placeholder"
    :disabled="disabled"
    :autofocus="autofocus"
    :min="min"
    :max="max"
    :step="step"
    :class="['input-ctrl', {}]"
    :data-testid="testid"
    v-select-on-focus
    @input="onInput"
    @keydown="onKeydown"
    @blur="$emit('blur', $event)"
  />
  <!-- full mode: with label, error, hint wrapper -->
  <div
    v-else
    v-bind="$attrs"
    class="input-field"
    :class="{ 'input-error': error, 'input-disabled': disabled }"
  >
    <label v-if="label" class="input-label">
      {{ label }}<span v-if="required" class="input-required">*</span>
    </label>
    <input
      :value="modelValue ?? ''"
      :type="type"
      :placeholder="placeholder"
      :disabled="disabled"
      :autofocus="autofocus"
      :min="min"
      :max="max"
      :step="step"
      :class="['input-ctrl', {}]"
      :data-testid="testid"
      v-select-on-focus
      @input="onInput"
      @keydown="onKeydown"
      @blur="$emit('blur', $event)"
    />
    <p v-if="error" class="input-hint input-hint-error">{{ error }}</p>
    <p v-else-if="hint" class="input-hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.input-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.input-label {
  font-size: var(--fsm);
  font-weight: 500;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  user-select: none;
}

.input-required {
  color: var(--warn);
  margin-left: 2px;
}

.input-ctrl {
  height: 28px;
  padding: 3px 6px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t2);
  font-size: var(--fs);
  font-family: var(--font);
  outline: none;
  transition: border-color 120ms var(--ease), background 120ms var(--ease), color 120ms var(--ease);
  width: 100%;
}
.input-ctrl::placeholder { color: var(--t4); }
.input-ctrl:focus {
  border-color: var(--b3);
  background: rgba(255,255,255,0.07);
  color: var(--t1);
}
.input-ctrl:focus-visible {
  outline: 2px solid rgba(255,255,255,0.5);
  outline-offset: 2px;
}


.input-error .input-ctrl {
  border-color: var(--warn);
}
.input-error .input-ctrl:focus {
  border-color: var(--warn);
}

.input-disabled .input-ctrl {
  opacity: 0.4;
  cursor: not-allowed;
}

.input-hint {
  font-size: var(--fsm);
  color: var(--t4);
}
.input-hint-error {
  color: var(--err);
}
</style>
