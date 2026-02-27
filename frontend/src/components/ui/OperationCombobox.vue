<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Operation } from '@/types/operation'

interface Props {
  modelValue: number | null
  options: Operation[]
  dataTestid?: string
  disabled?: boolean
  metaById?: Record<number, string>
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const inputText = ref('')
const isOpen = ref(false)
const activeIdx = ref(-1)
const filtered = ref<Operation[]>([])

function opLabel(op: Operation): string {
  return `${String(op.seq).padStart(2, '0')} · ${op.name}`
}

watch(
  () => props.modelValue,
  (id) => {
    const op = id != null ? props.options.find((o) => o.id === id) : null
    inputText.value = op ? opLabel(op) : ''
  },
  { immediate: true },
)

watch(
  () => props.options,
  () => {
    const op = props.modelValue != null ? props.options.find((o) => o.id === props.modelValue) : null
    inputText.value = op ? opLabel(op) : inputText.value
  },
)

function buildFiltered() {
  const q = inputText.value.trim().toLowerCase()
  filtered.value = q
    ? props.options.filter((o) => {
        const seq = String(o.seq).padStart(2, '0')
        return o.name.toLowerCase().includes(q) || seq.includes(q)
      })
    : [...props.options]
}

function open() {
  buildFiltered()
  isOpen.value = true
  activeIdx.value = -1
}

function close() {
  isOpen.value = false
  activeIdx.value = -1
}

function select(op: Operation) {
  inputText.value = opLabel(op)
  emit('update:modelValue', op.id)
  close()
}

function clearSelection() {
  inputText.value = ''
  emit('update:modelValue', null)
}

function onInput(e: Event) {
  inputText.value = (e.target as HTMLInputElement).value
  buildFiltered()
  isOpen.value = true
  activeIdx.value = -1
}

function onFocus() {
  open()
}

function onBlur() {
  setTimeout(() => {
    const op = props.modelValue != null ? props.options.find((o) => o.id === props.modelValue) : null
    if (op) {
      inputText.value = opLabel(op)
    } else if (inputText.value === '') {
      emit('update:modelValue', null)
    } else {
      inputText.value = op ? opLabel(op) : ''
    }
    close()
  }, 150)
}

function onKeydown(e: KeyboardEvent) {
  const len = filtered.value.length
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (!isOpen.value) {
      open()
      return
    }
    activeIdx.value = Math.min(activeIdx.value + 1, len - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIdx.value = Math.max(activeIdx.value - 1, -1)
  } else if (e.key === 'Enter' && isOpen.value && activeIdx.value >= 0) {
    e.preventDefault()
    e.stopPropagation()
    const op = filtered.value[activeIdx.value]
    if (op) select(op)
  } else if (e.key === 'Escape') {
    e.preventDefault()
    const op = props.modelValue != null ? props.options.find((o) => o.id === props.modelValue) : null
    inputText.value = op ? opLabel(op) : ''
    close()
    ;(e.target as HTMLElement).blur()
  } else if (e.key === 'Delete' || e.key === 'Backspace') {
    if (inputText.value === '') clearSelection()
  }
}

defineExpose({ focus: () => inputRef.value?.focus() })
</script>

<template>
  <div class="op-wrap">
    <input
      ref="inputRef"
      v-select-on-focus
      class="op-inp"
      type="text"
      autocomplete="off"
      :value="inputText"
      :data-testid="dataTestid || 'op-combo-input'"
      :disabled="disabled"
      @input="onInput"
      @focus="onFocus"
      @blur="onBlur"
      @keydown="onKeydown"
    />
    <div v-if="isOpen" class="op-dd">
      <div v-if="!filtered.length" class="op-dd-empty">Žádná operace</div>
      <div
        v-for="(op, i) in filtered"
        :key="op.id"
        class="op-opt"
        :class="{ hi: i === activeIdx }"
        :data-testid="`op-combo-option-${op.id}`"
        @mousedown.prevent="select(op)"
        @mouseover="activeIdx = i"
      >
        <span class="op-opt-main">{{ opLabel(op) }}</span>
        <span v-if="metaById?.[op.id]" class="op-opt-meta">{{ metaById[op.id] }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.op-wrap {
  position: relative;
  width: 100%;
}
.op-wrap:focus-within {
  z-index: 700;
}

.op-inp {
  background: var(--b1);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t2);
  font-family: var(--font);
  font-size: var(--fsm);
  padding: 3px 7px;
  outline: none;
  width: 100%;
  height: 24px;
  transition: border-color 80ms var(--ease), background 80ms var(--ease), color 80ms var(--ease);
}

.op-inp::placeholder {
  color: var(--t4);
  font-size: var(--fsm);
}

.op-inp:focus {
  border-color: var(--b3);
  background: var(--b2);
  color: var(--t1);
}

.op-inp:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.5);
  outline-offset: 2px;
}

.op-dd {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 220px;
  background: var(--raised);
  border: 1px solid var(--b3);
  border-radius: var(--r);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);
  z-index: 800;
  padding: 4px;
}

.op-opt {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 5px 8px;
  font-family: var(--font);
  font-size: var(--fs);
  color: var(--t2);
  border-radius: var(--rs);
  cursor: pointer;
  transition: background 50ms var(--ease), color 50ms var(--ease);
}

.op-opt-main {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.op-opt-meta {
  font-size: var(--fss);
  color: var(--t4);
  white-space: nowrap;
}

.op-opt:hover,
.op-opt.hi {
  background: var(--b2);
  color: var(--t1);
}

.op-dd-empty {
  padding: 8px 10px;
  font-size: var(--fsm);
  color: var(--t4);
  font-style: italic;
}

input::selection {
  background: transparent;
}
</style>
