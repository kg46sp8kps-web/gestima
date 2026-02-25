<script setup lang="ts">
defineOptions({ inheritAttrs: false })

interface Props {
  modelValue: string | null
  label?: string
  placeholder?: string
  error?: string
  hint?: string
  rows?: number
  disabled?: boolean
  required?: boolean
  testid?: string
}

withDefaults(defineProps<Props>(), {
  rows: 4,
  disabled: false,
  required: false,
  testid: 'textarea',
})

defineEmits<{
  'update:modelValue': [value: string | null]
  'blur': [event: FocusEvent]
}>()

function onInput(e: Event) {
  const target = e.target as HTMLTextAreaElement
  const raw = target.value
  return raw === '' ? null : raw
}
</script>

<template>
  <div
    v-bind="$attrs"
    class="textarea-field"
    :class="{ 'textarea-error': error, 'textarea-disabled': disabled }"
  >
    <label v-if="label" class="textarea-label">
      {{ label }}<span v-if="required" class="textarea-required">*</span>
    </label>
    <textarea
      :value="modelValue ?? ''"
      :placeholder="placeholder"
      :disabled="disabled"
      :rows="rows"
      :data-testid="testid"
      class="textarea-ctrl"
      @input="$emit('update:modelValue', onInput($event))"
      @blur="$emit('blur', $event)"
    />
    <p v-if="error" class="textarea-hint textarea-hint-error">{{ error }}</p>
    <p v-else-if="hint" class="textarea-hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.textarea-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.textarea-label {
  font-size: var(--fsm);
  font-weight: 500;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  user-select: none;
}

.textarea-required {
  color: var(--warn);
  margin-left: 2px;
}

.textarea-ctrl {
  padding: 6px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t2);
  font-size: var(--fs);
  font-family: var(--font);
  outline: none;
  resize: vertical;
  width: 100%;
  transition: border-color 120ms var(--ease), background 120ms var(--ease), color 120ms var(--ease);
}
.textarea-ctrl::placeholder { color: var(--t4); }
.textarea-ctrl:focus {
  border-color: var(--b3);
  background: rgba(255,255,255,0.07);
  color: var(--t1);
}
.textarea-ctrl:focus-visible {
  outline: 2px solid rgba(255,255,255,0.5);
  outline-offset: 2px;
}

.textarea-error .textarea-ctrl {
  border-color: var(--warn);
}

.textarea-disabled .textarea-ctrl {
  opacity: 0.4;
  cursor: not-allowed;
}

.textarea-hint {
  font-size: var(--fsm);
  color: var(--t4);
}
.textarea-hint-error {
  color: var(--err);
}
</style>
