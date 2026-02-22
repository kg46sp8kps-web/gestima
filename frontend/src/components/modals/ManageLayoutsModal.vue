<script setup lang="ts">
/**
 * ManageLayoutsModal - Manage saved window layouts
 * Actions: Delete, Rename, Toggle Favorite, Set as Default
 */

import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useWorkspaceStore } from '@/stores/workspace'
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

const store = useWorkspaceStore()

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
  const isCurrentDefault = store.defaultViewId === layoutId
  store.setDefaultView(isCurrentDefault ? null : layoutId)
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
                    :class="{ active: store.defaultViewId === layout.id }"
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
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: 8px;
  width: 600px;
  max-height: 70vh;
  box-shadow: 0 12px 40px rgba(0,0,0,0.7);
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--b2);
}

.modal-header h2 {
  margin: 0;
  font-size: 16px;
  color: var(--t1);
  font-weight: 600;
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  color: var(--t1);
  cursor: pointer;
  transition: all 100ms cubic-bezier(0,0,0.2,1);
}

.close-btn:hover {
  background: var(--b1);
  border-color: var(--b3);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.layouts-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.layout-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--pad) 12px;
  background: var(--raised);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  transition: all 100ms cubic-bezier(0,0,0.2,1);
}

.layout-row:hover {
  background: var(--b1);
  border-color: var(--b3);
}

.layout-name {
  flex: 1;
  min-width: 0;
}

.name-text {
  font-size: var(--fs);
  color: var(--t1);
  font-weight: 500;
}

.rename-input {
  width: 100%;
  padding: 6px var(--pad);
  background: var(--base);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  color: var(--t1);
  font-size: var(--fs);
  transition: all 100ms cubic-bezier(0,0,0.2,1);
}

.rename-input:focus {
  outline: none;
  border-color: var(--red);
}

.layout-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  color: var(--t1);
  cursor: pointer;
  transition: all 100ms cubic-bezier(0,0,0.2,1);
}

.action-btn:hover {
  background: var(--b1);
  border-color: var(--b3);
}

.btn-load:hover {
  color: var(--t3);
  border-color: var(--t3);
  background: rgba(37,99,235,0.1);
}

.btn-favorite.active {
  color: var(--warn);
  border-color: var(--warn);
}

.btn-default.active {
  color: var(--ok);
  border-color: var(--ok);
  background: rgba(52,211,153,0.1);
}

.btn-edit:hover {
  color: var(--t3);
  border-color: var(--t3);
}

.btn-delete:hover {
  color: var(--err);
  border-color: var(--err);
  background: rgba(248,113,113,0.1);
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
