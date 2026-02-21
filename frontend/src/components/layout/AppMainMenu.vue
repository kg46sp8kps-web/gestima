<script setup lang="ts">
import { computed, type Component } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { LogOut, FilePlus, Save, Settings as SettingsIcon } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  showMenu: boolean
  modules: Array<{ value: string; label: string; icon: Component }>
}

interface Emits {
  (e: 'close'): void
  (e: 'logout'): void
  (e: 'new-layout'): void
  (e: 'save-layout'): void
  (e: 'save-as-layout'): void
  (e: 'manage-layouts'): void
  (e: 'open-module', moduleValue: string, label: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const route = useRoute()
const auth = useAuthStore()

function openModuleItem(value: string, label: string) {
  emit('open-module', value, label)
  emit('close')
}
</script>

<template>
  <!-- Side Menu Drawer -->
  <Transition name="menu-slide">
    <div v-if="showMenu" class="menu-drawer" @click.self="emit('close')">
      <div class="menu-content">
        <!-- Moduly Section (top) -->
        <div class="menu-section">
          <div class="section-title">Moduly</div>
          <button
            v-for="mod in modules"
            :key="mod.value"
            class="menu-item"
            @click="openModuleItem(mod.value, mod.label)"
          >
            <component :is="mod.icon" :size="ICON_SIZE.STANDARD" />
            <span>{{ mod.label }}</span>
          </button>
        </div>

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

        <div class="menu-spacer"></div>

        <div class="menu-divider"></div>

        <!-- User + Settings + Logout -->
        <div class="menu-footer">
          <div v-if="auth.user" class="user-info">
            <div class="user-name">{{ auth.user.username }}</div>
            <div class="user-role">{{ auth.user.role }}</div>
          </div>
          <router-link to="/settings" class="settings-btn" @click="emit('close')">
            <SettingsIcon :size="ICON_SIZE.STANDARD" />
            <span>Nastavení</span>
          </router-link>
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

.menu-spacer {
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
  font-size: var(--text-sm);
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
  font-size: var(--text-sm);
}

.user-role {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-top: var(--space-1);
}

.settings-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  text-decoration: none;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.settings-btn:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
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
  font-size: var(--text-sm);
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
