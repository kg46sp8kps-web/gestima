<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { LogOut, FilePlus, Save, Settings as SettingsIcon } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  showMenu: boolean
}

interface Emits {
  (e: 'close'): void
  (e: 'logout'): void
  (e: 'new-layout'): void
  (e: 'save-layout'): void
  (e: 'save-as-layout'): void
  (e: 'manage-layouts'): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const route = useRoute()
const auth = useAuthStore()
</script>

<template>
  <!-- Side Menu Drawer -->
  <Transition name="menu-slide">
    <div v-if="showMenu" class="menu-drawer" @click.self="emit('close')">
      <div class="menu-content">
        <!-- Navigation -->
        <nav class="menu-nav">
          <router-link
            to="/"
            class="menu-item"
            :class="{ active: route.path === '/' }"
            @click="emit('close')"
          >
            Dashboard
          </router-link>
          <router-link
            to="/windows"
            class="menu-item"
            :class="{ active: route.path === '/windows' }"
            @click="emit('close')"
          >
            Windows
          </router-link>
          <router-link
            to="/settings"
            class="menu-item"
            :class="{ active: route.path === '/settings' }"
            @click="emit('close')"
          >
            Settings
          </router-link>
          <router-link
            v-if="auth.isAdmin"
            to="/admin/master-data"
            class="menu-item"
            :class="{ active: route.path.startsWith('/admin') }"
            @click="emit('close')"
          >
            Admin
          </router-link>
        </nav>

        <div class="menu-divider"></div>

        <!-- Window Layouts Section -->
        <div class="menu-section">
          <div class="section-title">Layouts</div>
          <button class="menu-item" @click="emit('new-layout')">
            <FilePlus :size="ICON_SIZE.STANDARD" />
            <span>Nový</span>
          </button>
          <button class="menu-item" @click="emit('save-layout')">
            <Save :size="ICON_SIZE.STANDARD" />
            <span>Uložit aktuální</span>
          </button>
          <button class="menu-item" @click="emit('save-as-layout')">
            <FilePlus :size="ICON_SIZE.STANDARD" />
            <span>Uložit aktivní jako...</span>
          </button>
          <button class="menu-item" @click="emit('manage-layouts')">
            <SettingsIcon :size="ICON_SIZE.STANDARD" />
            <span>Správa layoutů</span>
          </button>
        </div>

        <div class="menu-divider"></div>

        <!-- User + Logout -->
        <div class="menu-footer">
          <div v-if="auth.user" class="user-info">
            <div class="user-name">{{ auth.user.username }}</div>
            <div class="user-role">{{ auth.user.role }}</div>
          </div>
          <button class="logout-btn" @click="emit('logout')">
            <LogOut :size="ICON_SIZE.STANDARD" />
            <span>Logout</span>
          </button>
        </div>
      </div>
    </div>
  </Transition>

  <!-- Backdrop -->
  <Transition name="backdrop-fade">
    <div v-if="showMenu" class="backdrop" @click="emit('close')"></div>
  </Transition>
</template>

<style scoped>
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

.menu-item.active {
  background: var(--primary-color);
  color: white;
}

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
  display: flex;
  align-items: center;
  gap: var(--space-2);
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

.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 50;
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
