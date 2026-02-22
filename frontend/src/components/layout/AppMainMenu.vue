<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { useWorkspaceStore } from '@/stores/workspace'
import type { WorkspaceType } from '@/types/workspace'
import {
  LogOut, Save, FilePlus, Settings as SettingsIcon,
  Package, Wrench, FileText, Users, Database, FolderOpen,
  Calculator, Zap
} from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  showMenu: boolean
}

interface Emits {
  (e: 'close'): void
  (e: 'logout'): void
  (e: 'save-layout'): void
  (e: 'save-as-layout'): void
  (e: 'manage-layouts'): void
  (e: 'switch-workspace', workspace: string): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const auth = useAuthStore()
const workspaceStore = useWorkspaceStore()

const workspaces: { key: WorkspaceType; label: string; icon: typeof Package }[] = [
  { key: 'part', label: 'Díly', icon: Package },
  { key: 'manufacturing', label: 'Výroba', icon: Wrench },
  { key: 'quotes', label: 'Nabídky', icon: FileText },
  { key: 'partners', label: 'Partneři', icon: Users },
  { key: 'materials', label: 'Materiály', icon: Database },
  { key: 'files', label: 'Soubory', icon: FolderOpen },
  { key: 'accounting', label: 'Účetnictví', icon: Calculator },
  { key: 'timevision', label: 'TimeVision', icon: Zap },
  { key: 'admin', label: 'Správa', icon: SettingsIcon },
]

function switchWorkspace(ws: WorkspaceType) {
  emit('switch-workspace', ws)
  emit('close')
}
</script>

<template>
  <!-- Side Menu Drawer -->
  <Transition name="menu-slide">
    <div v-if="showMenu" class="menu-drawer" @click.self="emit('close')">
      <div class="menu-content">
        <!-- Workspaces Section -->
        <div class="menu-section">
          <div class="section-title">Moduly</div>
          <button
            v-for="ws in workspaces"
            :key="ws.key"
            class="menu-item"
            :class="{ active: workspaceStore.activeWorkspace === ws.key }"
            @click="switchWorkspace(ws.key)"
            :data-testid="`menu-ws-${ws.key}`"
          >
            <component :is="ws.icon" :size="ICON_SIZE.STANDARD" />
            <span>{{ ws.label }}</span>
          </button>
        </div>

        <div class="menu-divider"></div>

        <!-- Layouts Section -->
        <div class="menu-section">
          <div class="section-title">Layouts</div>
          <button class="menu-item" @click="emit('save-layout')">
            <Save :size="ICON_SIZE.STANDARD" />
            <span>Uložit aktuální</span>
          </button>
          <button class="menu-item" @click="emit('save-as-layout')">
            <FilePlus :size="ICON_SIZE.STANDARD" />
            <span>Uložit jako...</span>
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
  background: var(--surface);
  border-right: 1px solid var(--b2);
  box-shadow: 0 12px 40px rgba(0,0,0,0.7);
  z-index: 10002;
  overflow-y: auto;
}

.menu-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
}

.menu-spacer {
  flex: 1;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: var(--pad);
  padding: var(--pad) 12px;
  background: transparent;
  border: none;
  color: var(--t1);
  text-decoration: none;
  border-radius: var(--r);
  font-size: var(--fs);
  font-weight: 500;
  cursor: pointer;
  transition: all 100ms cubic-bezier(0,0,0.2,1);
  width: 100%;
  text-align: left;
}

.menu-item:hover {
  background: var(--b1);
}

.menu-item.active {
  background: var(--red);
  color: white;
}

.menu-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-title {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t3);
  padding: 6px 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.menu-divider {
  height: 1px;
  background: var(--b2);
  margin: 12px 0;
}

.menu-footer {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-info {
  padding: var(--pad);
  background: var(--raised);
  border-radius: var(--r);
}

.user-name {
  font-weight: 600;
  color: var(--t1);
  font-size: var(--fs);
}

.user-role {
  font-size: var(--fs);
  color: var(--t3);
  margin-top: 4px;
}

.settings-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: var(--pad) 12px;
  background: transparent;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  color: var(--t1);
  text-decoration: none;
  font-size: var(--fs);
  font-weight: 500;
  cursor: pointer;
  transition: all 100ms cubic-bezier(0,0,0.2,1);
}

.settings-btn:hover {
  background: var(--b1);
  border-color: var(--b3);
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: var(--pad) 12px;
  background: transparent;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  color: var(--t1);
  font-size: var(--fs);
  font-weight: 500;
  cursor: pointer;
  transition: all 100ms cubic-bezier(0,0,0.2,1);
}

.logout-btn:hover {
  background: var(--err);
  border-color: var(--err);
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
