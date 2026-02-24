<script setup lang="ts">
defineOptions({ inheritAttrs: false })

interface Props {
  modelValue?: string | number | boolean | null
  ghost?: boolean
  small?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  ghost: false,
  small: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

function onChange(e: Event) {
  emit('update:modelValue', (e.target as HTMLSelectElement).value)
}

function selClass(): string {
  if (props.ghost && props.small) return 'is-ghost-sm'
  if (props.ghost) return 'is-ghost'
  return 'is'
}
</script>

<template>
  <select
    v-bind="$attrs"
    :value="modelValue !== null && modelValue !== undefined ? String(modelValue) : ''"
    :class="selClass()"
    @change="onChange"
  >
    <slot />
  </select>
</template>

<style scoped>
/* ─── Standard (.ei-sel pattern) ─── */
.is {
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t2);
  font-size: var(--fs);
  font-family: var(--font);
  padding: 2px 4px;
  outline: none;
  cursor: pointer;
  transition: border-color 120ms var(--ease), background 120ms var(--ease), color 120ms var(--ease);
}
.is:focus { border-color: var(--b3); background: rgba(255,255,255,0.07); color: var(--t1); }
.is option { background: var(--ground); color: var(--t1); }

/* ─── Ghost (.gi-sel pattern) ─── */
.is-ghost {
  background: transparent;
  border: none;
  border-bottom: 1px solid transparent;
  color: var(--t4);
  font-size: var(--fs);
  font-family: var(--font);
  cursor: pointer;
  outline: none;
  appearance: none;
  -webkit-appearance: none;
  transition: border-bottom-color 120ms var(--ease), color 100ms var(--ease);
}
.is-ghost:hover { border-bottom-color: var(--b2); }
.is-ghost:focus { color: var(--t2); }
.is-ghost option { background: var(--ground); color: var(--t1); }

/* ─── Ghost small (.gi-sel-sm pattern) ─── */
.is-ghost-sm {
  background: transparent;
  border: none;
  border-bottom: 1px solid transparent;
  cursor: pointer;
  font-size: var(--fss);
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--t3);
  outline: none;
  appearance: none;
  -webkit-appearance: none;
  transition: color 100ms var(--ease);
}
.is-ghost-sm:focus { color: var(--t2); }
.is-ghost-sm option { background: var(--ground); color: var(--t1); }
</style>
