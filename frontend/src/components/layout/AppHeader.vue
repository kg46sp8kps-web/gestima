<script setup lang="ts">
/**
 * AppHeader - Minimální clean header
 * Menu vlevo, Search + 3 oblíbené layouty, Logo + GESTIMA vpravo
 */

import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useWindowsStore } from '@/stores/windows'
import { Menu, X, Search, Star, Save, FolderOpen, FilePlus, Settings as SettingsIcon } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const windowsStore = useWindowsStore()

const showMenu = ref(false)
const searchQuery = ref('')
const showSaveDialog = ref(false)
const saveLayoutName = ref('')

// Available modules for search
const availableModules = [
  { value: 'part-main', label: 'Part Main' },
  { value: 'part-pricing', label: 'Pricing' },
  { value: 'part-operations', label: 'Operations' },
  { value: 'part-material', label: 'Material' },
  { value: 'batch-sets', label: 'Batch Sets' }
]

// Filtered modules based on search
const filteredModules = computed(() => {
  if (!searchQuery.value) return []
  const query = searchQuery.value.toLowerCase()
  return availableModules.filter(m => m.label.toLowerCase().includes(query))
})

// Top 3 favorite layouts
const topFavorites = computed(() =>
  windowsStore.favoriteViews.slice(0, 3)
)

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

function loadFavoriteLayout(viewId: string) {
  windowsStore.loadView(viewId)
}

function handleNewLayout() {
  if (confirm('Close all windows and start new layout?')) {
    windowsStore.closeAllWindows()
  }
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

function handleLoadLayout() {
  closeMenu()
  router.push('/windows')
}

function handleManageLayouts() {
  closeMenu()
  router.push('/settings')
}
</script>

<template>
  <header class="app-header">
    <div class="header-content">
      <!-- Left: Menu Button -->
      <button
        class="menu-btn"
        :class="{ 'is-open': showMenu }"
        @click="toggleMenu"
        title="Menu"
      >
        <Menu v-if="!showMenu" :size="20" />
        <X v-if="showMenu" :size="20" />
      </button>

      <!-- Center: Search + Favorite Layouts -->
      <div class="header-center">
        <!-- Search for modules -->
        <div class="search-container" v-if="route.path === '/windows'">
          <Search :size="16" class="search-icon" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search modules..."
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

        <!-- Top 3 Favorite Layouts -->
        <div class="favorite-layouts" v-if="route.path === '/windows' && topFavorites.length > 0">
          <button
            v-for="fav in topFavorites"
            :key="fav.id"
            @click="loadFavoriteLayout(fav.id)"
            class="favorite-btn"
            :class="{ active: windowsStore.currentViewId === fav.id }"
            :title="fav.name"
          >
            <Star :size="14" :fill="windowsStore.currentViewId === fav.id ? 'currentColor' : 'none'" />
            <span>{{ fav.name }}</span>
          </button>
        </div>
      </div>

      <!-- Right: Logo + GESTIMA -->
      <router-link to="/" class="logo-link">
        <img src="/logo.png" alt="KOVO RYBKA" class="logo-img" />
        <div class="logo-text">
          <span class="logo-red">GESTI</span><span class="logo-black">MA</span>
        </div>
        <div class="version-badge">v1.11</div>
      </router-link>
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
            <button class="menu-item" @click="handleLoadLayout">
              <FolderOpen :size="18" />
              <span>Load Layout</span>
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
  </header>
</template>

<style scoped>
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10001;
  background: var(--bg-base);
  border-bottom: 1px solid var(--border-default);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-6);
  max-width: 100%;
  gap: var(--space-4);
}

.header-center {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  justify-content: flex-start;
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
  font-size: var(--text-2xl);
  font-weight: 700;
  letter-spacing: 0.5px;
}

.logo-red {
  color: var(--color-primary);
}

.logo-black {
  color: var(--text-primary);
}

.version-badge {
  font-size: var(--text-2xs);
  padding: var(--space-1) var(--space-2);
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-sm);
  font-weight: 600;
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
  z-index: 10001;
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
  transition: all var(--duration-fast) var(--ease-out);
}

.search-input:focus {
  outline: none;
  border-color: var(--primary-color);
  background: var(--bg-base);
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

/* Favorite Layouts */
.favorite-layouts {
  display: flex;
  gap: var(--space-2);
}

.favorite-btn {
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

.favorite-btn:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
}

.favorite-btn.active {
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
</style>
