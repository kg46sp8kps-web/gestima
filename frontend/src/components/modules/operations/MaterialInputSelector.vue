<script setup lang="ts">
/**
 * Material Input Selector Component (BUILDING BLOCK - L-039)
 * Reusable material dropdown + add button
 * Used in OperationsRightPanel (PartOperations + PartTechnology modules)
 */

import { computed, watch, ref } from 'vue'
import { useMaterialsStore } from '@/stores/materials'
import { useOperationsStore } from '@/stores/operations'
import { Plus, Boxes } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import type { LinkingGroup } from '@/stores/windows'
import type { MaterialInputWithOperations } from '@/types/material'
import Modal from '@/components/ui/Modal.vue'
import MaterialInputForm from '../material/MaterialInputForm.vue'

interface Props {
  partId: number | null
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  linkingGroup: null
})

const materialsStore = useMaterialsStore()
const operationsStore = useOperationsStore()

// State
const showAddModal = ref(false)

// Computed
const materialInputs = computed(() => materialsStore.getContext(props.linkingGroup).materialInputs)
const operations = computed(() => operationsStore.getContext(props.linkingGroup).operations)
const loading = computed(() => materialsStore.getContext(props.linkingGroup).loadingInputs)

// Load materials when partId changes
watch(() => props.partId, async (newPartId) => {
  if (newPartId) {
    await materialsStore.loadMaterialInputs(newPartId, props.linkingGroup)
  }
}, { immediate: true })

// Format material label for display
function formatMaterialLabel(material: MaterialInputWithOperations): string {
  const parts: string[] = []

  if (material.stock_shape === 'round_bar' && material.stock_diameter) {
    parts.push(`Ø${material.stock_diameter}`)
  } else if (material.stock_shape === 'square_bar' && material.stock_width) {
    parts.push(`□${material.stock_width}`)
  } else if (material.stock_shape === 'flat_bar' && material.stock_width && material.stock_height) {
    parts.push(`${material.stock_width}×${material.stock_height}`)
  }

  if (material.stock_length) {
    parts.push(`L${material.stock_length}`)
  }

  if (material.weight_kg && material.cost_per_piece) {
    parts.push(`${material.weight_kg.toFixed(2)} kg`)
    parts.push(`${material.cost_per_piece.toFixed(0)} Kč`)
  }

  return parts.length > 0 ? parts.join(' | ') : 'Materiál'
}

// Handle add material
function handleAddMaterial() {
  showAddModal.value = true
}

// Handle save (reload materials)
async function handleSave() {
  showAddModal.value = false
  if (props.partId) {
    await materialsStore.loadMaterialInputs(props.partId, props.linkingGroup)
  }
}

// Handle cancel
function handleCancel() {
  showAddModal.value = false
}

// Calculate total cost
const totalMaterialCost = computed(() => {
  return materialInputs.value.reduce((sum, mat) => sum + (mat.cost_per_piece || 0), 0)
})
</script>

<template>
  <div class="material-input-selector">
    <div class="selector-header">
      <label class="selector-label">Materiál</label>
      <button
        class="btn-add-icon"
        @click="handleAddMaterial"
        :disabled="!partId || loading"
        title="Přidat materiál"
      >
        <Plus :size="ICON_SIZE.STANDARD" />
      </button>
    </div>

    <div class="selector-body">
      <!-- Loading state -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <span>Načítám...</span>
      </div>

      <!-- Empty state -->
      <div v-else-if="materialInputs.length === 0" class="empty-state">
        <Boxes :size="24" class="empty-icon" />
        <span class="empty-text">Žádný materiál</span>
      </div>

      <!-- Material list -->
      <div v-else class="material-list">
        <div
          v-for="material in materialInputs"
          :key="material.id"
          class="material-item"
        >
          <span class="material-label">{{ formatMaterialLabel(material) }}</span>
        </div>

        <!-- Total cost (when multiple materials) -->
        <div v-if="materialInputs.length > 1" class="material-total">
          <span class="total-label">Celkem:</span>
          <span class="total-value">{{ totalMaterialCost.toFixed(0) }} Kč</span>
        </div>
      </div>
    </div>

    <!-- Add Material Modal -->
    <Modal
      v-model="showAddModal"
      title="Přidat materiál"
      size="xl"
    >
      <MaterialInputForm
        v-if="partId"
        :partId="partId"
        :operations="operations"
        @save="handleSave"
        @cancel="handleCancel"
      />
    </Modal>
  </div>
</template>

<style scoped>
.material-input-selector {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.selector-label {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.btn-add-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-add-icon:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-add-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.selector-body {
  min-height: 40px;
}

/* Loading state */
.loading-state {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Empty state */
.empty-state {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  color: var(--text-tertiary);
}

.empty-icon {
  color: var(--text-secondary);
}

.empty-text {
  font-size: var(--text-sm);
}

/* Material list */
.material-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.material-item {
  display: flex;
  align-items: center;
  padding: var(--space-2);
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  transition: var(--transition-fast);
}

.material-item:hover {
  background: var(--bg-hover);
}

.material-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

/* Total summary */
.material-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2) var(--space-2) 0;
  border-top: 1px solid var(--border-default);
  margin-top: var(--space-1);
}

.total-label {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-secondary);
}

.total-value {
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  color: var(--color-primary);
  font-family: var(--font-mono);
}
</style>
