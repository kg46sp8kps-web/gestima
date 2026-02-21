<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Package } from 'lucide-vue-next'
import Tooltip from '@/components/ui/Tooltip.vue'
import { ICON_SIZE } from '@/config/design'

interface Module {
  value: string
  label: string
  icon: unknown
}

interface CustomModule {
  value: string
  label: string
}

interface Props {
  quickModules: Module[]
  availableModules: Module[]
}

interface Emits {
  (e: 'open', value: string, label: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const customQuickModules = ref<Record<number, CustomModule | null>>({
  0: null,
  1: null,
  2: null,
  3: null,
  4: null
})

const showModuleSelector = ref<number | null>(null)

onMounted(() => {
  const saved = localStorage.getItem('gestima_custom_quick_modules')
  if (saved) {
    customQuickModules.value = JSON.parse(saved)
  }
})

function saveCustomModules() {
  localStorage.setItem('gestima_custom_quick_modules', JSON.stringify(customQuickModules.value))
}

function getEffectiveModule(slotIndex: number) {
  const custom = customQuickModules.value[slotIndex]
  if (custom) {
    const moduleWithIcon = props.availableModules.find(m => m.value === custom.value)
    return {
      value: custom.value,
      label: custom.label,
      icon: moduleWithIcon?.icon || Package
    }
  }
  return props.quickModules[slotIndex]
}

function handleClick(slotIndex: number) {
  const module = getEffectiveModule(slotIndex)
  if (module) {
    emit('open', module.value, module.label)
  }
}

function handleRightClick(event: MouseEvent, slotIndex: number) {
  event.preventDefault()
  showModuleSelector.value = slotIndex
}

function assignCustomModule(slotIndex: number, moduleValue: string, label: string) {
  customQuickModules.value[slotIndex] = { value: moduleValue, label }
  saveCustomModules()
  showModuleSelector.value = null
}

function resetToDefault(slotIndex: number) {
  customQuickModules.value[slotIndex] = null
  saveCustomModules()
  showModuleSelector.value = null
}

function closeSelector() {
  showModuleSelector.value = null
}
</script>

<template>
  <div class="quick-modules">
    <div
      v-for="(defaultMod, index) in quickModules"
      :key="index"
      class="quick-btn-wrapper"
    >
      <Tooltip :text="getEffectiveModule(index)?.label || ''" :delay="750">
        <button
          class="quick-btn"
          @click="handleClick(index)"
          @contextmenu="handleRightClick($event, index)"
        >
          <component :is="getEffectiveModule(index)?.icon || Package" :size="ICON_SIZE.SMALL" />
        </button>
      </Tooltip>

      <!-- Context Menu -->
      <Transition name="dropdown-fade">
        <div v-if="showModuleSelector === index" class="module-selector" @click.stop>
          <div class="selector-header">Choose Module</div>
          <button
            v-for="mod in availableModules"
            :key="mod.value"
            class="selector-option"
            @click="assignCustomModule(index, mod.value, mod.label)"
          >
            {{ mod.label }}
          </button>
          <div class="selector-divider"></div>
          <button class="selector-reset" @click="resetToDefault(index)">
            Reset to Default
          </button>
        </div>
      </Transition>
    </div>
  </div>

  <!-- Backdrop -->
  <div v-if="showModuleSelector !== null" class="selector-backdrop" @click="closeSelector"></div>
</template>

<style scoped>
.quick-modules {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.quick-btn-wrapper {
  position: relative;
}

.quick-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.quick-btn:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
  transform: scale(1.05);
}

.quick-btn:active {
  transform: scale(0.95);
}

.module-selector {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 160px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xl);
  padding: var(--space-1);
  z-index: 10003;
}

.selector-header {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.selector-option {
  display: block;
  width: 100%;
  padding: var(--space-2) var(--space-3);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-sm);
  text-align: left;
  cursor: pointer;
  transition: background var(--duration-fast);
}

.selector-option:hover {
  background: var(--state-hover);
}

.selector-divider {
  height: 1px;
  background: var(--border-default);
  margin: var(--space-1) 0;
}

.selector-reset {
  display: block;
  width: 100%;
  padding: var(--space-2) var(--space-3);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--color-danger);
  font-size: var(--text-sm);
  text-align: left;
  cursor: pointer;
  transition: background var(--duration-fast);
}

.selector-reset:hover {
  background: var(--palette-danger-light);
}

.selector-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10002;
  background: transparent;
}

.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: opacity 0.15s ease;
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
}
</style>
