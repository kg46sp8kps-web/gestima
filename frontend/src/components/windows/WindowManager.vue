<script setup lang="ts">
/**
 * WindowManager - Toolbar for managing windows
 * Open/close windows, arrange to grid, save/load views
 */

import { ref, computed, type Component } from 'vue'
import { useWindowsStore, type WindowModule } from '@/stores/windows'
import {
  Package,
  DollarSign,
  Settings,
  Box,
  ClipboardList,
  Save,
  Folder,
  X,
  Star,
  Grid3x3,
  AlignHorizontalSpaceAround,
  AlignVerticalSpaceAround
} from 'lucide-vue-next'

const store = useWindowsStore()

// Available modules with Lucide icons
const modules: Array<{ value: WindowModule; label: string; icon: Component }> = [
  { value: 'part-main', label: 'Part Main', icon: Package },
  { value: 'part-pricing', label: 'Pricing', icon: DollarSign },
  { value: 'part-operations', label: 'Operations', icon: Settings },
  { value: 'part-material', label: 'Material', icon: Box },
  { value: 'batch-sets', label: 'Batch Sets', icon: ClipboardList }
]

// Save view dialog
const showSaveDialog = ref(false)
const viewName = ref('')

// Arrange mode
const arrangeMode = ref<'grid' | 'horizontal' | 'vertical'>('grid')

function openModule(module: WindowModule, label: string) {
  store.openWindow(module, label)
}

function handleArrange() {
  store.arrangeWindows(arrangeMode.value)
}

function handleSaveView() {
  if (store.openWindows.length === 0) {
    alert('No windows open to save!')
    return
  }

  showSaveDialog.value = true
  viewName.value = `View ${store.savedViews.length + 1}`
}

function confirmSaveView() {
  if (!viewName.value.trim()) {
    alert('Please enter a view name')
    return
  }

  store.saveCurrentView(viewName.value)
  showSaveDialog.value = false
  viewName.value = ''
}

function handleLoadView(viewId: string) {
  store.loadView(viewId)
}

function handleLoadViewFromSelect(event: Event) {
  const select = event.target as HTMLSelectElement
  const viewId = select.value
  if (viewId) {
    store.loadView(viewId)
    select.value = '' // Reset dropdown
  }
}

function handleCloseAll() {
  if (confirm('Close all windows?')) {
    store.closeAllWindows()
  }
}
</script>

<template>
  <div class="window-manager">
    <!-- Toolbar -->
    <div class="toolbar">
      <!-- Open Windows -->
      <div class="toolbar-section">
        <label class="section-label">Open:</label>
        <button
          v-for="mod in modules"
          :key="mod.value"
          @click="openModule(mod.value, mod.label)"
          class="btn-module"
          :title="`Open ${mod.label}`"
        >
          <component :is="mod.icon" :size="16" />
          <span>{{ mod.label }}</span>
        </button>
      </div>

      <!-- Actions -->
      <div class="toolbar-section">
        <!-- Arrange dropdown -->
        <div class="arrange-group">
          <select
            v-model="arrangeMode"
            class="select-arrange"
            :disabled="store.openWindows.length === 0"
          >
            <option value="grid">Grid</option>
            <option value="horizontal">Horizontal</option>
            <option value="vertical">Vertical</option>
          </select>
          <button
            @click="handleArrange"
            class="btn-action"
            title="Arrange windows"
            :disabled="store.openWindows.length === 0"
          >
            Arrange
          </button>
        </div>

        <button
          @click="handleSaveView"
          class="btn-action"
          title="Save current window layout"
          :disabled="store.openWindows.length === 0"
        >
          <Save :size="16" />
          <span>Save View</span>
        </button>

        <!-- Views dropdown (all views) -->
        <select
          v-if="store.savedViews.length > 0"
          @change="handleLoadViewFromSelect"
          class="select-view"
        >
          <option value="">Load View...</option>
          <option
            v-for="view in store.savedViews"
            :key="view.id"
            :value="view.id"
          >
            {{ view.favorite ? '★' : '' }} {{ view.name }}
          </option>
        </select>

        <button
          @click="handleCloseAll"
          class="btn-action btn-danger"
          title="Close all windows"
          :disabled="store.openWindows.length === 0"
        >
          <X :size="16" />
          <span>Close All</span>
        </button>
      </div>

      <!-- Favorite Views (buttons) -->
      <div v-if="store.favoriteViews.length > 0" class="toolbar-section">
        <label class="section-label">Favorites:</label>
        <div class="favorite-views">
          <button
            v-for="view in store.favoriteViews"
            :key="view.id"
            @click="handleLoadView(view.id)"
            class="btn-favorite-view"
            :class="{ active: store.currentViewId === view.id }"
            :title="view.name"
          >
            <Star :size="14" :fill="store.currentViewId === view.id ? 'currentColor' : 'none'" />
            <span>{{ view.name }}</span>
          </button>
        </div>
      </div>

      <!-- System Tray (Minimized Windows) -->
      <div v-if="store.minimizedWindows.length > 0" class="toolbar-section system-tray">
        <label class="section-label">Tray:</label>
        <div class="tray-icons">
          <button
            v-for="win in store.minimizedWindows"
            :key="win.id"
            @click="store.restoreWindow(win.id)"
            class="btn-tray-icon"
            :title="`Restore: ${win.title}`"
          >
            {{ win.title.split(' ')[0] }}
          </button>
        </div>
      </div>
    </div>

    <!-- Save View Dialog -->
    <div v-if="showSaveDialog" class="modal-overlay" @click="showSaveDialog = false">
      <div class="modal" @click.stop>
        <h3>Save View</h3>
        <input
          v-model="viewName"
          type="text"
          placeholder="View name..."
          class="input-view-name"
          @keyup.enter="confirmSaveView"
        />
        <div class="modal-actions">
          <button @click="confirmSaveView" class="btn-primary">Save</button>
          <button @click="showSaveDialog = false" class="btn-secondary">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.window-manager {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(8px);
}

/* Toolbar */
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 0.75rem 1rem;
  align-items: center;
}

.toolbar-section {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.section-label {
  font-size: var(--text-base);
  color: var(--text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Buttons */
.btn-module,
.btn-action {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-xl);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  box-shadow: var(--shadow-sm);
}

.btn-module:hover,
.btn-action:hover {
  background: var(--state-hover);
  border-color: var(--primary-color);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-danger:hover:not(:disabled) {
  background: #fee;
  border-color: #ef4444;
  color: #ef4444;
}

/* Arrange group */
.arrange-group {
  display: flex;
  gap: 0.25rem;
  align-items: center;
}

.select-arrange,
.select-view {
  padding: var(--space-2) var(--space-3);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-xl);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  box-shadow: var(--shadow-sm);
}

.select-arrange:hover,
.select-view:hover {
  background: var(--state-hover);
  border-color: var(--primary-color);
  box-shadow: var(--shadow-md);
}

.select-arrange:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Favorite Views */
.favorite-views {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.btn-favorite-view {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-xl);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  box-shadow: var(--shadow-sm);
}

.btn-favorite-view:hover {
  background: var(--state-hover);
  border-color: var(--primary-color);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-favorite-view.active {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

/* System Tray */
.system-tray {
  margin-left: auto;
}

.tray-icons {
  display: flex;
  gap: 0.25rem;
  align-items: center;
}

.btn-tray-icon {
  width: 32px;
  height: 32px;
  padding: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-sm);
}

.btn-tray-icon:hover {
  background: var(--primary-color);
  color: white;
  transform: scale(1.15);
  box-shadow: var(--shadow-md);
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  width: 400px;
  box-shadow: var(--shadow-xl);
}

.modal h3 {
  margin: 0 0 1rem 0;
  color: var(--text-primary);
}

.input-view-name {
  width: 100%;
  padding: var(--space-3);
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-xl);
  margin-bottom: var(--space-5);
  transition: all var(--duration-fast) var(--ease-out);
}

.input-view-name:focus {
  outline: none;
  border-color: var(--state-focus-border);
  background: var(--state-focus-bg);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.modal-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

.btn-primary,
.btn-secondary {
  padding: var(--space-2) var(--space-5);
  border-radius: var(--radius-md);
  font-size: var(--text-xl);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  font-weight: var(--font-medium);
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  border: none;
  box-shadow: var(--shadow-sm);
}

.btn-primary:hover {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-secondary {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
}
</style>
