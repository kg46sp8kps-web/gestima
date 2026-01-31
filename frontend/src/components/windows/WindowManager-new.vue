<script setup lang="ts">
/**
 * WindowManager - Clean minimal toolbar
 * Open modules, arrange windows, save/load views
 */

import { ref, type Component } from 'vue'
import { useWindowsStore, type WindowModule } from '@/stores/windows'
import {
  Package,
  DollarSign,
  Settings,
  Box,
  ClipboardList,
  Save,
  X,
  Star,
  Grid3x3,
  Maximize2
} from 'lucide-vue-next'

const store = useWindowsStore()

// Modules with Lucide icons
const modules: Array<{ value: WindowModule; label: string; icon: Component }> = [
  { value: 'part-main', label: 'Part', icon: Package },
  { value: 'part-pricing', label: 'Pricing', icon: DollarSign },
  { value: 'part-operations', label: 'Operations', icon: Settings },
  { value: 'part-material', label: 'Material', icon: Box },
  { value: 'batch-sets', label: 'Batches', icon: ClipboardList }
]

function openModule(module: WindowModule, label: string) {
  store.openWindow(module, label)
}

function handleArrange() {
  store.arrangeWindows('grid')
}

function handleCloseAll() {
  if (confirm('Close all windows?')) {
    store.closeAllWindows()
  }
}
</script>

<template>
  <div class="window-manager">
    <!-- Module Buttons -->
    <div class="manager-section">
      <button
        v-for="mod in modules"
        :key="mod.value"
        @click="openModule(mod.value, mod.label)"
        class="module-btn"
        :title="`Open ${mod.label}`"
      >
        <component :is="mod.icon" :size="16" :stroke-width="2" />
        <span>{{ mod.label }}</span>
      </button>
    </div>

    <!-- Actions -->
    <div class="manager-section actions">
      <button
        @click="handleArrange"
        class="action-btn"
        title="Arrange windows (grid)"
        :disabled="store.openWindows.length === 0"
      >
        <Grid3x3 :size="16" :stroke-width="2" />
      </button>
      <button
        @click="handleCloseAll"
        class="action-btn danger"
        title="Close all windows"
        :disabled="store.openWindows.length === 0"
      >
        <X :size="16" :stroke-width="2" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.window-manager {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-4);
  gap: var(--space-4);
  box-shadow: var(--shadow-sm);
}

.manager-section {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.manager-section.actions {
  margin-left: auto;
}

/* Module Buttons */
.module-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.module-btn:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
}

.module-btn:active {
  transform: translateY(1px);
}

/* Action Buttons */
.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.action-btn:hover:not(:disabled) {
  background: var(--state-hover);
  border-color: var(--border-strong);
}

.action-btn.danger:hover:not(:disabled) {
  background: var(--color-danger);
  border-color: var(--color-danger);
  color: white;
}

.action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
