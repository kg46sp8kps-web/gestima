<script setup lang="ts">
interface SelectOption {
  value: string | number | null
  label: string
}

interface Props {
  modelValue: string | number | null
  options: SelectOption[]
  label?: string
  placeholder?: string
  error?: string
  disabled?: boolean
  required?: boolean
}

withDefaults(defineProps<Props>(), {
  disabled: false,
  required: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number | null]
  'change': [value: string | number | null]
}>()

function onChange(e: Event) {
  const target = e.target as HTMLSelectElement
  const raw = target.value
  const parsed: string | number | null = raw === '' ? null : raw
  emit('update:modelValue', parsed)
  emit('change', parsed)
}
</script>

<template>
  <div class="select-field" :class="{ 'select-error': error, 'select-disabled': disabled }">
    <label v-if="label" class="select-label">
      {{ label }}<span v-if="required" class="select-required">*</span>
    </label>
    <div class="select-wrap">
      <select
        :value="modelValue ?? ''"
        :disabled="disabled"
        class="select-ctrl"
        data-testid="select"
        @change="onChange"
      >
        <option v-if="placeholder" value="">{{ placeholder }}</option>
        <option
          v-for="opt in options"
          :key="String(opt.value)"
          :value="opt.value ?? ''"
        >
          {{ opt.label }}
        </option>
      </select>
      <svg class="select-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </div>
    <p v-if="error" class="select-hint select-hint-error">{{ error }}</p>
  </div>
</template>

<style scoped>
.select-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.select-label {
  font-size: var(--fsl);
  font-weight: 500;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  user-select: none;
}

.select-required {
  color: var(--red);
  margin-left: 2px;
}

.select-wrap {
  position: relative;
}

.select-ctrl {
  width: 100%;
  height: 28px;
  padding: 0 28px 0 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  font-family: var(--font);
  outline: none;
  appearance: none;
  cursor: pointer;
  transition: border-color 120ms var(--ease);
}
.select-ctrl:focus {
  border-color: var(--b3);
}
.select-ctrl:focus-visible {
  outline: 2px solid rgba(255,255,255,0.5);
  outline-offset: 2px;
}
.select-ctrl option {
  background: var(--ground);
  color: var(--t1);
}

.select-arrow {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 12px;
  height: 12px;
  color: var(--t4);
  pointer-events: none;
}

.select-error .select-ctrl { border-color: var(--err); }
.select-disabled .select-ctrl { opacity: 0.5; cursor: not-allowed; }

.select-hint { font-size: var(--fsl); color: var(--t4); }
.select-hint-error { color: var(--err); }
</style>
