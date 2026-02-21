<script setup lang="ts">
/**
 * WindowsView - Main view with floating windows
 */

import { onMounted } from 'vue'
import { useWindowsStore } from '@/stores/windows'
import FloatingWindow from '@/components/windows/FloatingWindow.vue'
import { LayoutGrid } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

// Module components (lazy loaded)
import { defineAsyncComponent } from 'vue'

const PartMainModule = defineAsyncComponent(() => import('@/components/modules/PartMainModule.vue'))
const PartPricingModule = defineAsyncComponent(() => import('@/components/modules/PartPricingModule.vue'))
const PartTechnologyModule = defineAsyncComponent(() => import('@/components/modules/PartTechnologyModule.vue'))
const PartDrawingWindow = defineAsyncComponent(() => import('@/components/modules/parts/PartDrawingWindow.vue'))
const BatchSetsModule = defineAsyncComponent(() => import('@/components/modules/BatchSetsModule.vue'))
const PartnersListModule = defineAsyncComponent(() => import('@/components/modules/PartnersListModule.vue'))
const QuotesListModule = defineAsyncComponent(() => import('@/components/modules/QuotesListModule.vue'))
const QuoteFromRequestModule = defineAsyncComponent(() => import('@/components/modules/QuoteFromRequestModule.vue'))
const ManufacturingItemsModule = defineAsyncComponent(() => import('@/components/modules/manufacturing/ManufacturingItemsModule.vue'))
const MaterialItemsListModule = defineAsyncComponent(() => import('@/components/modules/materials/MaterialItemsListModule.vue'))
const MasterAdminModule = defineAsyncComponent(() => import('@/components/modules/MasterAdminModule.vue'))
const AccountingModule = defineAsyncComponent(() => import('@/components/modules/AccountingModule.vue'))
const TimeVisionModule = defineAsyncComponent(() => import('@/components/modules/TimeVisionModule.vue'))
const FileManagerModule = defineAsyncComponent(() => import('@/components/modules/files/FileManagerModule.vue'))

const store = useWindowsStore()

// Get component for module
function getModuleComponent(module: string) {
  switch (module) {
    case 'part-main': return PartMainModule
    case 'part-pricing': return PartPricingModule
    case 'part-technology': return PartTechnologyModule
    case 'part-drawing': return PartDrawingWindow
    case 'batch-sets': return BatchSetsModule
    case 'partners-list': return PartnersListModule
    case 'quotes-list': return QuotesListModule
    case 'quote-from-request': return QuoteFromRequestModule
    case 'manufacturing-items': return ManufacturingItemsModule
    case 'material-items-list': return MaterialItemsListModule
    case 'master-admin': return MasterAdminModule
    case 'accounting': return AccountingModule
    case 'time-vision': return TimeVisionModule
    case 'file-manager': return FileManagerModule
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
          :windowId="win.id"
          :linkingGroup="win.linkingGroup"
          :windowRole="win.windowRole"
          :windowTitle="win.title"
        />
      </FloatingWindow>
    </div>

    <!-- Empty State -->
    <Transition name="fade">
      <div v-if="store.windows.length === 0" class="empty-state">
        <LayoutGrid :size="ICON_SIZE.HERO" :stroke-width="1" class="empty-icon" />
        <h2>No Windows Open</h2>
        <p>Use search or menu to open modules</p>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.windows-view {
  position: absolute;
  top: 56px; /* Right after fixed header */
  bottom: 32px; /* Above fixed footer */
  left: 0;
  right: 0;
  background: var(--bg-base);
  overflow: hidden;
}

.windows-container {
  position: relative;
  width: 100%;
  height: 100%;
}

/* Empty State */

.empty-icon {
  margin-bottom: var(--space-5);
  opacity: 0.3;
  color: var(--text-tertiary);
}

/* Empty state transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-slow) var(--ease);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

</style>
