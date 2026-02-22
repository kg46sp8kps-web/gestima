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
  gap: 6px;
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
  border: 1px solid var(--b2);
  border-radius: var(--r);
  color: var(--t1);
  cursor: pointer;
  transition: all 100ms cubic-bezier(0,0,0.2,1);
}

.quick-btn:hover {
  background: var(--b1);
  border-color: var(--b3);
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
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  box-shadow: 0 12px 40px rgba(0,0,0,0.7);
  padding: 4px;
  z-index: 10003;
}

.selector-header {
  padding: 6px var(--pad);
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.selector-option {
  display: block;
  width: 100%;
  padding: 6px var(--pad);
  background: transparent;
  border: none;
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  text-align: left;
  cursor: pointer;
  transition: background 100ms;
}

.selector-option:hover {
  background: var(--b1);
}

.selector-divider {
  height: 1px;
  background: var(--b2);
  margin: 4px 0;
}

.selector-reset {
  display: block;
  width: 100%;
  padding: 6px var(--pad);
  background: transparent;
  border: none;
  border-radius: var(--rs);
  color: var(--err);
  font-size: var(--fs);
  text-align: left;
  cursor: pointer;
  transition: background 100ms;
}

.selector-reset:hover {
  background: rgba(248,113,113,0.15);
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
