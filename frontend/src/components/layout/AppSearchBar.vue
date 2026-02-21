<script setup lang="ts">
import { ref, computed } from 'vue'
import { Search } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Module {
  value: string
  label: string
  icon: unknown
}

interface Props {
  modules: Module[]
}

interface Emits {
  (e: 'select', value: string, label: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const searchQuery = ref('')
const showDropdown = ref(false)

const filteredModules = computed(() => {
  if (!searchQuery.value) return props.modules
  const query = searchQuery.value.toLowerCase()
  return props.modules.filter(m => m.label.toLowerCase().includes(query))
})

function handleFocus() {
  showDropdown.value = true
}

function handleBlur() {
  setTimeout(() => {
    showDropdown.value = false
  }, 200)
}

function handleSelect(value: string, label: string) {
  emit('select', value, label)
  searchQuery.value = ''
  showDropdown.value = false
}
</script>

<template>
  <div class="search-container">
    <Search :size="ICON_SIZE.SMALL" class="search-icon" />
    <input
      v-model="searchQuery"
      type="text"
      placeholder="search modules"
      class="search-input"
      @focus="handleFocus"
      @blur="handleBlur"
    />
    <!-- Search results dropdown -->
    <div v-if="showDropdown && filteredModules.length > 0" class="search-results">
      <button
        v-for="mod in filteredModules"
        :key="mod.value"
        @click="handleSelect(mod.value, mod.label)"
        class="search-result-item"
      >
        {{ mod.label }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.search-container {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 280px;
}

.search-icon {
  position: absolute;
  left: var(--space-3);
  color: var(--text-secondary);
  pointer-events: none;
}

.search-results {
  position: absolute;
  top: calc(100% + var(--space-1));
  left: 0;
  right: 0;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: 10003;
  max-height: 300px;
  overflow-y: auto;
}

.search-result-item {
  display: block;
  width: 100%;
  padding: var(--space-3) var(--space-4);
  background: transparent;
  border: none;
  color: var(--text-primary);
  text-align: left;
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.search-result-item:hover {
  background: var(--state-hover);
}
</style>
