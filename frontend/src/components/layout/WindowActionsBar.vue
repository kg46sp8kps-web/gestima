<script setup lang="ts">
import { ref } from 'vue'
import { LayoutGrid, AlignHorizontalSpaceAround, AlignVerticalSpaceAround, X } from 'lucide-vue-next'
import Tooltip from '@/components/ui/Tooltip.vue'
import { ICON_SIZE } from '@/config/design'

interface Emits {
  (e: 'arrange', mode: 'grid' | 'horizontal' | 'vertical'): void
  (e: 'close-all'): void
}

const emit = defineEmits<Emits>()

const showArrangeDropdown = ref(false)

function toggleDropdown() {
  showArrangeDropdown.value = !showArrangeDropdown.value
}

function arrange(mode: 'grid' | 'horizontal' | 'vertical') {
  emit('arrange', mode)
  showArrangeDropdown.value = false
}
</script>

<template>
  <div class="window-actions">
    <!-- Arrange Dropdown -->
    <div class="action-wrapper">
      <Tooltip text="Arrange windows" :delay="750">
        <button class="action-btn" @click="toggleDropdown">
          <LayoutGrid :size="ICON_SIZE.SMALL" />
        </button>
      </Tooltip>
      <Transition name="dropdown-fade">
        <div v-if="showArrangeDropdown" class="arrange-dropdown" @click.stop>
          <button class="arrange-option" @click="arrange('grid')">
            <LayoutGrid :size="ICON_SIZE.SMALL" />
            <span>Grid</span>
          </button>
          <button class="arrange-option" @click="arrange('horizontal')">
            <AlignHorizontalSpaceAround :size="ICON_SIZE.SMALL" />
            <span>Horizontal</span>
          </button>
          <button class="arrange-option" @click="arrange('vertical')">
            <AlignVerticalSpaceAround :size="ICON_SIZE.SMALL" />
            <span>Vertical</span>
          </button>
        </div>
      </Transition>
    </div>

    <!-- Close All -->
    <Tooltip text="Close all windows" :delay="750">
      <button class="action-btn" @click="emit('close-all')">
        <X :size="ICON_SIZE.SMALL" />
      </button>
    </Tooltip>
  </div>
</template>

<style scoped>
.window-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

.action-wrapper {
  position: relative;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  color: var(--t3);
  cursor: pointer;
  transition: all 100ms cubic-bezier(0,0,0.2,1);
}

.action-btn:hover {
  background: var(--b1);
  border-color: var(--b3);
  color: var(--t1);
}

.arrange-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 140px;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  box-shadow: 0 8px 24px rgba(0,0,0,0.6);
  padding: 4px;
  z-index: 10003;
}

.arrange-option {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px var(--pad);
  width: 100%;
  background: transparent;
  border: none;
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  cursor: pointer;
  transition: background 100ms cubic-bezier(0,0,0.2,1);
  text-align: left;
}

.arrange-option:hover {
  background: var(--b1);
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
