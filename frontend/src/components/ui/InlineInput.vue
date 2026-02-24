<script setup lang="ts">
defineOptions({ inheritAttrs: false })

interface Props {
  modelValue: string | number | null
  numeric?: boolean
  ghost?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  numeric: false,
  ghost: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number | null]
}>()

function onInput(e: Event) {
  const val = (e.target as HTMLInputElement).value
  if (props.numeric) {
    const n = Number(val)
    emit('update:modelValue', val === '' ? null : isNaN(n) ? null : n)
  } else {
    emit('update:modelValue', val === '' ? null : val)
  }
}
</script>

<template>
  <input
    v-bind="$attrs"
    :value="modelValue ?? ''"
    :class="ghost ? 'ii-ghost' : 'ii'"
    @input="onInput"
  />
</template>

<style scoped>
/* ─── Standard (.ei pattern) ─── */
.ii {
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t2);
  font-size: var(--fs);
  font-family: var(--font);
  padding: 2px 4px;
  outline: none;
  transition: border-color 120ms var(--ease), background 120ms var(--ease), color 120ms var(--ease);
}
.ii::placeholder { color: var(--t4); }
.ii:focus { border-color: var(--b3); background: rgba(255,255,255,0.07); color: var(--t1); }
.ii:focus-visible { outline: 2px solid rgba(255,255,255,0.5); outline-offset: 2px; }

/* ─── Ghost (.gi pattern) ─── */
.ii-ghost {
  background: transparent;
  border: none;
  border-bottom: 1px solid transparent;
  color: var(--t2);
  font-size: var(--fs);
  font-family: var(--font);
  padding: 0;
  margin: 0;
  line-height: inherit;
  outline: none;
  transition: border-bottom-color 120ms var(--ease), color 100ms var(--ease);
}
.ii-ghost::placeholder { color: var(--t4); }
.ii-ghost:hover { border-bottom-color: var(--b2); }
.ii-ghost:focus { border-bottom-color: var(--b3); color: var(--t1); }
</style>
