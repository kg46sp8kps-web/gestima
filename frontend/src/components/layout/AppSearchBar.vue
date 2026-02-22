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
  gap: 6px;
  min-width: 280px;
}

.search-icon {
  position: absolute;
  left: var(--pad);
  color: var(--t3);
  pointer-events: none;
}

.search-results {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  box-shadow: 0 8px 24px rgba(0,0,0,0.6);
  z-index: 10003;
  max-height: 300px;
  overflow-y: auto;
}

.search-result-item {
  display: block;
  width: 100%;
  padding: var(--pad) 12px;
  background: transparent;
  border: none;
  color: var(--t1);
  text-align: left;
  font-size: var(--fs);
  cursor: pointer;
  transition: all 100ms cubic-bezier(0,0,0.2,1);
}

.search-result-item:hover {
  background: var(--b1);
}
</style>
