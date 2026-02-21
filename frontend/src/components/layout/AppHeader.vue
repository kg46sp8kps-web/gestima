<script setup lang="ts">
/**
 * AppHeader - Coordinator component (<250 LOC)
 * Delegates to sub-components for clean architecture
 */

import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useWindowsStore } from '@/stores/windows'
import { Menu, X, Package, DollarSign, Layers, LayoutGrid, Users, FileText, Database, Calculator, Zap, FolderOpen } from 'lucide-vue-next'
import ManageLayoutsModal from '@/components/modals/ManageLayoutsModal.vue'
import AppMainMenu from './AppMainMenu.vue'
import AppSearchBar from './AppSearchBar.vue'
import QuickModulesPanel from './QuickModulesPanel.vue'
import WindowActionsBar from './WindowActionsBar.vue'
import FavoriteLayoutsBar from './FavoriteLayoutsBar.vue'
import SaveLayoutDialog from './SaveLayoutDialog.vue'
import AppLogo from './AppLogo.vue'
import Tooltip from '@/components/ui/Tooltip.vue'
import { alert } from '@/composables/useDialog'
import { ICON_SIZE } from '@/config/design'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const windowsStore = useWindowsStore()

const showMenu = ref(false)
const showSaveDialog = ref(false)
const showSaveAsDialog = ref(false)
const showManageLayoutsModal = ref(false)

const availableModules = [
  { value: 'part-main', label: 'Part Main', icon: Package },
  { value: 'part-pricing', label: 'Pricing', icon: DollarSign },
  { value: 'part-technology', label: 'Technologie', icon: Layers },
  { value: 'batch-sets', label: 'Batch Sets', icon: Layers },
  { value: 'partners-list', label: 'Zákazníci', icon: Users },
  { value: 'quotes-list', label: 'Nabídky', icon: FileText },
  { value: 'manufacturing-items', label: 'Vyráběné položky', icon: Package },
  { value: 'material-items-list', label: 'Materiálové položky', icon: Database },
  { value: 'master-admin', label: 'Admin', icon: Database },
  { value: 'accounting', label: 'Účetnictví', icon: Calculator },
  { value: 'time-vision', label: 'TimeVision', icon: Zap },
  { value: 'file-manager', label: 'File Manager', icon: FolderOpen }
]

const quickModules = [
  { value: 'part-main', label: 'Part Main', icon: Package },
  { value: 'part-pricing', label: 'Pricing', icon: DollarSign },
  { value: 'part-technology', label: 'Technologie', icon: Layers },
  { value: 'batch-sets', label: 'Batch Sets', icon: Layers }
]

const topFavorites = computed(() => windowsStore.favoriteViews.slice(0, 3))
const saveLayoutName = computed(() => `Layout ${windowsStore.savedViews.length + 1}`)

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

function openModule(moduleValue: string, label: string) {
  windowsStore.openWindow(moduleValue as never, label)
}

function loadFavoriteLayout(layoutId: string) {
  windowsStore.loadView(layoutId)
}

function handleNewLayout() {
  windowsStore.closeAllWindows()
  closeMenu()
}

async function handleSaveCurrentLayout() {
  if (windowsStore.openWindows.length === 0) {
    await alert({ title: 'Info', message: 'No windows open to save!', type: 'info' })
    return
  }

  if (windowsStore.currentViewId) {
    const updated = windowsStore.updateActiveView()
    if (updated) {
      closeMenu()
      return
    }
  }

  showSaveDialog.value = true
  closeMenu()
}

async function handleSaveCurrentAsNewLayout() {
  if (windowsStore.openWindows.length === 0) {
    await alert({ title: 'Info', message: 'No windows open to save!', type: 'info' })
    return
  }
  showSaveAsDialog.value = true
  closeMenu()
}

async function confirmSaveLayout(name: string) {
  if (!name.trim()) {
    await alert({ title: 'Chyba validace', message: 'Please enter a layout name', type: 'warning' })
    return
  }
  windowsStore.saveCurrentView(name)
  showSaveDialog.value = false
}

async function confirmSaveAsLayout(name: string) {
  if (!name.trim()) {
    await alert({ title: 'Chyba validace', message: 'Please enter a layout name', type: 'warning' })
    return
  }
  windowsStore.saveCurrentViewAs(name)
  showSaveAsDialog.value = false
}

function handleManageLayouts() {
  closeMenu()
  showManageLayoutsModal.value = true
}

function arrangeWindows(mode: 'grid' | 'horizontal' | 'vertical') {
  windowsStore.arrangeWindows(mode)
}

function closeAllWindows() {
  windowsStore.closeAllWindows()
}

function handleOpenModule(moduleValue: string, label: string) {
  if (route.path !== '/windows') {
    router.push('/windows')
  }
  windowsStore.openWindow(moduleValue as never, label)
  closeMenu()
}
</script>

<template>
  <header class="app-header">
    <div class="header-content">
      <!-- Left -->
      <div class="header-left">
        <Tooltip text="Menu" :delay="750">
          <button class="menu-btn" :class="{ 'is-open': showMenu }" @click="toggleMenu">
            <Menu v-if="!showMenu" :size="ICON_SIZE.STANDARD" />
            <X v-if="showMenu" :size="ICON_SIZE.STANDARD" />
          </button>
        </Tooltip>

        <AppSearchBar
          v-if="route.path === '/windows'"
          :modules="availableModules"
          @select="openModule"
        />

        <WindowActionsBar
          v-if="route.path === '/windows'"
          @arrange="arrangeWindows"
          @close-all="closeAllWindows"
        />

        <FavoriteLayoutsBar
          v-if="route.path === '/windows'"
          :layouts="topFavorites"
          :active-id="windowsStore.currentViewId"
          @load="loadFavoriteLayout"
        />
      </div>

      <!-- Center -->
      <AppLogo />

      <!-- Right -->
      <div class="header-right">
        <QuickModulesPanel
          v-if="route.path === '/windows'"
          :quick-modules="quickModules"
          :available-modules="availableModules"
          @open="openModule"
        />
      </div>
    </div>

    <!-- Main Menu -->
    <AppMainMenu
      :show-menu="showMenu"
      :modules="availableModules"
      @close="closeMenu"
      @logout="handleLogout"
      @new-layout="handleNewLayout"
      @save-layout="handleSaveCurrentLayout"
      @save-as-layout="handleSaveCurrentAsNewLayout"
      @manage-layouts="handleManageLayouts"
      @open-module="handleOpenModule"
    />

    <!-- Dialogs -->
    <SaveLayoutDialog
      :show="showSaveDialog"
      title="Save Layout"
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
  height: 56px;
  box-sizing: border-box;
  z-index: 10001;
  background: var(--bg-base);
  border-bottom: 1px solid var(--border-default);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-6);
  max-width: 100%;
  height: 100%;
  gap: var(--space-4);
}

.menu-btn {
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

.menu-btn:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
}

.menu-btn.is-open {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.header-left {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.header-right {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  justify-content: flex-end;
}
</style>
