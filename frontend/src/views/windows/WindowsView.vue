<script setup lang="ts">
/**
 * WindowsView - Main view with floating windows
 */

import { useWindowsStore } from '@/stores/windows'
import FloatingWindow from '@/components/windows/FloatingWindow.vue'

// Module components (lazy loaded)
import { defineAsyncComponent } from 'vue'

const PartsListModule = defineAsyncComponent(() => import('@/components/modules/PartsListModule.vue'))
const PartPricingModule = defineAsyncComponent(() => import('@/components/modules/PartPricingModule.vue'))
const PartOperationsModule = defineAsyncComponent(() => import('@/components/modules/PartOperationsModule.vue'))
const PartMaterialModule = defineAsyncComponent(() => import('@/components/modules/PartMaterialModule.vue'))
const BatchSetsModule = defineAsyncComponent(() => import('@/components/modules/BatchSetsModule.vue'))

const store = useWindowsStore()

// Get component for module
function getModuleComponent(module: string) {
  switch (module) {
    case 'parts-list': return PartsListModule
    case 'part-pricing': return PartPricingModule
    case 'part-operations': return PartOperationsModule
    case 'part-material': return PartMaterialModule
    case 'batch-sets': return BatchSetsModule
    default: return null
  }
}
</script>

<template>
  <div class="windows-view">
    <!-- Floating Windows -->
    <div class="windows-container">
      <FloatingWindow
        v-for="win in store.windows"
        :key="win.id"
        :window="win"
        v-show="!win.minimized"
      >
        <component :is="getModuleComponent(win.module)" />
      </FloatingWindow>
    </div>

    <!-- Empty State -->
    <div v-if="store.windows.length === 0" class="empty-state">
      <div class="empty-icon">🪟</div>
      <h2>No Windows Open</h2>
      <p>Use the menu (☰) to open modules</p>
    </div>
  </div>
</template>

<style scoped>
.windows-view {
  width: 100%;
  height: 100%;
  min-height: calc(100vh - 120px); /* Account for header + footer */
  overflow: hidden;
  background: var(--bg-primary);
  position: relative;
}

.windows-container {
  position: absolute;
  inset: 0;
}

/* Empty State */
.empty-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-state h2 {
  font-size: 1.5rem;
  margin: 0 0 0.5rem 0;
  color: var(--text-primary);
}

.empty-state p {
  font-size: 1rem;
  margin: 0;
}
</style>
