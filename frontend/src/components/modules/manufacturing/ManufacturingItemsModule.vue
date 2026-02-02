<script setup lang="ts">
/**
 * Manufacturing Items Module - Split-pane layout
 *
 * LEFT: Parts list
 * RIGHT: Part detail
 */

import { ref, computed, onMounted } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useWindowsStore } from '@/stores/windows'
import { useWindowContextStore } from '@/stores/windowContext'
import { usePartLayoutSettings } from '@/composables/usePartLayoutSettings'
import PartListPanel from '@/components/modules/parts/PartListPanel.vue'
import CopyPartModal from '@/components/modules/parts/CopyPartModal.vue'
import DrawingsManagementModal from '@/components/modules/parts/DrawingsManagementModal.vue'
import type { Part, PartUpdate } from '@/types/part'
import type { LinkingGroup } from '@/stores/windows'
import { Package, Settings, DollarSign, FileText, Edit, Trash2, Save, X, Copy } from 'lucide-vue-next'
import { updatePart, createPart, deletePart } from '@/api/parts'
import type { PartCreate } from '@/types/part'

interface Props {
  partNumber?: string
  linkingGroup?: LinkingGroup
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'select-part': [partNumber: string]
}>()

// Stores
const partsStore = usePartsStore()
const windowsStore = useWindowsStore()
const contextStore = useWindowContextStore()

// Layout settings
const { layoutMode } = usePartLayoutSettings('manufacturing-items')

// Panel size state
const panelSize = ref(320)
const isDragging = ref(false)

// Selected part
const selectedPart = ref<Part | null>(null)
const listPanelRef = ref<InstanceType<typeof PartListPanel> | null>(null)

// Edit mode
const isEditing = ref(false)
const editForm = ref({
  article_number: '',
  name: '',
  drawing_number: '',
  customer_revision: '',
  material: '',
  weight_kg: null as number | null,
  description: ''
})

// Copy modal
const showCopyModal = ref(false)

// Drawings modal
const showDrawingsModal = ref(false)

// Load parts and setup
onMounted(async () => {
  // Load saved panel size
  const stored = localStorage.getItem('manufacturingItemsPanelSize')
  if (stored) {
    const size = parseInt(stored, 10)
    if (!isNaN(size) && size >= 250 && size <= 1000) {
      panelSize.value = size
    }
  }

  // Load parts
  await partsStore.fetchParts()

  // Auto-select if partNumber provided
  if (props.partNumber) {
    const part = partsStore.parts.find(p => p.part_number === props.partNumber)
    if (part) {
      selectedPart.value = part
      listPanelRef.value?.setSelection(part.id)
    }
  }
})

// Handle part selection
function handleSelectPart(part: Part) {
  selectedPart.value = part

  // Update window context for linking
  if (props.linkingGroup) {
    contextStore.setContext(props.linkingGroup, part.id, part.part_number, part.article_number)
  }

  emit('select-part', part.part_number)
}

function handleCreateNew() {
  // Create temporary virtual part (not saved to DB yet)
  const virtualPart: Part = {
    id: -1, // Negative ID indicates virtual/unsaved part
    part_number: 'NOVÝ',
    article_number: '',
    name: '',
    drawing_path: null,
    drawing_number: null,
    customer_revision: null,
    revision: 'A',
    status: 'draft',
    length: 0,
    notes: '',
    material: null,
    weight_kg: null,
    description: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    version: 0,
    created_by_name: null
  }

  // Set as selected and start edit mode
  selectedPart.value = virtualPart
  listPanelRef.value?.setSelection(-1)
  startEdit()
}

// Window actions - open linked modules
function openMaterialWindow() {
  if (!selectedPart.value) return

  const title = `Materiál položky - ${selectedPart.value.part_number}`
  windowsStore.openWindow('part-material', title, props.linkingGroup || null)
}

function openOperationsWindow() {
  if (!selectedPart.value) return

  const title = `Operace položky - ${selectedPart.value.part_number}`
  windowsStore.openWindow('part-operations', title, props.linkingGroup || null)
}

function openPricingWindow() {
  if (!selectedPart.value) return

  const title = `Ceny položky - ${selectedPart.value.part_number}`
  windowsStore.openWindow('part-pricing', title, props.linkingGroup || null)
}

// Edit handlers
function startEdit() {
  if (!selectedPart.value) return

  // Copy current values to edit form
  editForm.value = {
    article_number: selectedPart.value.article_number || '',
    name: selectedPart.value.name || '',
    drawing_number: selectedPart.value.drawing_number || '',
    customer_revision: selectedPart.value.customer_revision || '',
    material: selectedPart.value.material || '',
    weight_kg: selectedPart.value.weight_kg,
    description: selectedPart.value.description || ''
  }

  isEditing.value = true
}

function cancelEdit() {
  isEditing.value = false

  // If canceling creation of new virtual part, clear selection
  if (selectedPart.value?.id === -1) {
    selectedPart.value = null
    listPanelRef.value?.setSelection(null)
  }
}

async function saveEdit() {
  if (!selectedPart.value) return

  // Validate: article_number is required
  const articleNumber = editForm.value.article_number?.trim()
  if (!articleNumber) {
    alert('Artikl je povinný údaj!')
    return
  }

  try {
    // Check if this is a new virtual part (not yet saved to DB)
    const isNewPart = selectedPart.value.id === -1

    if (isNewPart) {
      // Create new part
      const newPartData: PartCreate = {
        article_number: editForm.value.article_number || undefined,
        name: editForm.value.name || undefined,
        drawing_number: editForm.value.drawing_number || undefined,
        customer_revision: editForm.value.customer_revision || undefined
      }

      const createdPart = await createPart(newPartData)

      // Refresh parts list
      await partsStore.fetchParts()

      // Select the newly created part
      const part = partsStore.parts.find(p => p.id === createdPart.id)
      if (part) {
        selectedPart.value = part
        listPanelRef.value?.setSelection(part.id)
      }
    } else {
      // Update existing part
      const updateData: PartUpdate = {
        article_number: editForm.value.article_number || null,
        name: editForm.value.name || null,
        drawing_number: editForm.value.drawing_number || null,
        customer_revision: editForm.value.customer_revision || null,
        version: selectedPart.value.version
      }

      await updatePart(selectedPart.value.part_number, updateData)

      // Refresh the part data
      await partsStore.fetchParts()
      const updatedPart = partsStore.parts.find(p => p.part_number === selectedPart.value?.part_number)
      if (updatedPart) {
        selectedPart.value = updatedPart
      }
    }

    isEditing.value = false
  } catch (error: any) {
    console.error('Failed to save part:', error)
    alert(`Chyba při ukládání: ${error.message || 'Neznámá chyba'}`)
  }
}

// Copy handlers
function openCopyModal() {
  showCopyModal.value = true
}

// Delete handler
async function handleDelete() {
  if (!selectedPart.value) return

  // Don't allow deleting virtual parts (they don't exist in DB yet)
  if (selectedPart.value.id === -1) {
    alert('Tento díl ještě není uložený.')
    return
  }

  // Confirm deletion
  const partInfo = selectedPart.value.article_number || selectedPart.value.part_number
  if (!confirm(`Opravdu chcete smazat díl ${partInfo}?\n\nTato akce je nevratná!`)) {
    return
  }

  try {
    await deletePart(selectedPart.value.part_number)

    // Clear selection and refresh list
    selectedPart.value = null
    listPanelRef.value?.setSelection(null)
    await partsStore.fetchParts()
  } catch (error: any) {
    console.error('Failed to delete part:', error)
    alert(`Chyba při mazání: ${error.message || 'Neznámá chyba'}`)
  }
}

async function handleCopySuccess() {
  // Refresh parts list after copy
  await partsStore.fetchParts()
}

// Drawing handlers
function openDrawingWindow(drawingId?: number) {
  if (!selectedPart.value) return

  // For specific drawing ID, open without linking group (standalone window)
  // For primary drawing, use linking group (context-aware)
  const title = drawingId
    ? `Drawing #${drawingId} - ${selectedPart.value.part_number}`
    : `Drawing - ${selectedPart.value.part_number}`

  // NOTE: drawingId is parsed from title in PartDrawingWindow
  // Pattern: "Drawing #123 - ..." where 123 is drawing_id
  windowsStore.openWindow('part-drawing', title, drawingId ? null : (props.linkingGroup || null))
}

function handleDrawingClick() {
  if (!selectedPart.value) return

  // Left-click: open drawing or upload modal
  if (selectedPart.value.drawing_path) {
    openDrawingWindow()
  } else {
    showDrawingsModal.value = true
  }
}

function handleDrawingRightClick(event: MouseEvent) {
  event.preventDefault()
  // Right-click: always open management modal
  showDrawingsModal.value = true
}

function handleOpenDrawing(drawingId?: number) {
  openDrawingWindow(drawingId)
  showDrawingsModal.value = false
}

async function handleDrawingRefresh() {
  // Refresh the part data
  await partsStore.fetchParts()
  const updatedPart = partsStore.parts.find(p => p.id === selectedPart.value?.id)
  if (updatedPart) {
    selectedPart.value = updatedPart
  }
}

// Resize handler
function startResize(event: MouseEvent) {
  event.preventDefault()
  isDragging.value = true

  const isVertical = layoutMode.value === 'vertical'
  const startPos = isVertical ? event.clientX : event.clientY
  const startSize = panelSize.value

  const onMove = (e: MouseEvent) => {
    const currentPos = isVertical ? e.clientX : e.clientY
    const delta = currentPos - startPos
    const newSize = Math.max(250, Math.min(1000, startSize + delta))
    panelSize.value = newSize
  }

  const onUp = () => {
    isDragging.value = false
    localStorage.setItem('manufacturingItemsPanelSize', panelSize.value.toString())
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

// Computed styles
const layoutClasses = computed(() => ({
  [`layout-${layoutMode.value}`]: true
}))

const resizeCursor = computed(() =>
  layoutMode.value === 'vertical' ? 'col-resize' : 'row-resize'
)
</script>

<template>
  <div class="split-layout" :class="layoutClasses">
    <!-- FIRST PANEL: Parts List -->
    <div class="first-panel" :style="layoutMode === 'vertical' ? { width: `${panelSize}px` } : { height: `${panelSize}px` }">
      <PartListPanel
        ref="listPanelRef"
        :linkingGroup="linkingGroup"
        @select-part="handleSelectPart"
        @create-new="handleCreateNew"
      />
    </div>

    <!-- RESIZE HANDLE -->
    <div
      class="resize-handle"
      :class="{ dragging: isDragging }"
      :style="{ cursor: resizeCursor }"
      @mousedown="startResize"
    ></div>

    <!-- SECOND PANEL: Part Detail -->
    <div v-if="selectedPart" class="second-panel">
      <!-- PART INFO RIBBON -->
      <div class="info-ribbon">
        <div class="info-grid">
          <div class="info-card">
            <label>Interní číslo</label>
            <span class="value">{{ selectedPart.part_number }}</span>
          </div>
          <div class="info-card">
            <label>Artikl<span v-if="isEditing" class="required">*</span></label>
            <input v-if="isEditing" v-model="editForm.article_number" class="edit-input" placeholder="Povinný údaj" />
            <span v-else class="value">{{ selectedPart.article_number || '-' }}</span>
          </div>
          <div class="info-card">
            <label>Název</label>
            <input v-if="isEditing" v-model="editForm.name" class="edit-input" />
            <span v-else class="value">{{ selectedPart.name || '-' }}</span>
          </div>
          <div class="info-card">
            <label>Číslo výkresu</label>
            <input v-if="isEditing" v-model="editForm.drawing_number" class="edit-input" />
            <span v-else class="value">{{ selectedPart.drawing_number || '-' }}</span>
          </div>
          <div class="info-card">
            <label>Zákaznická revize</label>
            <input v-if="isEditing" v-model="editForm.customer_revision" class="edit-input" />
            <span v-else class="value">{{ selectedPart.customer_revision || '-' }}</span>
          </div>
          <div class="info-card">
            <label>Materiál</label>
            <span class="value">{{ selectedPart.material || '-' }}</span>
          </div>
          <div class="info-card">
            <label>Hmotnost</label>
            <span class="value">{{ selectedPart.weight_kg ? `${selectedPart.weight_kg} kg` : '-' }}</span>
          </div>
          <div class="info-card">
            <label>Vytvořeno</label>
            <span class="value">{{ new Date(selectedPart.created_at).toLocaleDateString() }}</span>
          </div>
        </div>

        <div v-if="selectedPart.description || (isEditing && selectedPart.id !== -1)" class="description">
          <label>Popis</label>
          <textarea v-if="isEditing" v-model="editForm.description" class="edit-textarea" rows="3"></textarea>
          <p v-else>{{ selectedPart.description || '-' }}</p>
        </div>

        <!-- Icon toolbar (bottom right) -->
        <div class="icon-toolbar">
          <!-- Edit mode: Save/Cancel -->
          <template v-if="isEditing">
            <button class="icon-btn icon-btn-primary" @click="saveEdit" title="Uložit změny">
              <Save :size="14" />
            </button>
            <button class="icon-btn" @click="cancelEdit" title="Zrušit">
              <X :size="14" />
            </button>
          </template>

          <!-- Normal mode: Edit/Copy/Delete -->
          <template v-else>
            <button class="icon-btn" @click="startEdit" title="Upravit díl">
              <Edit :size="14" />
            </button>
            <button class="icon-btn" @click="openCopyModal" title="Kopírovat díl">
              <Copy :size="14" />
            </button>
            <button class="icon-btn icon-btn-danger" @click="handleDelete" title="Smazat díl">
              <Trash2 :size="14" />
            </button>
          </template>
        </div>
      </div>

      <!-- ACTIONS -->
      <div v-if="!isEditing" class="actions-section">
        <h4>Actions</h4>

        <!-- Normal mode: All actions -->
        <div class="actions-grid">
          <button class="action-button" @click="openMaterialWindow" title="Materiál">
            <Package :size="26" class="action-icon" />
            <span class="action-label">Materiál</span>
          </button>
          <button class="action-button" @click="openOperationsWindow" title="Operace">
            <Settings :size="26" class="action-icon" />
            <span class="action-label">Operace</span>
          </button>
          <button class="action-button" @click="openPricingWindow" title="Ceny">
            <DollarSign :size="26" class="action-icon" />
            <span class="action-label">Ceny</span>
          </button>
          <button
            class="action-button"
            @click="handleDrawingClick"
            @contextmenu="handleDrawingRightClick"
            title="Klikni = otevři výkres | Pravé tlačítko = správa výkresů"
          >
            <FileText :size="26" class="action-icon" />
            <span class="action-label">Výkres</span>
          </button>
        </div>
      </div>

      <!-- Copy Part Modal -->
      <CopyPartModal
        v-model="showCopyModal"
        :part-number="selectedPart.part_number"
        :source-part="selectedPart"
        @success="handleCopySuccess"
      />

      <!-- Drawings Management Modal -->
      <DrawingsManagementModal
        v-model="showDrawingsModal"
        :part-number="selectedPart.part_number"
        @refresh="handleDrawingRefresh"
        @open-drawing="handleOpenDrawing"
      />
    </div>

    <!-- EMPTY STATE -->
    <div v-else class="empty">
      <p>Select a part from the list to view details</p>
    </div>
  </div>
</template>

<style scoped>
/* === SPLIT LAYOUT === */
.split-layout {
  display: flex;
  gap: 0;
  height: 100%;
  overflow: hidden;
}

.layout-horizontal {
  flex-direction: column;
}

.layout-vertical {
  flex-direction: row;
}

/* === PANELS === */
.first-panel,
.second-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.first-panel {
  flex-shrink: 0;
}

.second-panel {
  flex: 1;
  padding: var(--space-5);
  overflow-y: auto;
  container-type: inline-size;
  container-name: second-panel;
}

/* === RESIZE HANDLE === */
.resize-handle {
  flex-shrink: 0;
  background: var(--border-color);
  transition: background var(--duration-fast);
  position: relative;
  z-index: 10;
}

.layout-vertical .resize-handle {
  width: 4px;
}

.layout-horizontal .resize-handle {
  height: 4px;
}

.resize-handle:hover,
.resize-handle.dragging {
  background: var(--color-primary);
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

/* Icon toolbar */
.icon-toolbar {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  justify-content: center;
  margin-top: var(--space-4);
  margin-bottom: calc(-1 * var(--space-5) + 2px);
  padding-top: var(--space-3);
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

.icon-btn-primary {
  color: var(--color-primary);
}

.icon-btn-primary:hover {
  color: var(--color-primary);
  background: rgba(153, 27, 27, 0.1);
  transform: scale(1.1);
}

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

.info-card label .required {
  color: var(--color-primary);
  margin-left: var(--space-1);
}

.info-card .value {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
}

.description {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-color);
}

.description label {
  display: block;
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--space-2);
}

.description p {
  margin: 0;
  font-size: var(--text-base);
  color: var(--text-primary);
  line-height: 1.6;
}

/* === EDIT INPUTS === */
.edit-input,
.edit-textarea {
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

.edit-input:focus,
.edit-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(153, 27, 27, 0.1);
}

.edit-textarea {
  resize: vertical;
  font-weight: 400;
  line-height: 1.6;
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

/* Edit mode actions - only 2 buttons */
.edit-actions {
  grid-template-columns: repeat(2, 1fr) !important;
  max-width: 500px;
}

/* Responsive actions grid */
@container second-panel (max-width: 500px) {
  .actions-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* === ACTION BUTTONS === */
.action-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-3);
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
  font-size: var(--text-xs);
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

/* Secondary action (Edit, Cancel) */
.action-button-secondary .action-icon {
  color: var(--text-secondary);
}

.action-button-secondary:hover {
  border-color: var(--text-secondary);
}

/* Danger action (Delete) */
.action-button-danger .action-icon {
  color: #ef4444;
}

.action-button-danger:hover {
  border-color: #ef4444;
  background: #fef2f2;
}

/* === EMPTY STATE === */
.empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  text-align: center;
}

.empty p {
  font-size: var(--text-base);
}
</style>
