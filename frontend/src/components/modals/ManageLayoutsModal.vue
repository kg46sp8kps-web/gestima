<script setup lang="ts">
/**
 * ManageLayoutsModal - Manage saved window layouts
 * Actions: Delete, Rename, Toggle Favorite, Set as Default
 */

import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useWindowsStore } from '@/stores/windows'
import { Star, Trash2, Edit3, Check, X, FolderOpen } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import { confirm, alert } from '@/composables/useDialog'

interface Props {
  show: boolean
}

interface Emits {
  (e: 'close'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const store = useWindowsStore()

// Keyboard handler
const handleKeydown = (e: KeyboardEvent) => {
  if (!props.show) return
  // Only handle Escape when not editing (editing has its own keyboard handlers)
  if (e.key === 'Escape' && !editingLayoutId.value) {
    handleClose()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

// Rename state
const editingLayoutId = ref<string | null>(null)
const editingName = ref('')

function startRename(layoutId: string, currentName: string) {
  editingLayoutId.value = layoutId
  editingName.value = currentName
}

function confirmRename() {
  if (!editingLayoutId.value || !editingName.value.trim()) return

  const layout = store.savedViews.find(v => v.id === editingLayoutId.value)
  if (layout) {
    layout.name = editingName.value.trim()
    layout.updatedAt = new Date().toISOString()
  }

  editingLayoutId.value = null
  editingName.value = ''
}

function cancelRename() {
  editingLayoutId.value = null
  editingName.value = ''
}

async function toggleFavorite(layoutId: string) {
  const view = store.savedViews.find(v => v.id === layoutId)
  if (!view) return

  // If marking as favorite, check max 3 limit
  if (!view.favorite) {
    const currentFavoritesCount = store.savedViews.filter(v => v.favorite).length
    if (currentFavoritesCount >= 3) {
      await alert({
        title: 'Limit oblíbených',
        message: 'Maximum 3 favorite layouts allowed. Unmark another layout first.',
        type: 'warning'
      })
      return
    }
  }

  store.toggleFavoriteView(layoutId)
}

function setAsDefault(layoutId: string) {
  const isCurrentDefault = store.defaultLayoutId === layoutId
  store.setDefaultLayout(isCurrentDefault ? null : layoutId)
}

async function deleteLayout(layoutId: string) {
  const confirmed = await confirm({
    title: 'Smazat layout?',
    message: 'Opravdu chcete smazat tento layout?\n\nTato akce je nevratná!',
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })

  if (confirmed) {
    store.deleteView(layoutId)
  }
}

function loadLayout(layoutId: string) {
  store.loadView(layoutId)
  handleClose()
}

function handleClose() {
  cancelRename()
  emit('close')
}
</script>

<template>
  <Transition name="backdrop-fade">
    <div v-if="show" class="modal-overlay" @click="handleClose">
      <div class="modal-container" @click.stop>
        <div class="modal-header">
          <h2>Manage Layouts</h2>
          <button class="close-btn" @click="handleClose" title="Close">
            <X :size="ICON_SIZE.STANDARD" />
          </button>
        </div>

        <div class="modal-body">
          <div v-if="store.savedViews.length === 0" class="empty-state">
            <p>No saved layouts yet.</p>
          </div>

          <div v-else class="layouts-list">
            <div
              v-for="layout in store.savedViews"
              :key="layout.id"
              class="layout-row"
            >
              <!-- Name or Edit Input -->
              <div class="layout-name">
                <input
                  v-if="editingLayoutId === layout.id"
                  v-model="editingName"
                  type="text"
                  class="rename-input"
                  @keyup.enter="confirmRename"
                  @keyup.escape="cancelRename"
                  autofocus
                />
                <span v-else class="name-text">{{ layout.name }}</span>
              </div>

              <!-- Actions -->
              <div class="layout-actions">
                <!-- Rename: Confirm/Cancel or Edit -->
                <template v-if="editingLayoutId === layout.id">
                  <button
                    class="action-btn btn-success"
                    @click="confirmRename"
                    title="Confirm"
                  >
                    <Check :size="ICON_SIZE.SMALL" />
                  </button>
                  <button
                    class="action-btn btn-secondary"
                    @click="cancelRename"
                    title="Cancel"
                  >
                    <X :size="ICON_SIZE.SMALL" />
                  </button>
                </template>
                <template v-else>
                  <!-- Load Layout -->
                  <button
                    class="action-btn btn-load"
                    @click="loadLayout(layout.id)"
                    title="Load Layout"
                  >
                    <FolderOpen :size="ICON_SIZE.SMALL" />
                  </button>

                  <!-- Toggle Favorite -->
                  <button
                    class="action-btn btn-favorite"
                    :class="{ active: layout.favorite }"
                    @click="toggleFavorite(layout.id)"
                    title="Toggle Favorite"
                  >
                    <Star :size="ICON_SIZE.SMALL" :fill="layout.favorite ? 'currentColor' : 'none'" />
                  </button>

                  <!-- Set as Default -->
                  <button
                    class="action-btn btn-default"
                    :class="{ active: store.defaultLayoutId === layout.id }"
                    @click="setAsDefault(layout.id)"
                    title="Set as Default"
                  >
                    <Check :size="ICON_SIZE.SMALL" />
                  </button>

                  <!-- Rename -->
                  <button
                    class="action-btn btn-edit"
                    @click="startRename(layout.id, layout.name)"
                    title="Rename"
                  >
                    <Edit3 :size="ICON_SIZE.SMALL" />
                  </button>

                  <!-- Delete -->
                  <button
                    class="action-btn btn-delete"
                    @click="deleteLayout(layout.id)"
                    title="Delete"
                  >
                    <Trash2 :size="ICON_SIZE.SMALL" />
                  </button>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>

.modal-container {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  width: 600px;
  max-height: 70vh;
  box-shadow: var(--shadow-xl);
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--border-default);
}

.modal-header h2 {
  margin: 0;
  font-size: var(--text-2xl);
  color: var(--text-primary);
  font-weight: 600;
}

.close-btn {
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

.close-btn:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
}

.layouts-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.layout-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  background: var(--bg-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  transition: all var(--duration-fast) var(--ease-out);
}

.layout-row:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
}

.layout-name {
  flex: 1;
  min-width: 0;
}

.name-text {
  font-size: var(--text-base);
  color: var(--text-primary);
  font-weight: 500;
}

.rename-input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-base);
  transition: all var(--duration-fast) var(--ease-out);
}

.rename-input:focus {
  outline: none;
  border-color: var(--brand);
}

.layout-actions {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.action-btn {
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

.action-btn:hover {
  background: var(--state-hover);
  border-color: var(--border-strong);
}

.btn-load:hover {
  color: var(--color-info);
  border-color: var(--color-info);
  background: rgba(59, 130, 246, 0.1);
}

.btn-favorite.active {
  color: var(--status-warn);
  border-color: var(--status-warn);
}

.btn-default.active {
  color: var(--status-ok);
  border-color: var(--status-ok);
  background: rgba(16, 185, 129, 0.1);
}

.btn-edit:hover {
  color: var(--color-info);
  border-color: var(--color-info);
}

.btn-delete:hover {
  color: var(--status-error);
  border-color: var(--status-error);
  background: rgba(239, 68, 68, 0.1);
}

/* Transition */
.backdrop-fade-enter-active,
.backdrop-fade-leave-active {
  transition: opacity 0.3s ease;
}

.backdrop-fade-enter-from,
.backdrop-fade-leave-to {
  opacity: 0;
}
</style>
