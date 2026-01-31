<template>
  <header class="app-header">
    <div class="header-container">
      <!-- Left: Logo + GESTIMA -->
      <router-link to="/" class="logo-link">
        <img src="/logo.png" alt="KOVO RYBKA" class="logo-img" />
        <div class="logo-text">
          <span class="logo-red">GESTI</span><span class="logo-black">MA</span>
        </div>
        <div class="version-badge">v1.10.1</div>
      </router-link>

      <!-- Right: Controls -->
      <div class="header-controls">
        <!-- Density Toggle -->
        <button
          class="control-btn density-toggle"
          :class="{ 'is-compact': ui.isCompactDensity }"
          @click="ui.toggleDensity()"
          :title="ui.isCompactDensity ? 'Přepnout na komfortní zobrazení' : 'Přepnout na kompaktní zobrazení'"
        >
          <span v-if="ui.isCompactDensity">📐</span>
          <span v-else>📏</span>
        </button>

        <!-- Search -->
        <div class="search-wrapper">
          <button
            class="control-btn"
            @click="toggleSearch"
            title="Vyhledávání (Ctrl+K)"
          >
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
          </button>
          <div v-if="showSearch" class="search-dropdown">
            <input
              ref="searchInput"
              v-model="searchQuery"
              type="text"
              placeholder="Hledat díly, operace..."
              class="search-input"
              @keydown.escape="showSearch = false"
              @keydown.enter="performSearch"
            />
            <div v-if="searchQuery" class="search-hint">
              Stiskni Enter pro vyhledání
            </div>
          </div>
        </div>

        <!-- Favorites -->
        <button
          class="control-btn"
          @click="toggleFavorites"
          title="Oblíbené"
        >
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
          </svg>
        </button>

        <!-- User Info -->
        <div v-if="auth.user" class="user-badge">
          <span class="user-name">{{ auth.user.username }}</span>
          <span class="user-role">({{ auth.user.role }})</span>
        </div>

        <!-- Hamburger Menu -->
        <div class="menu-wrapper">
          <button
            class="control-btn menu-btn"
            :class="{ 'is-open': showMenu }"
            @click="toggleMenu"
            title="Menu"
          >
            <svg class="icon hamburger-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="3" y1="6" x2="21" y2="6"/>
              <line x1="3" y1="12" x2="21" y2="12"/>
              <line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>

          <!-- Drawer Menu -->
          <Transition name="menu-slide">
            <div v-if="showMenu" class="menu-drawer">
              <div class="menu-section">
                <div class="menu-section-title">Navigace</div>
                <router-link
                  v-for="item in navItems"
                  :key="item.to"
                  :to="item.to"
                  class="menu-item"
                  :class="{ 'is-active': isActive(item.to) }"
                  @click="showMenu = false"
                >
                  <span class="menu-icon">{{ item.icon }}</span>
                  <span class="menu-label">{{ item.label }}</span>
                </router-link>
              </div>

              <!-- Windows Modules (only on /windows route) -->
              <template v-if="isWindowsRoute">
                <div class="menu-divider"></div>
                <div class="menu-section">
                  <div class="menu-section-title">Open Modules</div>
                  <button
                    v-for="mod in windowModules"
                    :key="mod.value"
                    class="menu-item"
                    @click="openWindowModule(mod.value, mod.label, mod.icon)"
                  >
                    <span class="menu-icon">{{ mod.icon }}</span>
                    <span class="menu-label">{{ mod.label }}</span>
                  </button>
                </div>

                <div class="menu-divider"></div>
                <div class="menu-section">
                  <div class="menu-section-title">Window Actions</div>
                  <button class="menu-item" @click="arrangeWindows('grid')">
                    <span class="menu-icon">🔲</span>
                    <span class="menu-label">Arrange Grid</span>
                  </button>
                  <button class="menu-item" @click="closeAllWindows">
                    <span class="menu-icon">❌</span>
                    <span class="menu-label">Close All</span>
                  </button>
                </div>
              </template>

              <div class="menu-divider"></div>

              <div class="menu-section">
                <div class="menu-section-title">Nastavení</div>
                <router-link
                  to="/settings"
                  class="menu-item"
                  :class="{ 'is-active': isActive('/settings') }"
                  @click="showMenu = false"
                >
                  <span class="menu-icon">⚙️</span>
                  <span class="menu-label">Nastavení</span>
                </router-link>
                <router-link
                  v-if="auth.isAdmin"
                  to="/admin/master-data"
                  class="menu-item"
                  :class="{ 'is-active': isActive('/admin/master-data') }"
                  @click="showMenu = false"
                >
                  <span class="menu-icon">🔧</span>
                  <span class="menu-label">Master Data</span>
                </router-link>
              </div>

              <div class="menu-divider"></div>

              <div class="menu-section">
                <button class="menu-item menu-item-danger" @click="handleLogout">
                  <span class="menu-icon">🚪</span>
                  <span class="menu-label">Odhlásit se</span>
                </button>
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </div>

    <!-- Click outside to close -->
    <Transition name="backdrop-fade">
      <div
        v-if="showMenu || showSearch || showFavorites"
        class="backdrop"
        @click="closeAll"
      ></div>
    </Transition>

    <!-- Windows Toolbar (only on /windows route) -->
    <div v-if="isWindowsRoute" class="header-windows-toolbar">
      <div class="toolbar-container">
        <!-- Left: Module + Layout dropdowns -->
        <div class="toolbar-left">
          <!-- Module Dropdown -->
          <div class="dropdown-wrapper">
            <button
              class="toolbar-btn toolbar-dropdown"
              :class="{ 'is-open': showModuleDropdown }"
              @click="toggleModuleDropdown"
            >
              <span class="btn-icon">➕</span>
              <span class="btn-label">Module</span>
              <span class="btn-arrow">▼</span>
            </button>
            <Transition name="dropdown-fade">
              <div v-if="showModuleDropdown" class="dropdown-menu">
                <button
                  v-for="mod in windowModules"
                  :key="mod.value"
                  class="dropdown-item"
                  @click="openWindowFromToolbar(mod.value, mod.label, mod.icon)"
                >
                  <span class="item-icon">{{ mod.icon }}</span>
                  <span class="item-label">{{ mod.label }}</span>
                </button>
              </div>
            </Transition>
          </div>

          <!-- Layout Dropdown -->
          <div class="dropdown-wrapper">
            <button
              class="toolbar-btn toolbar-dropdown"
              :class="{ 'is-open': showLayoutDropdown }"
              @click="toggleLayoutDropdown"
            >
              <span class="btn-icon">⭐</span>
              <span class="btn-label">{{ currentLayoutName }}</span>
              <span class="btn-arrow">▼</span>
            </button>
            <Transition name="dropdown-fade">
              <div v-if="showLayoutDropdown" class="dropdown-menu">
                <!-- Favorite Layouts -->
                <template v-if="windowsStore.favoriteViews.length > 0">
                  <div class="dropdown-section-title">⭐ Favorites</div>
                  <button
                    v-for="view in windowsStore.favoriteViews"
                    :key="view.id"
                    class="dropdown-item"
                    :class="{ 'is-active': windowsStore.currentViewId === view.id }"
                    @click="loadLayout(view.id)"
                  >
                    <span class="item-icon">{{ windowsStore.defaultLayoutId === view.id ? '🏠' : '⭐' }}</span>
                    <span class="item-label">{{ view.name }}</span>
                  </button>
                  <div class="dropdown-divider"></div>
                </template>

                <!-- All Layouts -->
                <div class="dropdown-section-title">All Layouts</div>
                <button
                  v-for="view in windowsStore.savedViews"
                  :key="view.id"
                  class="dropdown-item"
                  :class="{ 'is-active': windowsStore.currentViewId === view.id }"
                  @click="loadLayout(view.id)"
                >
                  <span class="item-icon">{{ windowsStore.defaultLayoutId === view.id ? '🏠' : '📐' }}</span>
                  <span class="item-label">{{ view.name }}</span>
                  <span class="item-actions">
                    <button
                      class="action-btn"
                      :title="view.favorite ? 'Remove from favorites' : 'Add to favorites'"
                      @click.stop="windowsStore.toggleFavoriteView(view.id)"
                    >
                      {{ view.favorite ? '⭐' : '☆' }}
                    </button>
                    <button
                      class="action-btn"
                      :title="windowsStore.defaultLayoutId === view.id ? 'Unset default' : 'Set as default'"
                      @click.stop="toggleDefaultLayout(view.id)"
                    >
                      {{ windowsStore.defaultLayoutId === view.id ? '🏠' : '🏡' }}
                    </button>
                    <button
                      class="action-btn action-danger"
                      title="Delete"
                      @click.stop="deleteLayout(view.id)"
                    >
                      🗑️
                    </button>
                  </span>
                </button>

                <template v-if="windowsStore.savedViews.length === 0">
                  <div class="dropdown-empty">No saved layouts</div>
                </template>
              </div>
            </Transition>
          </div>
        </div>

        <!-- Right: Action buttons -->
        <div class="toolbar-right">
          <!-- Save Dropdown -->
          <div class="dropdown-wrapper">
            <button
              class="toolbar-btn toolbar-dropdown"
              :class="{ 'is-open': showSaveDropdown }"
              @click="toggleSaveDropdown"
            >
              <span class="btn-icon">💾</span>
              <span class="btn-label-compact">Save</span>
              <span class="btn-arrow">▼</span>
            </button>
            <Transition name="dropdown-fade">
              <div v-if="showSaveDropdown" class="dropdown-menu">
                <button
                  class="dropdown-item"
                  :disabled="!windowsStore.currentViewId"
                  @click="saveCurrentLayout"
                >
                  <span class="item-icon">💾</span>
                  <span class="item-label">Uložit aktuální</span>
                </button>
                <button
                  class="dropdown-item"
                  @click="saveLayoutAs"
                >
                  <span class="item-icon">📝</span>
                  <span class="item-label">Uložit jako...</span>
                </button>
              </div>
            </Transition>
          </div>

          <button
            class="toolbar-btn"
            title="Arrange windows (grid)"
            @click="arrangeWindows('grid')"
          >
            <span class="btn-icon">🔲</span>
            <span class="btn-label-compact">Arrange</span>
          </button>
          <button
            class="toolbar-btn toolbar-danger"
            title="Close all windows"
            @click="closeAllWindows"
          >
            <span class="btn-icon">❌</span>
            <span class="btn-label-compact">Close All</span>
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useWindowsStore, type WindowModule } from '@/stores/windows'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const ui = useUiStore()
const windowsStore = useWindowsStore()

// State
const showMenu = ref(false)
const showSearch = ref(false)
const showFavorites = ref(false)
const showModuleDropdown = ref(false)
const showLayoutDropdown = ref(false)
const showSaveDropdown = ref(false)
const searchQuery = ref('')
const searchInput = ref<HTMLInputElement | null>(null)

// Navigation items
const navItems = computed(() => [
  { to: '/', icon: '📊', label: 'Dashboard' },
  { to: '/windows', icon: '🪟', label: 'Windows' },
])

// Windows modules (available only on /windows route)
const windowModules = [
  { value: 'part-main' as WindowModule, label: 'Part Main', icon: '📦' },
  { value: 'part-pricing' as WindowModule, label: 'Pricing', icon: '💰' },
  { value: 'part-operations' as WindowModule, label: 'Operations', icon: '⚙️' },
  { value: 'part-material' as WindowModule, label: 'Material', icon: '🧱' },
  { value: 'batch-sets' as WindowModule, label: 'Batch Sets', icon: '📋' }
]

// Check if on Windows route
const isWindowsRoute = computed(() => route.path === '/windows')

// Current layout name
const currentLayoutName = computed(() => {
  if (!windowsStore.currentViewId) return 'My Layout'
  const view = windowsStore.savedViews.find(v => v.id === windowsStore.currentViewId)
  return view ? view.name : 'My Layout'
})

// Check if route is active
function isActive(path: string): boolean {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path.startsWith(path)
}

// Toggle functions
function toggleMenu() {
  showMenu.value = !showMenu.value
  showSearch.value = false
  showFavorites.value = false
}

function toggleSearch() {
  showSearch.value = !showSearch.value
  showMenu.value = false
  showFavorites.value = false
  if (showSearch.value) {
    nextTick(() => {
      searchInput.value?.focus()
    })
  }
}

function toggleFavorites() {
  showFavorites.value = !showFavorites.value
  showMenu.value = false
  showSearch.value = false
  ui.showInfo('Oblíbené - připravujeme')
}

function toggleModuleDropdown() {
  showModuleDropdown.value = !showModuleDropdown.value
  showLayoutDropdown.value = false
}

function toggleLayoutDropdown() {
  showLayoutDropdown.value = !showLayoutDropdown.value
  showModuleDropdown.value = false
  showSaveDropdown.value = false
}

function toggleSaveDropdown() {
  showSaveDropdown.value = !showSaveDropdown.value
  showModuleDropdown.value = false
  showLayoutDropdown.value = false
}

function closeAll() {
  showMenu.value = false
  showSearch.value = false
  showFavorites.value = false
  showModuleDropdown.value = false
  showLayoutDropdown.value = false
  showSaveDropdown.value = false
}

// Search
function performSearch() {
  if (searchQuery.value.trim()) {
    // Navigate to windows and open part-main with search query
    router.push('/windows')
    // TODO: Pass search query to part-main module
    // This would require updating PartMainModule to accept initial search query
    showSearch.value = false
    searchQuery.value = ''
  }
}

// Logout
async function handleLogout() {
  try {
    await auth.logout()
    ui.showInfo('Odhlášení proběhlo úspěšně')
    showMenu.value = false
    router.push('/login')
  } catch (err) {
    ui.showError('Chyba při odhlašování')
  }
}

// Windows actions
function openWindowModule(module: WindowModule, label: string, icon: string) {
  const title = `${icon} ${label}`
  windowsStore.openWindow(module, title)
  showMenu.value = false
}

function openWindowFromToolbar(module: WindowModule, label: string, icon: string) {
  const title = `${icon} ${label}`
  windowsStore.openWindow(module, title)
  showModuleDropdown.value = false
}

function arrangeWindows(mode: 'grid' | 'horizontal' | 'vertical') {
  windowsStore.arrangeWindows(mode)
  showMenu.value = false
}

function closeAllWindows() {
  if (confirm('Zavřít všechna okna?')) {
    windowsStore.closeAllWindows()
  }
  showMenu.value = false
}

// Layout management
function saveLayout() {
  const name = prompt('Název layoutu:', `Layout ${windowsStore.savedViews.length + 1}`)
  if (name && name.trim()) {
    windowsStore.saveCurrentView(name.trim())
    ui.showSuccess(`Layout "${name}" uložen`)
  }
}

function saveCurrentLayout() {
  if (!windowsStore.currentViewId) return

  const currentView = windowsStore.savedViews.find(v => v.id === windowsStore.currentViewId)
  if (!currentView) return

  // Update current view with current window state
  currentView.windows = JSON.parse(JSON.stringify(windowsStore.windows))
  currentView.updatedAt = new Date().toISOString()

  showSaveDropdown.value = false
  ui.showSuccess(`Layout "${currentView.name}" aktualizován`)
}

function saveLayoutAs() {
  const currentView = windowsStore.savedViews.find(v => v.id === windowsStore.currentViewId)
  const defaultName = currentView
    ? `${currentView.name} (kopie)`
    : `Layout ${windowsStore.savedViews.length + 1}`

  const name = prompt('Název layoutu:', defaultName)
  if (name && name.trim()) {
    windowsStore.saveCurrentView(name.trim())
    showSaveDropdown.value = false
    ui.showSuccess(`Layout "${name}" uložen`)
  }
}

function loadLayout(viewId: string) {
  windowsStore.loadView(viewId)
  showLayoutDropdown.value = false
  ui.showSuccess('Layout načten')
}

function deleteLayout(viewId: string) {
  const view = windowsStore.savedViews.find(v => v.id === viewId)
  if (view && confirm(`Smazat layout "${view.name}"?`)) {
    windowsStore.deleteView(viewId)
    ui.showSuccess('Layout smazán')
  }
}

function toggleDefaultLayout(viewId: string) {
  windowsStore.setDefaultLayout(viewId === windowsStore.defaultLayoutId ? null : viewId)
  const view = windowsStore.savedViews.find(v => v.id === viewId)
  if (windowsStore.defaultLayoutId === viewId && view) {
    ui.showSuccess(`"${view.name}" nastaven jako výchozí`)
  } else {
    ui.showSuccess('Výchozí layout zrušen')
  }
}

// Keyboard shortcut (Ctrl+K)
function handleKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    toggleSearch()
  }
  if (e.key === 'Escape') {
    closeAll()
  }
}

// Click outside to close dropdowns
function handleClickOutside(e: MouseEvent) {
  const target = e.target as HTMLElement

  // Check if click is outside dropdown wrappers
  if (!target.closest('.dropdown-wrapper') &&
      !target.closest('.menu-wrapper') &&
      !target.closest('.search-wrapper')) {
    closeAll()
  }
}

// Register keyboard and click listeners
if (typeof window !== 'undefined') {
  window.addEventListener('keydown', handleKeydown)
  document.addEventListener('click', handleClickOutside)
}

// Body scroll lock when drawer is open
watch(showMenu, (isOpen) => {
  if (typeof document !== 'undefined') {
    document.body.style.overflow = isOpen ? 'hidden' : ''
  }
})
</script>

<style scoped>
.app-header {
  background: var(--bg-secondary, #fff);
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  padding: 0.5rem 2rem;
  position: relative;
  z-index: 10001;
}

.header-container {
  width: 95%;
  min-width: 1000px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-sizing: border-box;
}

/* Logo */
.logo-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  text-decoration: none;
}

.logo-img {
  height: 36px;
  width: auto;
}

.logo-text {
  font-size: 1.3rem;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.logo-red {
  color: var(--accent-red, #dc2626);
}

.logo-black {
  color: var(--text-primary, #111);
}

.version-badge {
  font-size: 0.55rem;
  padding: 2px 5px;
  background: var(--accent-red, #dc2626);
  color: white;
  border-radius: 3px;
  font-weight: 600;
}

/* Controls */
.header-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.control-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary, #6b7280);
  transition: all 0.15s ease;
}

.control-btn:hover {
  background: var(--bg-primary, #f3f4f6);
  color: var(--text-primary, #111);
}

.density-toggle.is-compact {
  background: var(--color-success, #059669);
  color: white;
}

.density-toggle.is-compact:hover {
  background: var(--color-success-hover, #047857);
  color: white;
}

.control-btn .icon {
  width: 20px;
  height: 20px;
}

.menu-btn.is-open {
  background: var(--accent-red, #dc2626);
  color: white;
}

.menu-btn.is-open:hover {
  background: #b91c1c;
  color: white;
}

/* User Badge */
.user-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-secondary, #6b7280);
  font-size: 0.75rem;
  margin-right: 0.25rem;
}

.user-name {
  color: var(--text-primary, #111);
  font-weight: 500;
}

.user-role {
  color: var(--text-muted, #9ca3af);
}

/* Search Dropdown */
.search-wrapper {
  position: relative;
}

.search-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 320px;
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  padding: 0.5rem;
  z-index: 200;
}

.search-input {
  width: 100%;
  padding: 0.75rem 1rem;
  font-size: 0.9rem;
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 8px;
  outline: none;
  transition: border-color 0.15s;
}

.search-input:focus {
  border-color: var(--accent-red, #dc2626);
}

.search-hint {
  padding: 0.5rem 1rem;
  font-size: 0.75rem;
  color: var(--text-muted, #9ca3af);
}

/* Menu Drawer */
.menu-wrapper {
  position: relative;
}

.menu-drawer {
  position: fixed;
  top: 0;
  right: 0;
  height: 100vh;
  width: 280px;
  background: var(--bg-surface, #141414);
  border-left: 1px solid var(--border-default, #262626);
  box-shadow: -10px 0 40px rgba(0, 0, 0, 0.5);
  padding: 0.75rem 0.5rem;
  overflow-y: auto;
  z-index: 10000;
}

.menu-section {
  padding: 0.25rem 0;
}

.menu-section-title {
  padding: 0.375rem 0.5rem;
  font-size: 0.625rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted, #9ca3af);
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.5rem;
  border-radius: 6px;
  text-decoration: none;
  color: var(--text-primary, #111);
  font-size: 0.8125rem;
  cursor: pointer;
  transition: all 0.1s ease;
  border: none;
  background: transparent;
  width: 100%;
  text-align: left;
}

.menu-item:hover {
  background: var(--bg-primary, #f3f4f6);
}

.menu-item.is-active {
  background: var(--accent-red, #dc2626);
  color: white;
}

.menu-item.is-active .menu-icon {
  filter: grayscale(1) brightness(10);
}

.menu-item-danger:hover {
  background: #fef2f2;
  color: #dc2626;
}

.menu-icon {
  font-size: 0.9rem;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
}

.menu-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.menu-divider {
  height: 1px;
  background: var(--border-color, #e5e7eb);
  margin: 0.375rem 0.5rem;
}

/* Backdrop */
.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 9999;
}

/* Transitions */
.menu-slide-enter-active,
.menu-slide-leave-active {
  transition: transform 0.3s ease-out;
}

.menu-slide-enter-from,
.menu-slide-leave-to {
  transform: translateX(100%);
}

.backdrop-fade-enter-active,
.backdrop-fade-leave-active {
  transition: opacity 0.3s ease;
}

.backdrop-fade-enter-from,
.backdrop-fade-leave-to {
  opacity: 0;
}

/* Windows Toolbar */
.header-windows-toolbar {
  background: var(--bg-surface, #fff);
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  padding: 0.25rem 2rem;
}

.toolbar-container {
  width: 95%;
  min-width: 1000px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

/* Toolbar Buttons */
.toolbar-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 4px;
  cursor: pointer;
  color: var(--text-primary, #111);
  transition: all 0.15s ease;
  white-space: nowrap;
}

.toolbar-btn:hover {
  background: var(--bg-secondary, #fff);
  border-color: var(--text-muted, #9ca3af);
}

.toolbar-btn.is-open {
  background: var(--accent-red, #dc2626);
  color: white;
  border-color: var(--accent-red, #dc2626);
}

.toolbar-btn-danger:hover {
  background: #fef2f2;
  color: #dc2626;
  border-color: #dc2626;
}

.toolbar-dropdown {
  min-width: 100px;
}

.btn-icon {
  font-size: 0.75rem;
}

.btn-label {
  flex: 1;
  text-align: left;
  font-size: 0.75rem;
}

.btn-label-compact {
  font-size: 0.6875rem;
}

.btn-arrow {
  font-size: 0.5rem;
  opacity: 0.6;
}

/* Dropdown Menu */
.dropdown-wrapper {
  position: relative;
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 220px;
  max-width: 320px;
  max-height: 400px;
  overflow-y: auto;
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 0.25rem;
  z-index: 200;
}

.dropdown-section-title {
  padding: 0.375rem 0.5rem;
  font-size: 0.625rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted, #9ca3af);
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.5rem;
  border-radius: 4px;
  text-decoration: none;
  color: var(--text-primary, #111);
  font-size: 0.8125rem;
  cursor: pointer;
  transition: all 0.1s ease;
  border: none;
  background: transparent;
  width: 100%;
  text-align: left;
}

.dropdown-item:hover {
  background: var(--bg-primary, #f3f4f6);
}

.dropdown-item.is-active {
  background: var(--accent-subtle, #fee2e2);
  color: var(--accent-red, #dc2626);
  font-weight: 500;
}

.item-icon {
  font-size: 0.9rem;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
}

.item-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-actions {
  display: flex;
  gap: 0.25rem;
  align-items: center;
}

.action-btn {
  padding: 0.125rem 0.25rem;
  font-size: 0.75rem;
  background: transparent;
  border: none;
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.15s;
}

.action-btn:hover {
  opacity: 1;
}

.action-danger:hover {
  color: #dc2626;
}

.dropdown-divider {
  height: 1px;
  background: var(--border-color, #e5e7eb);
  margin: 0.25rem 0;
}

.dropdown-empty {
  padding: 1rem;
  text-align: center;
  font-size: 0.75rem;
  color: var(--text-muted, #9ca3af);
}

/* Dropdown Transition */
.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
