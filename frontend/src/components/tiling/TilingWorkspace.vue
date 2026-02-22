<script setup lang="ts">
/**
 * TilingWorkspace — Main workspace container
 * Replaces WindowsView.vue
 *
 * Renders the active workspace component based on workspaceStore.activeWorkspace.
 * Full-screen workspaces: TimeVision, MasterAdmin
 * Split-pane workspaces: Part, Manufacturing, Quotes, Partners, Materials, Files, Accounting
 */

import { ref, defineAsyncComponent, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useWorkspaceStore } from '@/stores/workspace'
import type { WorkspaceType } from '@/types/workspace'

import CncBackground from './CncBackground.vue'
import BootSequence from './BootSequence.vue'
import FabButton from './FabButton.vue'

// Workspace components — lazy loaded
const PartWorkspace = defineAsyncComponent(() => import('./PartWorkspace.vue'))

// Standalone split-pane modules (render their own list+detail)
const QuotesListModule = defineAsyncComponent(() => import('@/components/modules/QuotesListModule.vue'))
const PartnersListModule = defineAsyncComponent(() => import('@/components/modules/PartnersListModule.vue'))
const MaterialItemsListModule = defineAsyncComponent(() => import('@/components/modules/materials/MaterialItemsListModule.vue'))
const FileManagerModule = defineAsyncComponent(() => import('@/components/modules/files/FileManagerModule.vue'))
const AccountingModule = defineAsyncComponent(() => import('@/components/modules/AccountingModule.vue'))

// Full-screen modules
const MasterAdminModule = defineAsyncComponent(() => import('@/components/modules/MasterAdminModule.vue'))
const TimeVisionModule = defineAsyncComponent(() => import('@/components/modules/TimeVisionModule.vue'))

const workspaceStore = useWorkspaceStore()
const router = useRouter()
const route = useRoute()

// Boot sequence state
const showBoot = ref(true)
function handleBootDone() {
  showBoot.value = false
}

// FAB workspace switch handler
function handleFabSwitch(workspace: WorkspaceType) {
  if (route.path !== '/workspace') {
    router.push('/workspace')
  }
  workspaceStore.switchWorkspace(workspace)
}

// Keyboard shortcuts for layout presets (⌘1-4)
function handleKeydown(e: KeyboardEvent) {
  if (!e.metaKey && !e.ctrlKey) return

  switch (e.key) {
    case '1':
      e.preventDefault()
      workspaceStore.setLayoutPreset('standard')
      break
    case '2':
      e.preventDefault()
      workspaceStore.setLayoutPreset('comparison')
      break
    case '3':
      e.preventDefault()
      workspaceStore.setLayoutPreset('horizontal')
      break
    case '4':
      e.preventDefault()
      workspaceStore.setLayoutPreset('complete')
      break
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)

  // Auto-load default view
  if (workspaceStore.defaultViewId) {
    const defaultView = workspaceStore.savedViews.find(v => v.id === workspaceStore.defaultViewId)
    if (defaultView) {
      workspaceStore.loadView(workspaceStore.defaultViewId)
    }
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <!-- Boot Sequence -->
  <BootSequence :show="showBoot" @done="handleBootDone" />

  <!-- CNC Background -->
  <CncBackground />

  <!-- Main Workspace Container -->
  <div class="tiling-workspace" :class="{ booting: showBoot }">
    <!-- Part Workspace (standard + manufacturing reuse) -->
    <PartWorkspace
      v-if="workspaceStore.activeWorkspace === 'part'"
      linkingGroup="red"
    />

    <PartWorkspace
      v-else-if="workspaceStore.activeWorkspace === 'manufacturing'"
      linkingGroup="red"
    />

    <!-- Standalone split-pane workspaces -->
    <QuotesListModule
      v-else-if="workspaceStore.activeWorkspace === 'quotes'"
    />

    <PartnersListModule
      v-else-if="workspaceStore.activeWorkspace === 'partners'"
    />

    <MaterialItemsListModule
      v-else-if="workspaceStore.activeWorkspace === 'materials'"
    />

    <FileManagerModule
      v-else-if="workspaceStore.activeWorkspace === 'files'"
    />

    <AccountingModule
      v-else-if="workspaceStore.activeWorkspace === 'accounting'"
    />

    <!-- Full-screen workspaces -->
    <MasterAdminModule
      v-else-if="workspaceStore.activeWorkspace === 'admin'"
    />

    <TimeVisionModule
      v-else-if="workspaceStore.activeWorkspace === 'timevision'"
    />
  </div>

  <!-- FAB Button -->
  <FabButton v-if="!showBoot" @switch-workspace="handleFabSwitch" />
</template>

<style scoped>
.tiling-workspace {
  position: absolute;
  top: 36px;    /* Compact header */
  bottom: 22px; /* Compact status bar */
  left: 0;
  right: 0;
  overflow: hidden;
  z-index: 1;
  padding: 3px;  /* Panel gap around tiles */
  transition: opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1), transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.tiling-workspace.booting {
  opacity: 0;
  transform: scale(0.985);
}
</style>
