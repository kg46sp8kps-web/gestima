<script setup lang="ts">
/**
 * WindowManager - Toolbar for managing windows
 * Open/close windows, arrange to grid, save/load views
 */

import { ref, computed } from 'vue'
import { useWindowsStore, type WindowModule } from '@/stores/windows'

const store = useWindowsStore()

// Available modules
const modules: Array<{ value: WindowModule; label: string; icon: string }> = [
  { value: 'parts-list', label: 'Parts List', icon: '📦' },
  { value: 'part-pricing', label: 'Pricing', icon: '💰' },
  { value: 'part-operations', label: 'Operations', icon: '⚙️' },
  { value: 'part-material', label: 'Material', icon: '🧱' },
  { value: 'batch-sets', label: 'Batch Sets', icon: '📋' }
]

// Save view dialog
const showSaveDialog = ref(false)
const viewName = ref('')

// Arrange mode
const arrangeMode = ref<'grid' | 'horizontal' | 'vertical'>('grid')

function openModule(module: WindowModule, label: string, icon: string) {
  store.openWindow(module, `${icon} ${label}`)
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
          @click="openModule(mod.value, mod.label, mod.icon)"
          class="btn-module"
          :title="`Open ${mod.label}`"
        >
          {{ mod.icon }} {{ mod.label }}
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
            <option value="grid">🔲 Grid</option>
            <option value="horizontal">⬌ Horizontal</option>
            <option value="vertical">⬍ Vertical</option>
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
          💾 Save View
        </button>

        <!-- Views dropdown (all views) -->
        <select
          v-if="store.savedViews.length > 0"
          @change="handleLoadViewFromSelect"
          class="select-view"
        >
          <option value="">📁 Load View...</option>
          <option
            v-for="view in store.savedViews"
            :key="view.id"
            :value="view.id"
          >
            {{ view.favorite ? '⭐' : '' }} {{ view.name }}
          </option>
        </select>

        <button
          @click="handleCloseAll"
          class="btn-action btn-danger"
          title="Close all windows"
          :disabled="store.openWindows.length === 0"
        >
          ❌ Close All
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
            ⭐ {{ view.name }}
          </button>
        </div>
      </div>
    </div>

    <!-- Minimized Windows Bar -->
    <div v-if="store.minimizedWindows.length > 0" class="minimized-bar">
      <label class="section-label">Minimized:</label>
      <button
        v-for="win in store.minimizedWindows"
        :key="win.id"
        @click="store.restoreWindow(win.id)"
        class="btn-minimized"
        :title="`Restore ${win.title}`"
      >
        {{ win.title }}
      </button>
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
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
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
  font-size: 0.75rem;
  color: var(--text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Buttons */
.btn-module,
.btn-action {
  padding: 0.5rem 0.75rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 150ms;
}

.btn-module:hover,
.btn-action:hover {
  background: var(--bg-hover);
  border-color: var(--primary-color);
  transform: translateY(-1px);
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
  padding: 0.5rem 0.75rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 150ms;
}

.select-arrange:hover,
.select-view:hover {
  background: var(--bg-hover);
  border-color: var(--primary-color);
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
  padding: 0.5rem 0.75rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 150ms;
}

.btn-favorite-view:hover {
  background: var(--bg-hover);
  border-color: var(--primary-color);
  transform: translateY(-1px);
}

.btn-favorite-view.active {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

/* Minimized Bar */
.minimized-bar {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  padding: 0.5rem 1rem;
  background: var(--bg-primary);
  border-top: 1px solid var(--border-color);
}

.btn-minimized {
  padding: 0.4rem 0.75rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 150ms;
}

.btn-minimized:hover {
  background: var(--primary-color);
  color: white;
  transform: translateY(-1px);
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
  border-radius: 8px;
  padding: 1.5rem;
  width: 400px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal h3 {
  margin: 0 0 1rem 0;
  color: var(--text-primary);
}

.input-view-name {
  width: 100%;
  padding: 0.75rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.95rem;
  margin-bottom: 1rem;
}

.input-view-name:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.modal-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

.btn-primary,
.btn-secondary {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 150ms;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  border: none;
}

.btn-primary:hover {
  background: #2563eb;
  transform: translateY(-1px);
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--bg-hover);
}
</style>
