<script setup lang="ts">
/**
 * AppHeader - Coordinator component
 * Workspace-based navigation with WorkspaceSwitcher + LayoutPresetSelector
 */

import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useWorkspaceStore } from '@/stores/workspace'
import { Menu, X } from 'lucide-vue-next'
import ManageLayoutsModal from '@/components/modals/ManageLayoutsModal.vue'
import AppMainMenu from './AppMainMenu.vue'
// FavoriteLayoutsBar removed from compact header — functionality accessible via menu
import SaveLayoutDialog from './SaveLayoutDialog.vue'
import AppLogo from './AppLogo.vue'
import WorkspaceSwitcher from '@/components/tiling/WorkspaceSwitcher.vue'
import LayoutPresetSelector from '@/components/tiling/LayoutPresetSelector.vue'
import Tooltip from '@/components/ui/Tooltip.vue'
import { alert } from '@/composables/useDialog'
import { ICON_SIZE } from '@/config/design'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const workspaceStore = useWorkspaceStore()

const showMenu = ref(false)
const showSaveDialog = ref(false)
const showSaveAsDialog = ref(false)
const showManageLayoutsModal = ref(false)

const isWorkspaceRoute = computed(() => route.path === '/workspace')
const saveLayoutName = computed(() => `Layout ${workspaceStore.savedViews.length + 1}`)

function toggleMenu() {
  showMenu.value = !showMenu.value
}

function closeMenu() {
  showMenu.value = false
}

async function handleLogout() {
  await auth.logout()
  closeMenu()
  router.push('/login')
}

async function handleSaveCurrentLayout() {
  if (workspaceStore.currentViewId) {
    const updated = workspaceStore.updateActiveView()
    if (updated) {
      closeMenu()
      return
    }
  }

  showSaveDialog.value = true
  closeMenu()
}

async function handleSaveCurrentAsNewLayout() {
  showSaveAsDialog.value = true
  closeMenu()
}

async function confirmSaveLayout(name: string) {
  if (!name.trim()) {
    await alert({ title: 'Chyba validace', message: 'Zadejte název layoutu', type: 'warning' })
    return
  }
  workspaceStore.saveCurrentView(name)
  showSaveDialog.value = false
}

async function confirmSaveAsLayout(name: string) {
  if (!name.trim()) {
    await alert({ title: 'Chyba validace', message: 'Zadejte název layoutu', type: 'warning' })
    return
  }
  workspaceStore.saveCurrentView(name)
  showSaveAsDialog.value = false
}

function handleManageLayouts() {
  closeMenu()
  showManageLayoutsModal.value = true
}

function handleSwitchWorkspace(workspace: string) {
  if (route.path !== '/workspace') {
    router.push('/workspace')
  }
  workspaceStore.switchWorkspace(workspace as Parameters<typeof workspaceStore.switchWorkspace>[0])
  closeMenu()
}
</script>

<template>
  <header class="app-header">
    <div class="header-content">
      <!-- Left: Menu + Workspace Switcher -->
      <div class="header-left">
        <Tooltip text="Menu" :delay="750">
          <button class="menu-btn" :class="{ 'is-open': showMenu }" @click="toggleMenu" data-testid="menu-btn">
            <Menu v-if="!showMenu" :size="ICON_SIZE.STANDARD" />
            <X v-if="showMenu" :size="ICON_SIZE.STANDARD" />
          </button>
        </Tooltip>

        <WorkspaceSwitcher v-if="isWorkspaceRoute" />
      </div>

      <!-- Center: Logo -->
      <AppLogo />

      <!-- Right: Layout Presets (only for part/manufacturing workspaces) -->
      <div class="header-right">
        <LayoutPresetSelector
          v-if="isWorkspaceRoute && workspaceStore.isPartWorkspace"
        />
      </div>
    </div>

    <!-- Main Menu -->
    <AppMainMenu
      :show-menu="showMenu"
      @close="closeMenu"
      @logout="handleLogout"
      @save-layout="handleSaveCurrentLayout"
      @save-as-layout="handleSaveCurrentAsNewLayout"
      @manage-layouts="handleManageLayouts"
      @switch-workspace="handleSwitchWorkspace"
    />

    <!-- Dialogs -->
    <SaveLayoutDialog
      :show="showSaveDialog"
      title="Uložit layout"
      :default-name="saveLayoutName"
      @close="showSaveDialog = false"
      @confirm="confirmSaveLayout"
    />

    <SaveLayoutDialog
      :show="showSaveAsDialog"
      title="Uložit jako nový layout"
      :default-name="saveLayoutName"
      @close="showSaveAsDialog = false"
      @confirm="confirmSaveAsLayout"
    />

    <ManageLayoutsModal
      :show="showManageLayoutsModal"
      @close="showManageLayoutsModal = false"
    />
  </header>
</template>

<style scoped>
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 36px;
  box-sizing: border-box;
  z-index: 10001;
  background: color-mix(in srgb, var(--surface) 88%, transparent);
  backdrop-filter: blur(20px) saturate(1.4);
  -webkit-backdrop-filter: blur(20px) saturate(1.4);
  border-bottom: 1px solid var(--b1);
  opacity: 0;
  transform: translateY(-4px);
  animation: header-slide-down 0.3s 0.05s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.app-header::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent 5%, var(--red) 30%, var(--red) 70%, transparent 95%);
  opacity: 0.25;
}

@keyframes header-slide-down {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;
  max-width: 100%;
  height: 100%;
  gap: 7px;
}

.menu-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  background: transparent;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  color: var(--t1);
  cursor: pointer;
  transition: all 100ms cubic-bezier(0,0,0.2,1);
}

.menu-btn:hover {
  background: var(--b1);
  border-color: var(--b3);
}

.menu-btn.is-open {
  background: var(--red);
  border-color: var(--red);
  color: white;
}

.header-left {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 5px;
}

.header-right {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 5px;
  justify-content: flex-end;
}
</style>
