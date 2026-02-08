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
  gap: var(--space-2);
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
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.action-btn:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
  color: var(--text-primary);
}

.arrange-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 140px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: var(--space-1);
  z-index: 10003;
}

.arrange-option {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  width: 100%;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
  text-align: left;
}

.arrange-option:hover {
  background: var(--state-hover);
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
