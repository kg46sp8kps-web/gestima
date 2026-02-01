<script setup lang="ts">
/**
 * AppHeader - Minimální clean header
 * Menu vlevo, Search + 3 oblíbené layouty, Logo + GESTIMA vpravo
 */

import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useWindowsStore } from '@/stores/windows'
import { Menu, X, Search, Save, FolderOpen, FilePlus, Settings as SettingsIcon, Package, DollarSign, Cog, Box, Layers, LayoutGrid, AlignHorizontalSpaceAround, AlignVerticalSpaceAround } from 'lucide-vue-next'
import ManageLayoutsModal from '@/components/modals/ManageLayoutsModal.vue'
import Tooltip from '@/components/ui/Tooltip.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const windowsStore = useWindowsStore()

const showMenu = ref(false)
const searchQuery = ref('')
const showSaveDialog = ref(false)
const saveLayoutName = ref('')
const showManageLayoutsModal = ref(false)
const showArrangeDropdown = ref(false)

// Custom module mapping for quick buttons
const customQuickModules = ref<Record<number, { value: string; label: string } | null>>({
  0: null, // Slot 0 = default Part Main
  1: null, // Slot 1 = default Pricing
  2: null, // Slot 2 = default Operations
  3: null, // Slot 3 = default Material
  4: null  // Slot 4 = default Batch Sets
})

const showModuleSelector = ref<number | null>(null) // Which slot's context menu is open

// Available modules for search (with icons for context menu)
const availableModules = [
  { value: 'part-main', label: 'Part Main', icon: Package },
  { value: 'part-pricing', label: 'Pricing', icon: DollarSign },
  { value: 'part-operations', label: 'Operations', icon: Cog },
  { value: 'part-material', label: 'Material', icon: Box },
  { value: 'batch-sets', label: 'Batch Sets', icon: Layers }
]

// Quick module buttons (fixed 5)
const quickModules = [
  { value: 'part-main', label: 'Part Main', icon: Package },
  { value: 'part-pricing', label: 'Pricing', icon: DollarSign },
  { value: 'part-operations', label: 'Operations', icon: Cog },
  { value: 'part-material', label: 'Material', icon: Box },
  { value: 'batch-sets', label: 'Batch Sets', icon: Layers }
]

// Filtered modules based on search
const filteredModules = computed(() => {
  if (!searchQuery.value) return []
  const query = searchQuery.value.toLowerCase()
  return availableModules.filter(m => m.label.toLowerCase().includes(query))
})

// Top 3 favorite layouts (dynamic)
const topFavorites = computed(() => windowsStore.favoriteViews.slice(0, 3))

// Load custom module mapping from localStorage
onMounted(() => {
  const saved = localStorage.getItem('gestima_custom_quick_modules')
  if (saved) {
    customQuickModules.value = JSON.parse(saved)
  }
})

// Save custom modules to localStorage
function saveCustomModules() {
  localStorage.setItem('gestima_custom_quick_modules', JSON.stringify(customQuickModules.value))
}

// Get effective module (custom or default)
function getEffectiveModule(slotIndex: number) {
  const custom = customQuickModules.value[slotIndex]
  if (custom) {
    // Find icon from availableModules
    const moduleWithIcon = availableModules.find(m => m.value === custom.value)
    return {
      value: custom.value,
      label: custom.label,
      icon: moduleWithIcon?.icon || Package
    }
  }
  return quickModules[slotIndex]
}

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
  windowsStore.openWindow(moduleValue as any, label)
  searchQuery.value = ''
}

function openQuickModule(moduleValue: string, label: string) {
  windowsStore.openWindow(moduleValue as any, label)
}

// Quick button handlers
function handleQuickButtonClick(slotIndex: number) {
  const module = getEffectiveModule(slotIndex)
  windowsStore.openWindow(module.value as any, module.label)
}

function handleQuickButtonRightClick(event: MouseEvent, slotIndex: number) {
  event.preventDefault() // Prevent browser context menu
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

function closeModuleSelector() {
  showModuleSelector.value = null
}

// Favorite actions
function loadFavoriteLayout(layoutId: string) {
  windowsStore.loadView(layoutId)
}

function handleNewLayout() {
  windowsStore.closeAllWindows()
  closeMenu()
}

function handleSaveCurrentLayout() {
  if (windowsStore.openWindows.length === 0) {
    alert('No windows open to save!')
    return
  }
  showSaveDialog.value = true
  saveLayoutName.value = `Layout ${windowsStore.savedViews.length + 1}`
  closeMenu()
}

function confirmSaveLayout() {
  if (!saveLayoutName.value.trim()) {
    alert('Please enter a layout name')
    return
  }
  windowsStore.saveCurrentView(saveLayoutName.value)
  showSaveDialog.value = false
  saveLayoutName.value = ''
}

function handleManageLayouts() {
  closeMenu()
  showManageLayoutsModal.value = true
}

function toggleArrangeDropdown() {
  showArrangeDropdown.value = !showArrangeDropdown.value
}

function arrangeWindows(mode: 'grid' | 'horizontal' | 'vertical') {
  windowsStore.arrangeWindows(mode)
  showArrangeDropdown.value = false
}

function closeAllWindows() {
  windowsStore.closeAllWindows()
}
</script>

<template>
  <header class="app-header">
    <div class="header-content">
      <!-- Left: Menu Button + Search + Actions + Layouts -->
      <div class="header-left">
        <Tooltip text="Menu" :delay="750">
          <button
            class="menu-btn"
            :class="{ 'is-open': showMenu }"
            @click="toggleMenu"
          >
            <Menu v-if="!showMenu" :size="20" />
            <X v-if="showMenu" :size="20" />
          </button>
        </Tooltip>

        <!-- Search for modules -->
        <div class="search-container" v-if="route.path === '/windows'">
          <Search :size="16" class="search-icon" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="search modules"
            class="search-input"
          />
          <!-- Search results dropdown -->
          <div v-if="filteredModules.length > 0" class="search-results">
            <button
              v-for="mod in filteredModules"
              :key="mod.value"
              @click="openModule(mod.value, mod.label)"
              class="search-result-item"
            >
              {{ mod.label }}
            </button>
          </div>
        </div>

        <!-- Window Actions (Arrange + Close All) -->
        <div class="window-actions" v-if="route.path === '/windows'">
          <!-- Arrange Dropdown -->
          <div class="action-wrapper">
            <Tooltip text="Arrange windows" :delay="750">
              <button
                class="action-btn"
                @click="toggleArrangeDropdown"
              >
                <LayoutGrid :size="16" />
              </button>
            </Tooltip>
            <Transition name="dropdown-fade">
              <div v-if="showArrangeDropdown" class="arrange-dropdown" @click.stop>
                <button class="arrange-option" @click="arrangeWindows('grid')">
                  <LayoutGrid :size="14" />
                  <span>Grid</span>
                </button>
                <button class="arrange-option" @click="arrangeWindows('horizontal')">
                  <AlignHorizontalSpaceAround :size="14" />
                  <span>Horizontal</span>
                </button>
                <button class="arrange-option" @click="arrangeWindows('vertical')">
                  <AlignVerticalSpaceAround :size="14" />
                  <span>Vertical</span>
                </button>
              </div>
            </Transition>
          </div>

          <!-- Close All -->
          <Tooltip text="Close all windows" :delay="750">
            <button
              class="action-btn"
              @click="closeAllWindows"
            >
              <X :size="16" />
            </button>
          </Tooltip>
        </div>

        <!-- Dynamic Favorite Layouts (max 3) -->
        <div class="favorite-layouts" v-if="route.path === '/windows' && topFavorites.length > 0">
          <Tooltip
            v-for="fav in topFavorites"
            :key="fav.id"
            :text="fav.name"
            :delay="750"
          >
            <button
              class="favorite-btn"
              :class="{ 'is-active': windowsStore.currentViewId === fav.id }"
              @click="loadFavoriteLayout(fav.id)"
            >
              {{ fav.name }}
            </button>
          </Tooltip>
        </div>
      </div>

      <!-- Center: GESTIMA -->
      <div class="header-center">
        <router-link to="/" class="logo-link">
          <div class="logo-text">
            <span class="logo-red">GESTI</span><span class="logo-black">MA</span>
          </div>
        </router-link>
      </div>

      <!-- Right: Quick Modules -->
      <div class="header-right">
        <!-- Quick Module Buttons (5 fixed) -->
        <div class="quick-modules" v-if="route.path === '/windows'">
          <div
            v-for="(defaultMod, index) in quickModules"
            :key="index"
            class="quick-btn-wrapper"
          >
            <Tooltip :text="getEffectiveModule(index).label" :delay="750">
              <button
                class="quick-btn"
                @click="handleQuickButtonClick(index)"
                @contextmenu="handleQuickButtonRightClick($event, index)"
              >
                <component :is="getEffectiveModule(index).icon" :size="16" />
              </button>
            </Tooltip>

            <!-- Context Menu for module selection -->
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
      </div>
    </div>

    <!-- Side Menu Drawer -->
    <Transition name="menu-slide">
      <div v-if="showMenu" class="menu-drawer" @click.self="closeMenu">
        <div class="menu-content">
          <!-- Navigation -->
          <nav class="menu-nav">
            <router-link
              to="/"
              class="menu-item"
              :class="{ active: route.path === '/' }"
              @click="closeMenu"
            >
              Dashboard
            </router-link>
            <router-link
              to="/windows"
              class="menu-item"
              :class="{ active: route.path === '/windows' }"
              @click="closeMenu"
            >
              Windows
            </router-link>
            <router-link
              to="/settings"
              class="menu-item"
              :class="{ active: route.path === '/settings' }"
              @click="closeMenu"
            >
              Settings
            </router-link>
            <router-link
              v-if="auth.isAdmin"
              to="/admin/master-data"
              class="menu-item"
              :class="{ active: route.path.startsWith('/admin') }"
              @click="closeMenu"
            >
              Admin
            </router-link>
          </nav>

          <div class="menu-divider"></div>

          <!-- Window Layouts Section -->
          <div class="menu-section">
            <div class="section-title">Window Layouts</div>
            <button class="menu-item" @click="handleNewLayout">
              <FilePlus :size="18" />
              <span>New</span>
            </button>
            <button class="menu-item" @click="handleSaveCurrentLayout">
              <Save :size="18" />
              <span>Save Current</span>
            </button>
            <button class="menu-item" @click="handleManageLayouts">
              <SettingsIcon :size="18" />
              <span>Manage Layouts</span>
            </button>
          </div>

          <div class="menu-divider"></div>

          <!-- User + Logout -->
          <div class="menu-footer">
            <div v-if="auth.user" class="user-info">
              <div class="user-name">{{ auth.user.username }}</div>
              <div class="user-role">{{ auth.user.role }}</div>
            </div>
            <button class="logout-btn" @click="handleLogout">
              Logout
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Backdrop -->
    <Transition name="backdrop-fade">
      <div v-if="showMenu" class="backdrop" @click="closeMenu"></div>
    </Transition>

    <!-- Backdrop for module selector -->
    <div v-if="showModuleSelector !== null" class="selector-backdrop" @click="closeModuleSelector"></div>

    <!-- Save Layout Dialog -->
    <Transition name="backdrop-fade">
      <div v-if="showSaveDialog" class="modal-overlay" @click="showSaveDialog = false">
        <div class="modal" @click.stop>
          <h3>Save Layout</h3>
          <input
            v-model="saveLayoutName"
            type="text"
            placeholder="Layout name..."
            class="input-layout-name"
            @keyup.enter="confirmSaveLayout"
          />
          <div class="modal-actions">
            <button @click="confirmSaveLayout" class="btn-primary">Save</button>
            <button @click="showSaveDialog = false" class="btn-secondary">Cancel</button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Manage Layouts Modal -->
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
  height: 56px; /* Fixed total height */
  box-sizing: border-box; /* Border included in height */
  z-index: 10001;
  background: var(--bg-base);
  border-bottom: 1px solid var(--border-default);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-6); /* ONLY horizontal padding - vertical centering via align-items */
  max-width: 100%;
  height: 100%; /* Fill parent height */
  gap: var(--space-4);
}

.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
}

/* Menu Button */
.menu-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
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

/* Header Left */
.header-left {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

/* Header Right */
.header-right {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  justify-content: flex-end;
}

/* Quick Module Buttons */
.quick-modules {
  display: flex;
  gap: var(--space-2);
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
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.quick-btn:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
  transform: scale(1.05);
}

.quick-btn:active {
  transform: scale(0.95);
}

/* Module Selector (context menu) */
.module-selector {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 160px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xl);
  padding: var(--space-1);
  z-index: 10003;
}

.selector-header {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.selector-option {
  display: block;
  width: 100%;
  padding: var(--space-2) var(--space-3);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-sm);
  text-align: left;
  cursor: pointer;
  transition: background var(--duration-fast);
}

.selector-option:hover {
  background: var(--state-hover);
}

.selector-divider {
  height: 1px;
  background: var(--border-default);
  margin: var(--space-1) 0;
}

.selector-reset {
  display: block;
  width: 100%;
  padding: var(--space-2) var(--space-3);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--color-danger);
  font-size: var(--text-sm);
  text-align: left;
  cursor: pointer;
  transition: background var(--duration-fast);
}

.selector-reset:hover {
  background: rgba(244, 63, 94, 0.1);
}

.selector-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10002;
  background: transparent;
}

/* Logo */
.logo-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  text-decoration: none;
}

.logo-img {
  height: 32px;
  width: auto;
}

.logo-text {
  font-size: calc(var(--text-2xl) * 2);
  font-weight: 700;
  letter-spacing: 0.5px;
}

.logo-red {
  color: #E84545; /* Logo red */
}

.logo-black {
  color: var(--text-primary);
}

/* Menu Drawer */
.menu-drawer {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 280px;
  background: var(--bg-surface);
  border-right: 1px solid var(--border-default);
  box-shadow: var(--shadow-xl);
  z-index: 10002;
  overflow-y: auto;
}

.menu-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: var(--space-6);
}

.menu-nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  flex: 1;
}

.menu-item {
  display: block;
  padding: var(--space-3) var(--space-4);
  color: var(--text-primary);
  text-decoration: none;
  border-radius: var(--radius-md);
  font-size: var(--text-xl);
  font-weight: var(--font-medium);
  transition: all var(--duration-fast) var(--ease-out);
}

.menu-item:hover {
  background: var(--state-hover);
}

.menu-item.active {
  background: var(--primary-color);
  color: white;
}

/* Menu Section */
.menu-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.section-title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  padding: var(--space-2) var(--space-4);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: transparent;
  border: none;
  color: var(--text-primary);
  text-decoration: none;
  border-radius: var(--radius-md);
  font-size: var(--text-xl);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  width: 100%;
  text-align: left;
}

.menu-item:hover {
  background: var(--state-hover);
}

.menu-divider {
  height: 1px;
  background: var(--border-default);
  margin: var(--space-4) 0;
}

.menu-footer {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.user-info {
  padding: var(--space-3);
  background: var(--bg-raised);
  border-radius: var(--radius-md);
}

.user-name {
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  font-size: var(--text-xl);
}

.user-role {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-top: var(--space-1);
}

.logout-btn {
  padding: var(--space-3) var(--space-4);
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-xl);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.logout-btn:hover {
  background: var(--color-danger);
  border-color: var(--color-danger);
  color: white;
}

/* Backdrop */
.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 50; /* BELOW windows (100+) but ABOVE page content */
}

/* Transitions */
.menu-slide-enter-active,
.menu-slide-leave-active {
  transition: transform 0.3s ease-out;
}

.menu-slide-enter-from,
.menu-slide-leave-to {
  transform: translateX(-100%);
}

.backdrop-fade-enter-active,
.backdrop-fade-leave-active {
  transition: opacity 0.3s ease;
}

.backdrop-fade-enter-from,
.backdrop-fade-leave-to {
  opacity: 0;
}

/* Search Container */
.search-container {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 280px;
}

.search-icon {
  position: absolute;
  left: var(--space-3);
  color: var(--text-secondary);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: var(--space-2) var(--space-3) var(--space-2) var(--space-8);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-sm);
  text-align: center;
  transition: all var(--duration-fast) var(--ease-out);
}

.search-input:focus {
  outline: none;
  border-color: var(--primary-color);
  background: var(--bg-base);
  text-align: left;
}

.search-input:not(:placeholder-shown) {
  text-align: left;
}

.search-results {
  position: absolute;
  top: calc(100% + var(--space-1));
  left: 0;
  right: 0;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: 10003;
  max-height: 300px;
  overflow-y: auto;
}

.search-result-item {
  display: block;
  width: 100%;
  padding: var(--space-3) var(--space-4);
  background: transparent;
  border: none;
  color: var(--text-primary);
  text-align: left;
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.search-result-item:hover {
  background: var(--state-hover);
}

/* Dynamic Favorite Layouts */
.favorite-layouts {
  display: flex;
  gap: var(--space-2);
}

.favorite-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 80px;
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

.favorite-btn:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
}

.favorite-btn.is-active {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10004;
}

.modal {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  width: 400px;
  box-shadow: var(--shadow-xl);
}

.modal h3 {
  margin: 0 0 var(--space-4) 0;
  color: var(--text-primary);
  font-size: var(--text-xl);
}

.input-layout-name {
  width: 100%;
  padding: var(--space-3);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-base);
  margin-bottom: var(--space-4);
  transition: all var(--duration-fast) var(--ease-out);
}

.input-layout-name:focus {
  outline: none;
  border-color: var(--primary-color);
}

.modal-actions {
  display: flex;
  gap: var(--space-2);
  justify-content: flex-end;
}

.btn-primary,
.btn-secondary {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  border: none;
}

.btn-primary:hover {
  opacity: 0.9;
}

.btn-secondary {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

.btn-secondary:hover {
  background: var(--state-hover);
}

/* Window Actions (Arrange + Close All) */
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
  width: 28px;
  height: 28px;
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.action-btn:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
  color: var(--text-primary);
}

/* Arrange Dropdown */
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

/* Dropdown Transition */
.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: opacity 0.15s ease;
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
}
</style>
