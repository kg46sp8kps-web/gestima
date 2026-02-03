<script setup lang="ts">
/**
 * PartDetailPanel.vue - Part detail with UI-BIBLE pattern
 *
 * Pattern: Info Ribbon + Icon Toolbar + Action Buttons Grid
 * @see docs/guides/UI-BIBLE-V8.md
 */

import { ref } from 'vue'
import type { Part, PartUpdate } from '@/types/part'
import type { LinkingGroup } from '@/stores/windows'
import DrawingsManagementModal from './DrawingsManagementModal.vue'
import CopyPartModal from './CopyPartModal.vue'
import { updatePart, deletePart } from '@/api/parts'
import { useAuthStore } from '@/stores/auth'
import { Edit, Copy, Trash2, Package, Settings, DollarSign, FileText, Save, X } from 'lucide-vue-next'
import { confirm, alert } from '@/composables/useDialog'

interface Props {
  part: Part
  linkingGroup?: LinkingGroup
  orientation?: 'vertical' | 'horizontal'
}

const props = withDefaults(defineProps<Props>(), {
  orientation: 'vertical'
})

const emit = defineEmits<{
  'open-material': []
  'open-operations': []
  'open-pricing': []
  'open-drawing': [drawingId?: number]
  'refresh': []
}>()

const authStore = useAuthStore()

// Edit state
const isEditing = ref(false)
const editForm = ref({
  article_number: '',
  drawing_number: '',
  name: '',
  customer_revision: ''
})

// Modals
const showDrawingsModal = ref(false)
const showCopyModal = ref(false)

function startEdit() {
  editForm.value = {
    article_number: props.part.article_number || '',
    drawing_number: props.part.drawing_number || '',
    name: props.part.name || '',
    customer_revision: props.part.customer_revision || ''
  }
  isEditing.value = true
}

async function saveEdit() {
  try {
    const updateData: PartUpdate = {
      article_number: editForm.value.article_number,
      drawing_number: editForm.value.drawing_number,
      name: editForm.value.name,
      customer_revision: editForm.value.customer_revision,
      version: props.part.version
    }
    await updatePart(props.part.part_number, updateData)
    isEditing.value = false
    emit('refresh')
  } catch (error: any) {
    console.error('Failed to update part:', error)
    await alert({
      title: 'Chyba',
      message: `Chyba při ukládání: ${error.message || 'Neznámá chyba'}`,
      type: 'error'
    })
  }
}

function cancelEdit() {
  isEditing.value = false
}

async function handleDelete() {
  const confirmed = await confirm({
    title: 'Smazat díl?',
    message: `Opravdu chcete smazat díl ${props.part.part_number}?\n\nTato akce je nevratná!`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  try {
    await deletePart(props.part.part_number)
    emit('refresh')
  } catch (error: any) {
    console.error('Failed to delete part:', error)
    await alert({
      title: 'Chyba',
      message: `Chyba při mazání: ${error.message || 'Neznámá chyba'}`,
      type: 'error'
    })
  }
}

function handleCopy() {
  showCopyModal.value = true
}

function handleCopySuccess() {
  emit('refresh')
}

function handleDrawingClick() {
  if (props.part.drawing_path) {
    emit('open-drawing')
  } else {
    showDrawingsModal.value = true
  }
}

function handleDrawingRightClick(e: MouseEvent) {
  e.preventDefault()
  showDrawingsModal.value = true
}

function handleOpenDrawing(drawingId?: number) {
  emit('open-drawing', drawingId)
  showDrawingsModal.value = false
}
</script>

<template>
  <div class="part-detail-panel">
    <!-- INFO RIBBON -->
    <div class="info-ribbon" :class="{ 'editing': isEditing }">
      <!-- INFO GRID -->
      <div class="info-grid">
        <div class="info-card">
          <label>Part Number</label>
          <span class="value">{{ part.part_number }}</span>
        </div>

        <div class="info-card">
          <label>Article Number</label>
          <input
            v-if="isEditing"
            v-model="editForm.article_number"
            class="edit-input"
            placeholder="Artikl..."
          />
          <span v-else class="value">{{ part.article_number || '-' }}</span>
        </div>

        <div class="info-card">
          <label>Drawing Number</label>
          <input
            v-if="isEditing"
            v-model="editForm.drawing_number"
            class="edit-input"
            placeholder="Číslo výkresu..."
          />
          <span v-else class="value">{{ part.drawing_number || '-' }}</span>
        </div>

        <div class="info-card">
          <label>Customer Revision</label>
          <input
            v-if="isEditing"
            v-model="editForm.customer_revision"
            class="edit-input"
            placeholder="Revize..."
          />
          <span v-else class="value">{{ part.customer_revision || '-' }}</span>
        </div>

        <div class="info-card">
          <label>Name</label>
          <input
            v-if="isEditing"
            v-model="editForm.name"
            class="edit-input"
            placeholder="Název..."
          />
          <span v-else class="value">{{ part.name || '-' }}</span>
        </div>

        <div class="info-card">
          <label>Version</label>
          <span class="value">{{ part.version }}</span>
        </div>

        <div class="info-card">
          <label>Created By</label>
          <span class="value">{{ part.created_by_name || '-' }}</span>
        </div>

        <div class="info-card">
          <label>Length</label>
          <span class="value">{{ part.length }} mm</span>
        </div>
      </div>

      <!-- ICON TOOLBAR (Edit mode) -->
      <div v-if="isEditing" class="icon-toolbar">
        <button class="action-button action-button-primary" @click="saveEdit">
          <Save :size="32" class="action-icon" />
          <span class="action-label">Uložit</span>
        </button>
        <button class="action-button action-button-secondary" @click="cancelEdit">
          <X :size="32" class="action-icon" />
          <span class="action-label">Zrušit</span>
        </button>
      </div>

      <!-- ICON TOOLBAR (View mode) -->
      <div v-else class="icon-toolbar">
        <button
          v-if="authStore.isAdmin"
          class="icon-btn"
          @click="startEdit"
          title="Upravit"
        >
          <Edit :size="15" />
        </button>
        <button class="icon-btn" @click="handleCopy" title="Kopírovat">
          <Copy :size="15" />
        </button>
        <button
          v-if="authStore.isAdmin"
          class="icon-btn icon-btn-danger"
          @click="handleDelete"
          title="Smazat"
        >
          <Trash2 :size="15" />
        </button>
      </div>
    </div>

    <!-- ACTIONS SECTION -->
    <div class="actions-section">
      <h4>Actions</h4>

      <div class="actions-grid">
        <button class="action-button" @click="$emit('open-material')" title="Materiál">
          <Package :size="32" class="action-icon" />
          <span class="action-label">Materiál</span>
        </button>

        <button class="action-button" @click="$emit('open-operations')" title="Operace">
          <Settings :size="32" class="action-icon" />
          <span class="action-label">Operace</span>
        </button>

        <button class="action-button" @click="$emit('open-pricing')" title="Ceny">
          <DollarSign :size="32" class="action-icon" />
          <span class="action-label">Ceny</span>
        </button>

        <button
          class="action-button"
          @click="handleDrawingClick"
          @contextmenu="handleDrawingRightClick"
          title="Klikni = otevři výkres | Pravé tlačítko = správa výkresů"
        >
          <FileText :size="32" class="action-icon" />
          <span class="action-label">Výkres</span>
        </button>
      </div>
    </div>

    <!-- MODALS -->
    <DrawingsManagementModal
      v-model="showDrawingsModal"
      :part-number="part.part_number"
      @refresh="emit('refresh')"
      @open-drawing="handleOpenDrawing"
    />

    <CopyPartModal
      v-model="showCopyModal"
      :part-number="part.part_number"
      :source-part="part"
      @success="handleCopySuccess"
    />
  </div>
</template>

<style scoped>
/* === CONTAINER === */
.part-detail-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  padding: var(--space-5);
  container-type: inline-size;
  container-name: part-detail;
}

/* === INFO RIBBON === */
.info-ribbon {
  position: relative;
  padding: var(--space-5);
  background: var(--bg-surface);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-6);
  transition: all var(--duration-normal);
}

.info-ribbon.editing {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(153, 27, 27, 0.1);
}

/* === INFO GRID === */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-3);
}

.info-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.info-card label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-card .value {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
}

/* === ICON TOOLBAR === */
.icon-toolbar {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  justify-content: center;
  margin-top: 2px;
  margin-bottom: calc(-1 * var(--space-5) + 2px);
  padding-top: 2px;
  padding-bottom: 2px;
  border-top: 1px solid var(--border-color);
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all var(--duration-fast);
}

.icon-btn:hover {
  color: var(--color-primary);
  transform: scale(1.1);
}

.icon-btn-danger:hover {
  color: #ef4444;
}

/* === EDIT INPUTS === */
.edit-input {
  width: 100%;
  padding: var(--space-2);
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  background: var(--bg-base);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  transition: all var(--duration-fast);
}

.edit-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(153, 27, 27, 0.1);
}

/* === ACTIONS SECTION === */
.actions-section {
  margin-top: var(--space-6);
  padding-top: var(--space-5);
  border-top: 2px solid var(--border-color);
}

.actions-section h4 {
  margin: 0 0 var(--space-4) 0;
  font-size: var(--text-lg);
  color: var(--text-primary);
  font-weight: 600;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
  align-content: start;
}

/* Responsive: 2 columns on narrow containers */
@container part-detail (max-width: 500px) {
  .actions-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* === ACTION BUTTONS === */
.action-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 2px solid var(--border-default);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--duration-normal);
}

.action-button:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.action-icon {
  color: var(--color-primary);
}

.action-label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
}

/* Primary action (Save) */
.action-button-primary {
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.action-button-primary .action-icon,
.action-button-primary .action-label {
  color: white;
}

.action-button-primary:hover {
  background: #7f1d1d;
  border-color: #7f1d1d;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(153, 27, 27, 0.3);
}

/* Secondary action (Cancel) */
.action-button-secondary .action-icon {
  color: var(--text-secondary);
}

.action-button-secondary:hover {
  border-color: var(--text-secondary);
}
</style>
