<script setup lang="ts">
/**
 * TypeAheadSelect.vue — Reusable type-ahead/autocomplete select component
 *
 * BUILDING BLOCK (L-039): Generic, reusable across the app.
 * Full keyboard support — NO MOUSE required for complete workflow.
 *
 * Usage:
 *   <TypeAheadSelect
 *     :options="[{ value: 1, label: 'Option A' }]"
 *     :model-value="selectedId"
 *     placeholder="Search..."
 *     @select="handleSelect"
 *     @cancel="handleCancel"
 *   />
 *
 * Keyboard:
 *   - Type to filter options
 *   - ArrowDown/ArrowUp to navigate
 *   - Enter to select highlighted option
 *   - Escape to cancel (restores original value)
 *   - Tab to select highlighted + move focus
 */
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'

export interface TypeAheadOption {
  value: string | number
  label: string
}

const props = withDefaults(defineProps<{
  options: TypeAheadOption[]
  modelValue?: string | number | null
  placeholder?: string
  maxVisible?: number
}>(), {
  modelValue: null,
  placeholder: 'Hledat...',
  maxVisible: 8
})

const emit = defineEmits<{
  select: [value: string | number | null]
  cancel: []
}>()

// ── State ───────────────────────────────────────────────
const query = ref('')
const highlightIndex = ref(0)
const isOpen = ref(true)
const inputRef = ref<HTMLInputElement | null>(null)
const listRef = ref<HTMLElement | null>(null)

// ── Computed ────────────────────────────────────────────
const filtered = computed(() => {
  if (!query.value.trim()) return props.options
  const q = query.value.toLowerCase().trim()
  return props.options.filter(opt =>
    opt.label.toLowerCase().includes(q)
  )
})

const visibleOptions = computed(() =>
  filtered.value.slice(0, props.maxVisible)
)

const currentLabel = computed(() => {
  if (props.modelValue === null || props.modelValue === undefined) return ''
  const opt = props.options.find(o => o.value === props.modelValue)
  return opt?.label ?? ''
})

// ── Methods ─────────────────────────────────────────────
function selectOption(opt: TypeAheadOption) {
  emit('select', opt.value)
}

function selectHighlighted() {
  const opt = visibleOptions.value[highlightIndex.value]
  if (opt) {
    selectOption(opt)
  } else if (filtered.value.length === 0) {
    // No match — emit null to clear
    emit('select', null)
  }
}

function handleKeydown(e: KeyboardEvent) {
  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault()
      highlightIndex.value = Math.min(
        highlightIndex.value + 1,
        visibleOptions.value.length - 1
      )
      scrollToHighlighted()
      break
    case 'ArrowUp':
      e.preventDefault()
      highlightIndex.value = Math.max(highlightIndex.value - 1, 0)
      scrollToHighlighted()
      break
    case 'Enter':
      e.preventDefault()
      selectHighlighted()
      break
    case 'Tab':
      // Select current and let focus move naturally
      selectHighlighted()
      break
    case 'Escape':
      e.preventDefault()
      emit('cancel')
      break
  }
}

function scrollToHighlighted() {
  nextTick(() => {
    const el = listRef.value?.querySelector('.highlighted')
    if (el) {
      el.scrollIntoView({ block: 'nearest' })
    }
  })
}

// Reset highlight when filter changes
watch(query, () => {
  highlightIndex.value = 0
})

// Handle click outside to close
function handleClickOutside(e: MouseEvent) {
  const wrapper = inputRef.value?.closest('.typeahead-select')
  if (wrapper && !wrapper.contains(e.target as Node)) {
    emit('cancel')
  }
}

// ── Lifecycle ───────────────────────────────────────────
onMounted(() => {
  query.value = ''
  nextTick(() => {
    inputRef.value?.focus()
  })
  document.addEventListener('mousedown', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleClickOutside)
})
</script>

<template>
  <div class="typeahead-select">
    <input
      ref="inputRef"
      v-model="query"
      type="text"
      class="typeahead-input"
      :placeholder="currentLabel || placeholder"
      autocomplete="off"
      @keydown="handleKeydown"
    />
    <div v-if="isOpen" ref="listRef" class="typeahead-dropdown">
      <div
        v-for="(opt, idx) in visibleOptions"
        :key="String(opt.value)"
        class="typeahead-option"
        :class="{
          highlighted: idx === highlightIndex,
          selected: opt.value === modelValue
        }"
        @mousedown.prevent="selectOption(opt)"
        @mouseenter="highlightIndex = idx"
      >
        {{ opt.label }}
      </div>
      <div v-if="filtered.length === 0" class="typeahead-empty">
        Nic nenalezeno
      </div>
      <div v-if="filtered.length > maxVisible" class="typeahead-more">
        +{{ filtered.length - maxVisible }} dalších...
      </div>
    </div>
  </div>
</template>

<style scoped>
.typeahead-select {
  position: relative;
  width: 100%;
}

.typeahead-input {
  width: 100%;
  padding: 4px 6px;
  border: 1px solid var(--red);
  border-radius: 4px;
  font-size: var(--fs);
  background: var(--surface);
  color: var(--t2);
  outline: none;
  box-shadow: 0 0 0 2px var(--red-10);
}

.typeahead-input:focus {
  border-color: var(--red);
}

.typeahead-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 200;
  max-height: 240px;
  overflow-y: auto;
  background: rgba(0,0,0,0.7);
  border: 1px solid var(--b2);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  margin-top: 2px;
}

.typeahead-option {
  padding: 6px 10px;
  font-size: var(--fs);
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.typeahead-option:hover,
.typeahead-option.highlighted {
  background: var(--raised);
}

.typeahead-option.selected {
  font-weight: 600;
  color: var(--red);
}

.typeahead-option.highlighted.selected {
  background: var(--b1);
}

.typeahead-empty {
  padding: 8px 10px;
  font-size: var(--fs);
  color: var(--t3);
  text-align: center;
  font-style: italic;
}

.typeahead-more {
  padding: 4px 10px;
  font-size: var(--fs);
  color: var(--t3);
  text-align: center;
  border-top: 1px solid var(--b2);
}
</style>
