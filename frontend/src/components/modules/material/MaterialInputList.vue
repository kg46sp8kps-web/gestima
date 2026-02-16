<template>
  <div class="material-input-list">
    <div class="list-header">
      <h4>Přidané materiály</h4>
      <span v-if="materials.length > 0" class="count-badge">{{ materials.length }}</span>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <span>Načítání...</span>
    </div>

    <div v-else-if="materials.length === 0" class="empty-state">
      <span class="empty-icon">📦</span>
      <p>Žádné materiály</p>
    </div>

    <div v-else class="materials-list">
      <div
        v-for="material in materials"
        :key="material.id"
        class="material-row"
        :class="{ 'material-row-editing': material.id === props.editingMaterialId }"
      >
        <!-- Shape icon -->
        <div class="material-shape">
          <span class="shape-icon">{{ getShapeIcon(material.stock_shape) }}</span>
        </div>

        <!-- Editable dimension fields (ALWAYS VISIBLE) -->
        <div class="material-dimensions" @click.stop>
          <div v-if="getShapeDimensionFields(material.stock_shape).showDiameter" class="dim-field">
            <span class="dim-label">Ø:</span>
            <input
              type="number"
              step="0.1"
              min="0"
              :value="material.stock_diameter"
              @focus="($event.target as HTMLInputElement).select()"
              @input="handleDimensionInput(material.id, 'stock_diameter', $event)"
              class="dim-input"
            />
          </div>
          <div v-if="getShapeDimensionFields(material.stock_shape).showWidth" class="dim-field">
            <span class="dim-label">Š:</span>
            <input
              type="number"
              step="0.1"
              min="0"
              :value="material.stock_width"
              @focus="($event.target as HTMLInputElement).select()"
              @input="handleDimensionInput(material.id, 'stock_width', $event)"
              class="dim-input"
            />
          </div>
          <div v-if="getShapeDimensionFields(material.stock_shape).showHeight" class="dim-field">
            <span class="dim-label">V:</span>
            <input
              type="number"
              step="0.1"
              min="0"
              :value="material.stock_height"
              @focus="($event.target as HTMLInputElement).select()"
              @input="handleDimensionInput(material.id, 'stock_height', $event)"
              class="dim-input"
            />
          </div>
          <div class="dim-field">
            <span class="dim-label">L:</span>
            <input
              type="number"
              step="0.1"
              min="0"
              :value="material.stock_length"
              @focus="($event.target as HTMLInputElement).select()"
              @input="handleDimensionInput(material.id, 'stock_length', $event)"
              class="dim-input"
            />
          </div>
          <div v-if="getShapeDimensionFields(material.stock_shape).showWallThickness" class="dim-field">
            <span class="dim-label">t:</span>
            <input
              type="number"
              step="0.1"
              min="0"
              :value="material.stock_wall_thickness"
              @focus="($event.target as HTMLInputElement).select()"
              @input="handleDimensionInput(material.id, 'stock_wall_thickness', $event)"
              class="dim-input"
            />
          </div>
        </div>

        <!-- Category -->
        <div class="material-category">
          <span class="category-label">{{ getPriceCategoryName(material.price_category_id) }}</span>
        </div>

        <!-- Calculated values (weight, price) -->
        <Tooltip :text="getMaterialTooltip(material)">
          <div class="material-info">
            <span v-if="material.weight_kg" class="weight">{{ material.weight_kg.toFixed(3) }} kg</span>
            <span v-if="material.cost_per_piece" class="price">{{ material.cost_per_piece.toFixed(2) }} Kč</span>
          </div>
        </Tooltip>

        <!-- Linked operations (compact: just numbers) -->
        <div class="material-operations">
          <!-- Existing linked operations -->
          <span
            v-for="op in material.operations"
            :key="op.id"
            class="operation-chip-compact"
            :title="`${op.seq}: ${op.name}`"
          >
            {{ op.seq }}
            <button
              type="button"
              class="unlink-btn-compact"
              @click.stop="handleUnlinkOperation(material.id, op.id)"
              title="Odpojit"
            >
              ×
            </button>
          </span>

          <!-- Add operation dropdown (compact) -->
          <select
            v-if="getAvailableOperations(material).length > 0"
            v-model="selectedOperations[material.id]"
            class="operation-select-compact"
            @change="handleLinkOperation(material.id)"
            @click.stop
          >
            <option :value="null">+</option>
            <option
              v-for="op in getAvailableOperations(material)"
              :key="op.id"
              :value="op.id"
            >
              {{ op.seq }}
            </option>
          </select>
        </div>

        <!-- Actions -->
        <div class="material-actions">
          <Button variant="ghost" size="sm" @click="emit('delete', material.id)" title="Smazat">
            ×
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { MaterialInputWithOperations, StockShape } from '@/types/material'
import type { Operation } from '@/types/operation'
import { getShapeDimensionFields } from '@/types/material'
import { useMaterialsStore } from '@/stores/materials'
import Button from '@/components/ui/Button.vue'
import Tooltip from '@/components/ui/Tooltip.vue'
import { Link as LinkIcon, X as XIcon } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

const materialsStore = useMaterialsStore()

interface Props {
  materials: MaterialInputWithOperations[]
  operations: Operation[]  // Available operations for the part
  loading?: boolean
  editingMaterialId?: number | null  // ID of material being edited
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  editingMaterialId: null,
  operations: () => []
})

const emit = defineEmits<{
  delete: [materialId: number]
  update: [materialId: number, updates: Partial<MaterialInputWithOperations>]
  linkOperation: [materialId: number, operationId: number]
  unlinkOperation: [materialId: number, operationId: number]
}>()

// Local state for selected operation per material
const selectedOperations = ref<Record<number, number | null>>({})

const SHAPE_ICONS: Record<StockShape, string> = {
  round_bar: '○',
  square_bar: '□',
  flat_bar: '▬',
  hexagonal_bar: '⬡',
  plate: '▭',
  tube: '◯',
  casting: '⬢',
  forging: '⬣'
}

function getShapeIcon(shape: StockShape): string {
  return SHAPE_ICONS[shape] || '•'
}

function getPriceCategoryName(categoryId: number): string {
  const category = materialsStore.priceCategories.find(c => c.id === categoryId)
  return category?.name || `Kategorie #${categoryId}`
}

function handleDimensionInput(materialId: number, field: string, event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  emit('update', materialId, { [field]: value })
}

function formatPrice(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return '-'
  return value.toLocaleString('cs-CZ', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function getMaterialTooltip(material: MaterialInputWithOperations): string {
  if (!material.price_per_kg) return 'Cena není dostupná'
  return `Cena z tieru: ${formatPrice(material.price_per_kg)} Kč/kg`
}

// Get available operations for material (not already linked)
function getAvailableOperations(material: MaterialInputWithOperations): Operation[] {
  const linkedOpIds = material.operations?.map(op => op.id) || []
  return props.operations.filter(op => !linkedOpIds.includes(op.id))
}

// Handle link operation
function handleLinkOperation(materialId: number) {
  const operationId = selectedOperations.value[materialId]
  if (operationId) {
    emit('linkOperation', materialId, operationId)
    selectedOperations.value[materialId] = null  // Reset selection
  }
}

// Handle unlink operation
function handleUnlinkOperation(materialId: number, operationId: number) {
  emit('unlinkOperation', materialId, operationId)
}
</script>

<style scoped>
.material-input-list { display: flex; flex-direction: column; gap: var(--space-3); height: 100%; overflow: hidden; }
.list-header { display: flex; align-items: center; gap: var(--space-2); }
.list-header h4 { margin: 0; font-size: var(--text-base); font-weight: var(--font-semibold); color: var(--text-primary); }
.count-badge {
  display: inline-flex; align-items: center; justify-content: center; min-width: 24px; height: 24px;
  padding: 0 var(--space-1); background: var(--bg-raised); border: 1px solid var(--border-default);
  border-radius: var(--radius-full); font-size: var(--text-xs); font-weight: var(--font-medium);
  color: var(--text-secondary);
}
.loading-state, .empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: var(--space-2); padding: var(--space-6); color: var(--text-secondary);
}
.spinner { width: 24px; height: 24px; border: 2px solid var(--border-default); border-radius: 50%; border-top-color: var(--color-primary); animation: spin 0.6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty-icon { font-size: var(--text-7xl); opacity: 0.5; }
.empty-state p { margin: 0; font-size: var(--text-md); color: var(--text-secondary); }
.materials-list { display: flex; flex-direction: column; gap: var(--space-1); overflow-y: auto; }
/* Material row - grid layout: Icon | Dimensions | Category | Info | Operations | Actions */
.material-row {
  display: grid;
  grid-template-columns: auto 1fr auto auto minmax(200px, auto) auto;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-3);
  border-bottom: 1px solid var(--border-default);
  transition: background-color 0.15s ease, border-left 0.15s ease;
}
.material-row:hover {
  background: var(--bg-hover);
}
.material-row:last-child { border-bottom: none; }

/* Editing state - persistent highlight */
.material-row-editing {
  background: var(--palette-info-light, rgba(37, 99, 235, 0.15)) !important;
  border-left: 4px solid var(--color-primary) !important;
  padding-left: calc(var(--space-3) - 4px) !important;
}

/* Shape icon */
.material-shape {
  display: flex;
  align-items: center;
}
.shape-icon {
  font-size: var(--text-lg);
  color: var(--text-secondary);
}

/* Dimension fields (always visible and editable) */
.material-dimensions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: nowrap;
}

.dim-field {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.dim-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
  font-family: var(--font-mono);
  white-space: nowrap;
}

.dim-input {
  width: 60px;
  padding: var(--space-1) var(--space-1);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  font-family: var(--font-mono);
  text-align: right;
}

.dim-input:focus {
  outline: none;
  border-color: var(--state-focus-border);
  background: var(--state-focus-bg);
}

.dim-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Category */
.material-category {
  display: flex;
  align-items: center;
}
.category-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
  white-space: nowrap;
}

/* Info section (weight, price, operations) */
.material-info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  white-space: nowrap;
}

/* Tooltip wrapper should not break grid */
.material-row :deep(.tooltip-wrapper) {
  display: contents;
}

.weight, .price {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-body);
}
.price { color: var(--palette-success); }
.operations {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  padding: var(--space-1) var(--space-2);
  background: var(--bg-surface);
  border-radius: var(--radius-sm);
  white-space: nowrap;
}

/* Operations section (compact inline) */
.material-operations {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1);
  min-width: 100px;
}

.operation-chip-compact {
  display: inline-flex;
  align-items: center;
  gap: var(--space-0\.5);
  padding: var(--space-0\.5) var(--space-2);
  background: var(--palette-info, rgba(37, 99, 235, 0.2));
  border: 1px solid var(--palette-info);
  border-radius: var(--radius-sm);
  font-size: var(--text-2xs);
  font-weight: var(--font-semibold);
  font-family: var(--font-mono);
  color: var(--text-primary);
  white-space: nowrap;
  cursor: help;
}

.unlink-btn-compact {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0;
  margin-left: 2px;
  font-size: var(--text-sm);
  line-height: 1;
  transition: color var(--transition-fast);
}

.unlink-btn-compact:hover {
  color: var(--palette-danger);
}

.operation-select-compact {
  min-width: 40px;
  max-width: 50px;
  padding: var(--space-0\.5) var(--space-1);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-2xs);
  font-weight: var(--font-semibold);
  font-family: var(--font-mono);
  color: var(--text-body);
  cursor: pointer;
}

.operation-select-compact:focus {
  outline: none;
  border-color: var(--state-focus-border);
  background: var(--state-focus-bg);
}

/* Actions */
.material-actions {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}
</style>
