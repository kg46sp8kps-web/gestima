<script setup lang="ts">
/**
 * ModulePicker — dropdown to add/remove modules from a panel
 * Shows all available modules with checkmarks for active ones
 */

import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { MODULE_REGISTRY, MODULE_ORDER } from './modules/moduleRegistry'
import type { TileModuleId } from '@/types/workspace'
import { Plus, Check } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  activeModules: TileModuleId[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'add-module': [moduleId: TileModuleId]
  'remove-module': [moduleId: TileModuleId]
}>()

const isOpen = ref(false)
const pickerRef = ref<HTMLElement | null>(null)

const availableModules = computed(() =>
  MODULE_ORDER.map(id => ({
    ...MODULE_REGISTRY[id],
    active: props.activeModules.includes(id),
  }))
)

function toggle() {
  isOpen.value = !isOpen.value
}

function handleModuleClick(moduleId: TileModuleId, active: boolean) {
  if (active) {
    // Don't remove last module
    if (props.activeModules.length > 1) {
      emit('remove-module', moduleId)
    }
  } else {
    emit('add-module', moduleId)
  }
  isOpen.value = false
}

function handleClickOutside(e: MouseEvent) {
  if (pickerRef.value && !pickerRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('mousedown', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleClickOutside)
})
</script>

<template>
  <div ref="pickerRef" class="module-picker">
    <button
      class="picker-trigger"
      @click="toggle"
      title="Přidat modul"
      data-testid="module-picker-trigger"
    >
      <Plus :size="ICON_SIZE.SMALL" />
    </button>
    <div v-if="isOpen" class="picker-dropdown" data-testid="module-picker-dropdown">
      <button
        v-for="mod in availableModules"
        :key="mod.id"
        class="picker-item"
        :class="{ active: mod.active }"
        @click="handleModuleClick(mod.id, mod.active)"
        :data-testid="`picker-item-${mod.id}`"
      >
        <Check v-if="mod.active" :size="ICON_SIZE.SMALL" class="check-icon" />
        <span v-else class="check-placeholder" />
        <span class="picker-label">{{ mod.label }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.module-picker {
  position: relative;
}

.picker-trigger {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 2px;
  color: var(--t4);
  cursor: pointer;
  transition: all 0.08s;
}

.picker-trigger:hover {
  background: var(--b1);
  color: var(--t1);
}

.picker-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 50;
  min-width: 160px;
  padding: 4px;
  background: var(--raised);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  box-shadow: 0 12px 40px rgba(0,0,0,0.5);
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.picker-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  background: transparent;
  border: none;
  border-radius: var(--rs);
  color: var(--t3);
  font-size: var(--fs);
  cursor: pointer;
  transition: all 0.06s;
  text-align: left;
  font-family: inherit;
}

.picker-item:hover {
  background: var(--b1);
  color: var(--t1);
}

.picker-item.active {
  color: var(--t1);
}

.check-icon {
  color: var(--green);
  flex-shrink: 0;
}

.check-placeholder {
  width: 14px;
  flex-shrink: 0;
}

.picker-label {
  white-space: nowrap;
}
</style>
