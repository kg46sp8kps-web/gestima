<script setup lang="ts">
/**
 * AppHeader - Minimální clean header
 * Menu vlevo, Logo + GESTIMA vpravo
 */

import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Menu, X } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const showMenu = ref(false)

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
  </header>
</template>

<style scoped>
.app-header {
  position: relative;
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
</style>
