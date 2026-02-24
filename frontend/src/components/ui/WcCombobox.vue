<script setup lang="ts">
import { ref, watch } from 'vue'
import type { WorkCenter } from '@/types/work-center'

interface Props {
  modelValue: number | null
  options: WorkCenter[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const inputText = ref('')
const isOpen = ref(false)
const activeIdx = ref(-1)
const filtered = ref<WorkCenter[]>([])

watch(
  () => props.modelValue,
  (id) => {
    const wc = id != null ? props.options.find((w) => w.id === id) : null
    inputText.value = wc ? wc.name : ''
  },
  { immediate: true },
)

watch(
  () => props.options,
  () => {
    const wc = props.modelValue != null ? props.options.find((w) => w.id === props.modelValue) : null
    inputText.value = wc ? wc.name : inputText.value
  },
)

function buildFiltered() {
  const q = inputText.value.trim().toLowerCase()
  filtered.value = q ? props.options.filter((w) => w.name.toLowerCase().includes(q)) : [...props.options]
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

function select(wc: WorkCenter) {
  inputText.value = wc.name
  emit('update:modelValue', wc.id)
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
    // Vrátit text na naposledy platné WC jméno
    const wc = props.modelValue != null ? props.options.find((w) => w.id === props.modelValue) : null
    if (wc) {
      inputText.value = wc.name
    } else if (inputText.value === '') {
      // Uživatel smazal text → emit null
      emit('update:modelValue', null)
    } else {
      // Text neodpovídá žádnému WC → vrátit poslední platnou hodnotu
      inputText.value = wc ? (wc as WorkCenter).name : ''
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
    const wc = filtered.value[activeIdx.value]
    if (wc) select(wc)
  } else if (e.key === 'Escape') {
    e.preventDefault()
    const wc = props.modelValue != null ? props.options.find((w) => w.id === props.modelValue) : null
    inputText.value = wc ? wc.name : ''
    close()
    ;(e.target as HTMLElement).blur()
  } else if (e.key === 'Delete' || e.key === 'Backspace') {
    if (inputText.value === '') {
      clearSelection()
    }
  }
}

defineExpose({ focus: () => inputRef.value?.focus() })
</script>

<template>
  <div class="wc-wrap">
    <input
      ref="inputRef"
      v-select-on-focus
      class="wc-inp"
      type="text"
      autocomplete="off"
      :value="inputText"
      placeholder="Pracoviště…"
      data-testid="wc-combo-input"
      @input="onInput"
      @focus="onFocus"
      @blur="onBlur"
      @keydown="onKeydown"
    />
    <div v-if="isOpen" class="wc-dd">
      <div v-if="!filtered.length" class="wc-dd-empty">Žádné pracoviště</div>
      <div
        v-for="(wc, i) in filtered"
        :key="wc.id"
        class="wc-opt"
        :class="{ hi: i === activeIdx }"
        :data-testid="`wc-combo-option-${wc.id}`"
        @mousedown.prevent="select(wc)"
        @mouseover="activeIdx = i"
      >
        {{ wc.name }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.wc-wrap {
  position: relative;
}

.wc-inp {
  background: var(--b1);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t2);
  font-family: var(--font);
  font-size: var(--fs);
  padding: 3px 7px;
  outline: none;
  width: 100%;
  transition: border-color 80ms var(--ease), background 80ms var(--ease), color 80ms var(--ease);
}

.wc-inp::placeholder {
  color: var(--t4);
  font-size: var(--fsm);
}

.wc-inp:focus {
  border-color: var(--b3);
  background: var(--b2);
  color: var(--t1);
}

.wc-inp:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.5);
  outline-offset: 2px;
}

/* ─── Dropdown ─── */
.wc-dd {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 210px;
  background: var(--raised);
  border: 1px solid var(--b3);
  border-radius: var(--r);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);
  z-index: 500;
  padding: 4px;
}

.wc-opt {
  display: flex;
  align-items: center;
  padding: 5px 8px;
  font-family: var(--font);
  font-size: var(--fs);
  color: var(--t2);
  border-radius: var(--rs);
  cursor: pointer;
  transition: background 50ms var(--ease), color 50ms var(--ease);
}

.wc-opt:hover,
.wc-opt.hi {
  background: var(--b2);
  color: var(--t1);
}

.wc-dd-empty {
  padding: 8px 10px;
  font-size: var(--fsm);
  color: var(--t4);
  font-style: italic;
}

/* Invisible selection — value overwritten by typing without visible highlight */
input::selection {
  background: transparent;
}
</style>
