<script setup lang="ts">
import { ref, watch } from 'vue'
import * as partsApi from '@/api/parts'
import type { Part } from '@/types/part'

interface Props {
  modelValue: Part | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: Part | null]
  'select': [part: Part]
  'enter': []
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const inputText = ref('')
const isOpen = ref(false)
const activeIdx = ref(-1)
const filtered = ref<Part[]>([])
const loading = ref(false)

let searchTimer: ReturnType<typeof setTimeout>

// Sync input text when modelValue changes externally
watch(
  () => props.modelValue,
  (part) => {
    inputText.value = part ? (part.article_number ?? part.part_number) : ''
  },
  { immediate: true },
)

function displayLabel(part: Part): string {
  return part.article_number ?? part.part_number
}

function open() {
  isOpen.value = true
}

function close() {
  isOpen.value = false
  activeIdx.value = -1
}

function select(part: Part) {
  inputText.value = displayLabel(part)
  emit('update:modelValue', part)
  emit('select', part)
  close()
}

function clearSelection() {
  inputText.value = ''
  filtered.value = []
  emit('update:modelValue', null)
  close()
}

async function search(q: string) {
  loading.value = true
  try {
    const res = await partsApi.getAll({ search: q, limit: 10 })
    filtered.value = res.parts
    activeIdx.value = -1
    if (filtered.value.length > 0) open()
  } catch {
    filtered.value = []
  } finally {
    loading.value = false
  }
}

function onInput(e: Event) {
  const val = (e.target as HTMLInputElement).value
  inputText.value = val
  // Clear selected part when user types
  if (props.modelValue !== null) emit('update:modelValue', null)

  clearTimeout(searchTimer)
  if (!val.trim()) {
    filtered.value = []
    close()
    return
  }
  // Show loading hint immediately
  isOpen.value = true
  searchTimer = setTimeout(() => search(val.trim()), 300)
}

function onFocus() {
  if (filtered.value.length > 0) open()
}

function onBlur() {
  setTimeout(() => {
    if (props.modelValue) {
      inputText.value = displayLabel(props.modelValue)
    } else if (inputText.value && !props.modelValue) {
      // Text entered but no part selected → reset
      inputText.value = ''
    }
    close()
  }, 150)
}

function onKeydown(e: KeyboardEvent) {
  const len = filtered.value.length

  if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (!isOpen.value) {
      if (filtered.value.length > 0) open()
      return
    }
    activeIdx.value = Math.min(activeIdx.value + 1, len - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIdx.value = Math.max(activeIdx.value - 1, -1)
  } else if (e.key === 'Enter') {
    if (isOpen.value && activeIdx.value >= 0) {
      e.preventDefault()
      e.stopPropagation()
      const part = filtered.value[activeIdx.value]
      if (part) select(part)
    } else if (!isOpen.value) {
      // Dropdown closed → propagate Enter to parent (confirm add-row)
      e.preventDefault()
      emit('enter')
    }
  } else if (e.key === 'Escape') {
    e.preventDefault()
    if (props.modelValue) {
      inputText.value = displayLabel(props.modelValue)
    } else {
      inputText.value = ''
    }
    close()
    ;(e.target as HTMLElement).blur()
  } else if ((e.key === 'Delete' || e.key === 'Backspace') && inputText.value === '') {
    clearSelection()
  }
}

defineExpose({ focus: () => inputRef.value?.focus() })
</script>

<template>
  <!-- intentional: custom part combobox with API search -->
  <div class="pc-wrap">
    <input
      ref="inputRef"
      class="pc-inp"
      type="text"
      autocomplete="off"
      :value="inputText"
      placeholder="Hledat díl (article / název)…"
      data-testid="part-combo-input"
      @input="onInput"
      @focus="onFocus"
      @blur="onBlur"
      @keydown="onKeydown"
    />

    <!-- Dropdown -->
    <div v-if="isOpen" class="pc-dd">
      <!-- Loading -->
      <div v-if="loading" class="pc-dd-msg">Hledám…</div>

      <!-- Results -->
      <template v-else-if="filtered.length > 0">
        <div
          v-for="(part, i) in filtered"
          :key="part.id"
          class="pc-opt"
          :class="{ hi: i === activeIdx }"
          :data-testid="`part-combo-option-${part.id}`"
          @mousedown.prevent="select(part)"
          @mouseover="activeIdx = i"
        >
          <span class="pc-opt-code">{{ part.article_number ?? part.part_number }}</span>
          <span class="pc-opt-name">{{ part.name ?? '—' }}</span>
        </div>
      </template>

      <!-- Empty -->
      <div v-else class="pc-dd-msg">Žádný výsledek</div>
    </div>
  </div>
</template>

<style scoped>
.pc-wrap {
  position: relative;
  width: 100%;
}

.pc-inp {
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
.pc-inp::placeholder { color: var(--t4); font-size: var(--fsm); }
.pc-inp:focus { border-color: var(--b3); background: var(--b2); color: var(--t1); }
.pc-inp:focus-visible { outline: 2px solid rgba(255, 255, 255, 0.5); outline-offset: 2px; }

/* ─── Dropdown ─── */
.pc-dd {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 280px;
  background: var(--raised);
  border: 1px solid var(--b3);
  border-radius: var(--r);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);
  z-index: 500;
  padding: 4px;
}

.pc-opt {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 5px 8px;
  border-radius: var(--rs);
  cursor: pointer;
  transition: background 50ms var(--ease), color 50ms var(--ease);
}
.pc-opt:hover,
.pc-opt.hi { background: var(--b2); }

.pc-opt-code {
  font-family: var(--font);
  font-size: var(--fs);
  color: var(--t1);
  white-space: nowrap;
  flex-shrink: 0;
}
.pc-opt-name {
  font-size: var(--fsm);
  color: var(--t4);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pc-dd-msg {
  padding: 8px 10px;
  font-size: var(--fsm);
  color: var(--t4);
  font-style: italic;
}

input::selection { background: transparent; }
</style>
