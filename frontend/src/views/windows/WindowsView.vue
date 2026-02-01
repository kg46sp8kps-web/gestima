<script setup lang="ts">
/**
 * WindowsView - Main view with floating windows
 */

import { onMounted } from 'vue'
import { useWindowsStore } from '@/stores/windows'
import FloatingWindow from '@/components/windows/FloatingWindow.vue'
import Taskbar from '@/components/windows/Taskbar.vue'
import { LayoutGrid } from 'lucide-vue-next'

// Module components (lazy loaded)
import { defineAsyncComponent } from 'vue'

const PartMainModule = defineAsyncComponent(() => import('@/components/modules/PartMainModule.vue'))
const PartPricingModule = defineAsyncComponent(() => import('@/components/modules/PartPricingModule.vue'))
const PartOperationsModule = defineAsyncComponent(() => import('@/components/modules/PartOperationsModule.vue'))
const PartMaterialModule = defineAsyncComponent(() => import('@/components/modules/PartMaterialModule.vue'))
const PartDrawingWindow = defineAsyncComponent(() => import('@/components/modules/parts/PartDrawingWindow.vue'))
const BatchSetsModule = defineAsyncComponent(() => import('@/components/modules/BatchSetsModule.vue'))
const PartnersListModule = defineAsyncComponent(() => import('@/components/modules/PartnersListModule.vue'))
const QuotesListModule = defineAsyncComponent(() => import('@/components/modules/QuotesListModule.vue'))

const store = useWindowsStore()

// Get component for module
function getModuleComponent(module: string) {
  switch (module) {
    case 'part-main': return PartMainModule
    case 'part-pricing': return PartPricingModule
    case 'part-operations': return PartOperationsModule
    case 'part-material': return PartMaterialModule
    case 'part-drawing': return PartDrawingWindow
    case 'batch-sets': return BatchSetsModule
    case 'partners-list': return PartnersListModule
    case 'quotes-list': return QuotesListModule
    default: return null
  }
}

// Auto-load default layout on mount
onMounted(() => {
  if (store.defaultLayoutId) {
    const defaultView = store.savedViews.find(v => v.id === store.defaultLayoutId)
    if (defaultView) {
      store.loadView(store.defaultLayoutId)
    }
  }
})
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
        <component
          :is="getModuleComponent(win.module)"
          :linkingGroup="win.linkingGroup"
          :windowTitle="win.title"
        />
      </FloatingWindow>
    </div>

    <!-- Empty State -->
    <div v-if="store.windows.length === 0" class="empty-state">
      <LayoutGrid :size="64" :stroke-width="1" class="empty-icon" />
      <h2>No Windows Open</h2>
      <p>Use the toolbar above to open modules</p>
    </div>

    <!-- Bottom Taskbar -->
    <Taskbar />
  </div>
</template>

<style scoped>
.windows-view {
  width: 100%;
  min-height: calc(100vh - 120px); /* Account for header + footer */
  overflow: auto; /* Allow scrolling */
  background: var(--bg-base);
  position: relative;
  margin: var(--space-4); /* Pevné hranice vlevo, vpravo, nahoře */
  margin-bottom: 0; /* Footer bude fixní */
  padding-bottom: 40px; /* Space for taskbar */
}

.windows-container {
  position: relative;
  min-height: 600px; /* Minimum height for windows */
  width: 100%;
  height: 100%;
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
  margin-bottom: var(--space-5);
  opacity: 0.3;
  color: var(--text-tertiary);
}

.empty-state h2 {
  font-size: var(--text-5xl);
  margin: 0 0 0.5rem 0;
  color: var(--text-primary);
}

.empty-state p {
  font-size: var(--text-2xl);
  margin: 0;
}
</style>
