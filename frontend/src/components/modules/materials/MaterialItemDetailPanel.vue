<script setup lang="ts">
/**
 * Material Item Detail Panel - Info Ribbon pattern (Design System Pattern 7.3)
 *
 * Displays selected material item with inline edit capability
 * Icon toolbar at bottom: Edit | Copy | Delete
 */

import { ref, watch, computed } from 'vue'
import { Edit, Copy, Trash2, Save, X } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import type { MaterialItem } from '@/types/material'
import { confirm, alert } from '@/composables/useDialog'

interface Props {
  item?: MaterialItem | null
}

const props = withDefaults(defineProps<Props>(), {
  item: null
})

const emit = defineEmits<{
  updated: []
  deleted: []
}>()

// State
const isEditing = ref(false)
const editForm = ref({
  code: '',
  name: '',
  supplier: '',
  supplier_code: '',
  norms: ''
})

// Computed
const shapeLabel = computed(() => {
  const labels: Record<string, string> = {
    round_bar: 'Kruhová tyč',
    square_bar: 'Čtvercová tyč',
    flat_bar: 'Plochá tyč',
    hexagonal_bar: 'Šestihranná tyč',
    plate: 'Deska/Plech',
    tube: 'Trubka',
    casting: 'Odlitek',
    forging: 'Výkovek'
  }
  return labels[props.item?.shape || ''] || props.item?.shape || '-'
})

// Watch for item changes
watch(() => props.item, (newItem) => {
  if (newItem && !isEditing.value) {
    // Reset edit form when item changes
    editForm.value = {
      code: newItem.code || '',
      name: newItem.name || '',
      supplier: newItem.supplier || '',
      supplier_code: newItem.supplier_code || '',
      norms: newItem.norms || ''
    }
  }
}, { immediate: true })

// Methods
function startEdit() {
  if (!props.item) return

  editForm.value = {
    code: props.item.code || '',
    name: props.item.name || '',
    supplier: props.item.supplier || '',
    supplier_code: props.item.supplier_code || '',
    norms: props.item.norms || ''
  }

  isEditing.value = true
}

function cancelEdit() {
  isEditing.value = false
}

async function saveEdit() {
  if (!props.item) return

  try {
    // TODO: Implement API call to update material item
    // await updateMaterialItem(props.item.material_number, editForm.value)

    emit('updated')
    isEditing.value = false
  } catch (error: unknown) {
    const err = error as Error
    console.error('Failed to save material item:', error)
    await alert({
      title: 'Chyba',
      message: `Chyba při ukládání: ${err.message || 'Neznámá chyba'}`,
      type: 'error'
    })
  }
}

async function handleCopy() {
  if (!props.item) return

  // TODO: Implement copy functionality
  await alert({
    title: 'Info',
    message: 'Kopírování materiálové položky zatím není implementováno',
    type: 'info'
  })
}

async function handleDelete() {
  if (!props.item) return

  const confirmed = await confirm({
    title: 'Smazat materiálovou položku?',
    message: `Opravdu chcete smazat materiálovou položku ${props.item.code}?\n\nTato akce je nevratná!`,
    type: 'danger',
    confirmText: 'Smazat',
    cancelText: 'Zrušit'
  })

  if (!confirmed) return

  try {
    // TODO: Implement API call to delete material item
    // await deleteMaterialItem(props.item.material_number)

    emit('deleted')
  } catch (error: unknown) {
    const err = error as Error
    console.error('Failed to delete material item:', error)
    await alert({
      title: 'Chyba',
      message: `Chyba při mazání: ${err.message || 'Neznámá chyba'}`,
      type: 'error'
    })
  }
}

function formatDimension(value: number | null | undefined, unit = 'mm'): string {
  if (value == null) return '-'
  return `${value} ${unit}`
}
</script>

<template>
  <div class="material-detail-panel">
    <div v-if="!item" class="empty">
      <p>Select a material item from the list to view details</p>
    </div>

    <div v-else class="detail-content">
      <!-- INFO RIBBON -->
      <div class="info-ribbon">
        <!-- INFO GRID -->
        <div class="info-grid">
          <div class="info-card">
            <label>Kód</label>
            <input v-if="isEditing" v-model="editForm.code" class="edit-input" />
            <span v-else class="value">{{ item.code || '-' }}</span>
          </div>

          <div class="info-card">
            <label>Název</label>
            <input v-if="isEditing" v-model="editForm.name" class="edit-input" />
            <span v-else class="value">{{ item.name || '-' }}</span>
          </div>

          <div class="info-card">
            <label>Materiál. číslo</label>
            <span class="value">{{ item.material_number }}</span>
          </div>

          <div class="info-card">
            <label>Tvar</label>
            <span class="value">{{ shapeLabel }}</span>
          </div>

          <div class="info-card">
            <label>Průměr</label>
            <span class="value">{{ formatDimension(item.diameter) }}</span>
          </div>

          <div class="info-card">
            <label>Šířka</label>
            <span class="value">{{ formatDimension(item.width) }}</span>
          </div>

          <div class="info-card">
            <label>Tloušťka</label>
            <span class="value">{{ formatDimension(item.thickness) }}</span>
          </div>

          <div class="info-card">
            <label>Tl. stěny</label>
            <span class="value">{{ formatDimension(item.wall_thickness) }}</span>
          </div>

          <div class="info-card">
            <label>Hmotnost/m</label>
            <span class="value">{{ formatDimension(item.weight_per_meter, 'kg/m') }}</span>
          </div>

          <div class="info-card">
            <label>Stand. délka</label>
            <span class="value">{{ formatDimension(item.standard_length) }}</span>
          </div>

          <div class="info-card">
            <label>Normy</label>
            <input v-if="isEditing" v-model="editForm.norms" class="edit-input" />
            <span v-else class="value">{{ item.norms || '-' }}</span>
          </div>

          <div class="info-card">
            <label>Dodavatel</label>
            <input v-if="isEditing" v-model="editForm.supplier" class="edit-input" />
            <span v-else class="value">{{ item.supplier || '-' }}</span>
          </div>

          <div class="info-card">
            <label>Kód dodavatele</label>
            <input v-if="isEditing" v-model="editForm.supplier_code" class="edit-input" />
            <span v-else class="value">{{ item.supplier_code || '-' }}</span>
          </div>

          <div class="info-card">
            <label>Sklad</label>
            <span class="value">
              {{ item.stock_available != null ? `${item.stock_available.toFixed(1)} kg` : '-' }}
            </span>
          </div>
        </div>

        <!-- ICON TOOLBAR -->
        <div class="icon-toolbar">
          <!-- Edit mode: Save/Cancel -->
          <template v-if="isEditing">
            <button class="icon-btn icon-btn-primary" @click="saveEdit" title="Uložit změny">
              <Save :size="ICON_SIZE.STANDARD" />
            </button>
            <button class="icon-btn" @click="cancelEdit" title="Zrušit">
              <X :size="ICON_SIZE.STANDARD" />
            </button>
          </template>

          <!-- Normal mode: Edit/Copy/Delete -->
          <template v-else>
            <button class="icon-btn" @click="startEdit" title="Upravit položku">
              <Edit :size="ICON_SIZE.STANDARD" />
            </button>
            <button class="icon-btn" @click="handleCopy" title="Kopírovat položku">
              <Copy :size="ICON_SIZE.STANDARD" />
            </button>
            <button class="icon-btn icon-btn-danger" @click="handleDelete" title="Smazat položku">
              <Trash2 :size="ICON_SIZE.STANDARD" />
            </button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* === PANEL === */
.material-detail-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
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
  font-size: var(--text-sm);
}

/* === ICON TOOLBAR === */
.icon-toolbar {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  justify-content: center;
  margin-top: var(--space-4);
  margin-bottom: calc(-1 * var(--space-5) + 2px);
  padding-top: var(--space-3);
  padding-bottom: 2px;
  border-top: 1px solid var(--border-default);
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
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-card .value {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

/* === EDIT INPUTS === */
.edit-input {
  width: 100%;
  padding: var(--space-2);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  transition: all var(--duration-fast);
}

.edit-input:focus {
  outline: none;
  border-color: var(--border-strong);
  box-shadow: 0 0 0 3px var(--focus-ring);
}
</style>
