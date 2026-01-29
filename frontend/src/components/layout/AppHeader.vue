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

          <!-- Dropdown Menu -->
          <Transition name="menu-fade">
            <div v-if="showMenu" class="menu-dropdown">
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
    <div
      v-if="showMenu || showSearch || showFavorites"
      class="backdrop"
      @click="closeAll"
    ></div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
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
const searchQuery = ref('')
const searchInput = ref<HTMLInputElement | null>(null)

// Navigation items
const navItems = computed(() => [
  { to: '/', icon: '📊', label: 'Dashboard' },
  { to: '/parts', icon: '📦', label: 'Díly' },
  { to: '/pricing/batch-sets', icon: '💰', label: 'Sady cen' },
  { to: '/work-centers', icon: '🏭', label: 'Pracoviště' },
  { to: '/windows', icon: '🪟', label: 'Windows' },
])

// Windows modules (available only on /windows route)
const windowModules = [
  { value: 'parts-list' as WindowModule, label: 'Parts List', icon: '📦' },
  { value: 'part-pricing' as WindowModule, label: 'Pricing', icon: '💰' },
  { value: 'part-operations' as WindowModule, label: 'Operations', icon: '⚙️' },
  { value: 'part-material' as WindowModule, label: 'Material', icon: '🧱' },
  { value: 'batch-sets' as WindowModule, label: 'Batch Sets', icon: '📋' }
]

// Check if on Windows route
const isWindowsRoute = computed(() => route.path === '/windows')

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

function closeAll() {
  showMenu.value = false
  showSearch.value = false
  showFavorites.value = false
}

// Search
function performSearch() {
  if (searchQuery.value.trim()) {
    router.push({ path: '/parts', query: { search: searchQuery.value } })
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
  windowsStore.openWindow(module, `${icon} ${label}`)
  showMenu.value = false
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

// Register keyboard listener
if (typeof window !== 'undefined') {
  window.addEventListener('keydown', handleKeydown)
}
</script>

<style scoped>
.app-header {
  background: var(--bg-secondary, #fff);
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  padding: 0.5rem 2rem;
  position: relative;
  z-index: 100;
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

/* Menu Dropdown */
.menu-wrapper {
  position: relative;
}

.menu-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 240px;
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  padding: 0.5rem;
  z-index: 200;
}

.menu-section {
  padding: 0.25rem 0;
}

.menu-section-title {
  padding: 0.5rem 0.75rem;
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted, #9ca3af);
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.75rem;
  border-radius: 8px;
  text-decoration: none;
  color: var(--text-primary, #111);
  font-size: 0.875rem;
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
  font-size: 1rem;
  width: 20px;
  text-align: center;
}

.menu-label {
  flex: 1;
}

.menu-divider {
  height: 1px;
  background: var(--border-color, #e5e7eb);
  margin: 0.25rem 0.5rem;
}

/* Backdrop */
.backdrop {
  position: fixed;
  inset: 0;
  z-index: 99;
}

/* Transitions */
.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: all 0.15s ease;
}

.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
