<script setup lang="ts">
/**
 * PartDetailPanel.vue - Part detail with Design System patterns
 *
 * Pattern: Info Ribbon + Icon Toolbar + Action Buttons Grid
 * @see docs/reference/DESIGN-SYSTEM.md
 */

import { ref, onMounted, watch } from 'vue'
import type { Part, PartUpdate, PartCreate } from '@/types/part'
import type { LinkingGroup } from '@/stores/windows'
import DrawingsManagementModal from './DrawingsManagementModal.vue'
import CopyPartModal from './CopyPartModal.vue'
import { updatePart, deletePart } from '@/api/parts'
import { usePartsStore } from '@/stores/parts'
import { useAuthStore } from '@/stores/auth'
import { Edit, Copy, Trash2, Save, X } from 'lucide-vue-next'
import { PricingIcon, DrawingIcon } from '@/config/icons'
import { Layers } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import { confirm, alert } from '@/composables/useDialog'
import { partStatusLabel, partStatusDotClass, partSourceLabel, partSourceDotClass } from '@/utils/partStatus'

interface Props {
  part: Part
  linkingGroup?: LinkingGroup
  orientation?: 'vertical' | 'horizontal'
  showActions?: boolean
  /** Pokud true, panel se otevře rovnou v edit módu (pro nový díl id=-1) */
  editOnMount?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  orientation: 'vertical',
  showActions: true,
  editOnMount: false
})

const emit = defineEmits<{
  'open-technology': []
  'open-pricing': []
  'open-drawing': [drawingId?: number]
  'refresh': []
  /** Emitováno po úspěšném vytvoření nového dílu (id=-1 workflow) */
  'created': [part: Part]
  /** Emitováno při zrušení create módu */
  'cancel-create': []
}>()

const authStore = useAuthStore()
const partsStore = usePartsStore()

// Je to nový (dosud neuložený) díl?
const isNew = () => props.part.id === -1

// Edit state
const isEditing = ref(false)
const editForm = ref({
  article_number: '',
  drawing_number: '',
  name: '',
  customer_revision: '',
  status: 'draft' as string
})

// Modals
const showDrawingsModal = ref(false)
const showCopyModal = ref(false)

onMounted(() => {
  if (props.editOnMount || isNew()) {
    startEdit()
  }
})

// Při switchi na nový díl (id=-1) okamžitě otevři edit — prop se mění, komponent se neremountuje
watch(() => props.part.id, (newId) => {
  if (newId === -1) {
    startEdit()
  } else {
    // Reset edit stavu při přepnutí na jiný díl
    isEditing.value = false
  }
})

function startEdit() {
  editForm.value = {
    article_number: props.part.article_number || '',
    drawing_number: props.part.drawing_number || '',
    name: props.part.name || '',
    customer_revision: props.part.customer_revision || '',
    status: props.part.status || 'draft'
  }
  isEditing.value = true
}

async function saveEdit() {
  const articleNumber = editForm.value.article_number.trim()
  if (!articleNumber) {
    await alert({ title: 'Chyba validace', message: 'Artikl je povinný údaj!', type: 'warning' })
    return
  }

  try {
    if (isNew()) {
      // CREATE — přes store (unshift do listu + success toast)
      const newPartData: PartCreate = {
        article_number: editForm.value.article_number || undefined,
        name: editForm.value.name || undefined,
        drawing_number: editForm.value.drawing_number || undefined,
        customer_revision: editForm.value.customer_revision || undefined,
      }
      const created = await partsStore.createPart(newPartData)
      isEditing.value = false
      emit('created', created)
    } else {
      // UPDATE — existující díl
      const updateData: PartUpdate = {
        article_number: editForm.value.article_number,
        drawing_number: editForm.value.drawing_number,
        name: editForm.value.name,
        customer_revision: editForm.value.customer_revision,
        status: editForm.value.status as 'draft' | 'active' | 'archived',
        version: props.part.version
      }
      await updatePart(props.part.part_number, updateData)
      isEditing.value = false
      emit('refresh')
    }
  } catch (error: unknown) {
    const err = error as Error
    await alert({
      title: 'Chyba',
      message: `Chyba při ukládání: ${err.message || 'Neznámá chyba'}`,
      type: 'error'
    })
  }
}

function cancelEdit() {
  if (isNew()) {
    emit('cancel-create')
    return
  }
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
  } catch (error: unknown) {
    const err = error as Error
    console.error('Failed to delete part:', error)
    await alert({
      title: 'Chyba',
      message: `Chyba při mazání: ${err.message || 'Neznámá chyba'}`,
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

// Status/source helpers — importováno z @/utils/partStatus (single source of truth)
const statusDotClass = partStatusDotClass
const statusLabel = partStatusLabel
const sourceDotClass = partSourceDotClass
const sourceLabel = partSourceLabel

function handleDrawingClick() {
  if (props.part.drawing_path || props.part.file_id) {
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
        <!-- Číslo dílu — skryté pro nový (dosud neuložený) díl -->
        <div v-if="!isNew()" class="info-card">
          <label>Číslo dílu</label>
          <span class="value">{{ part.part_number }}</span>
        </div>

        <div class="info-card">
          <label>Artikl<span v-if="isEditing" class="required">*</span></label>
          <input
            v-if="isEditing"
            v-model="editForm.article_number"
            class="edit-input"
            placeholder="Povinný údaj"
            :autofocus="isNew()"
          />
          <span v-else class="value">{{ part.article_number || '-' }}</span>
        </div>

        <div class="info-card">
          <label>Název</label>
          <input
            v-if="isEditing"
            v-model="editForm.name"
            class="edit-input"
            placeholder="Název..."
          />
          <span v-else class="value">{{ part.name || '-' }}</span>
        </div>

        <div class="info-card">
          <label>Číslo výkresu</label>
          <input
            v-if="isEditing"
            v-model="editForm.drawing_number"
            class="edit-input"
            placeholder="Číslo výkresu..."
          />
          <span v-else class="value">{{ part.drawing_number || '-' }}</span>
        </div>

        <div class="info-card">
          <label>Revize zákazníka</label>
          <input
            v-if="isEditing"
            v-model="editForm.customer_revision"
            class="edit-input"
            placeholder="Revize..."
          />
          <span v-else class="value">{{ part.customer_revision || '-' }}</span>
        </div>

        <div class="info-card">
          <label>Stav</label>
          <select v-if="isEditing && !isNew()" v-model="editForm.status" class="edit-input">
            <option value="draft">Rozpracovaný</option>
            <option value="active">Aktivní</option>
            <option value="archived">Archivovaný</option>
            <option value="quote">Nabídka</option>
          </select>
          <span v-else class="value">
            <span class="dot" :class="statusDotClass(part.status)"></span>
            {{ statusLabel(part.status) }}
          </span>
        </div>

        <!-- Skrýt read-only metadata pro nový díl -->
        <template v-if="!isNew()">
          <div class="info-card">
            <label>Verze</label>
            <span class="value">{{ part.version }}</span>
          </div>

          <div class="info-card">
            <label>Zdroj</label>
            <span class="value">
              <span class="dot" :class="sourceDotClass(part.source)"></span>
              {{ sourceLabel(part.source) }}
            </span>
          </div>

          <div class="info-card">
            <label>Vytvořil</label>
            <span class="value">{{ part.created_by_name || '-' }}</span>
          </div>
        </template>
      </div>

      <!-- ICON TOOLBAR -->
      <div class="icon-toolbar">
        <template v-if="isEditing">
          <button class="icon-btn icon-btn-save" @click="saveEdit" title="Uložit">
            <Save :size="ICON_SIZE.STANDARD" />
          </button>
          <button class="icon-btn" @click="cancelEdit" title="Zrušit">
            <X :size="ICON_SIZE.STANDARD" />
          </button>
        </template>
        <template v-else>
          <button
            v-if="authStore.isAdmin"
            class="icon-btn"
            @click="startEdit"
            title="Upravit"
          >
            <Edit :size="ICON_SIZE.STANDARD" />
          </button>
          <button v-if="!isNew()" class="icon-btn" @click="handleCopy" title="Kopírovat">
            <Copy :size="ICON_SIZE.STANDARD" />
          </button>
          <button
            v-if="authStore.isAdmin && !isNew()"
            class="icon-btn icon-btn-danger"
            @click="handleDelete"
            title="Smazat"
          >
            <Trash2 :size="ICON_SIZE.STANDARD" />
          </button>
        </template>
      </div>
    </div>

    <!-- ACTIONS SECTION -->
    <div v-if="showActions" class="actions-section">
      <h4>Actions</h4>

      <div class="actions-grid">
        <button class="action-button" @click="$emit('open-technology')" title="Technologie">
          <Layers :size="ICON_SIZE.XLARGE" class="action-icon" />
          <span class="action-label">Technologie</span>
        </button>

        <button class="action-button" @click="$emit('open-pricing')" title="Ceny">
          <PricingIcon :size="ICON_SIZE.XLARGE" class="action-icon" />
          <span class="action-label">Ceny</span>
        </button>

        <button
          class="action-button"
          @click="handleDrawingClick"
          @contextmenu="handleDrawingRightClick"
          title="Klikni = otevři výkres | Pravé tlačítko = správa výkresů"
        >
          <DrawingIcon :size="ICON_SIZE.XLARGE" class="action-icon" />
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

/* === INFO RIBBON — local customization ONLY === */

/* Inline color dot */
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
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
  border-top: 1px solid var(--border-default);
}

/* === EDIT INPUTS === */
.edit-input {
  width: 100%;
  padding: var(--space-2);
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
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
  border-top: 2px solid var(--border-default);
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

</style>
