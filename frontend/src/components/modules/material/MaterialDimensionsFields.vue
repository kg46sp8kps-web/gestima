<template>
  <div class="material-dimensions-fields">
    <!-- Shape selector -->
    <div class="field-row">
      <Select
        v-model="localShape"
        label="Tvar polotovaru"
        :options="shapeOptions"
        required
        :disabled="disabled"
        @change="handleShapeChange"
      />

      <Select
        v-model="localPriceCategoryId"
        label="Cenová kategorie"
        :options="priceCategoryOptions"
        placeholder="-- Vyberte --"
        required
        :disabled="disabled || !localShape"
      />
    </div>

    <!-- Conditional dimension fields based on shape - COMPACT (side by side) -->
    <div class="dimensions-grid">
      <!-- Diameter (round_bar, hexagonal_bar, tube, casting, forging) -->
      <Input
        v-if="showDiameter"
        v-model="localDiameter"
        type="number"
        label="Ø [mm]"
        placeholder="0"
        :mono="true"
        :disabled="disabled"
        :required="showDiameter"
      />

      <!-- Width (square_bar, flat_bar, plate) -->
      <Input
        v-if="showWidth"
        v-model="localWidth"
        type="number"
        label="Š [mm]"
        placeholder="0"
        :mono="true"
        :disabled="disabled"
        :required="showWidth"
      />

      <!-- Height/Thickness (flat_bar, plate) -->
      <Input
        v-if="showHeight"
        v-model="localHeight"
        type="number"
        label="V/t [mm]"
        placeholder="0"
        :mono="true"
        :disabled="disabled"
        :required="showHeight"
      />

      <!-- Wall thickness (tube) -->
      <Input
        v-if="showWallThickness"
        v-model="localWallThickness"
        type="number"
        label="t stěny [mm]"
        placeholder="0"
        :mono="true"
        :disabled="disabled"
        :required="showWallThickness"
      />

      <!-- Length (always visible) -->
      <Input
        v-model="localLength"
        type="number"
        label="L [mm]"
        placeholder="0"
        :mono="true"
        :disabled="disabled"
        required
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useMaterialsStore } from '@/stores/materials'
import type { StockShape } from '@/types/material'
import { STOCK_SHAPE_OPTIONS, getShapeDimensionFields } from '@/types/material'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'

interface Props {
  shape: StockShape
  priceCategoryId: number | null
  diameter: number | null
  width: number | null
  height: number | null
  wallThickness: number | null
  length: number | null
  disabled?: boolean
}

interface Emits {
  (e: 'update:shape', value: StockShape): void
  (e: 'update:priceCategoryId', value: number | null): void
  (e: 'update:diameter', value: number | null): void
  (e: 'update:width', value: number | null): void
  (e: 'update:height', value: number | null): void
  (e: 'update:wallThickness', value: number | null): void
  (e: 'update:length', value: number | null): void
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false
})

const emit = defineEmits<Emits>()

const materialsStore = useMaterialsStore()

// Local reactive state (v-model)
const localShape = computed({
  get: () => props.shape,
  set: (value) => emit('update:shape', value)
})

const localPriceCategoryId = computed({
  get: () => props.priceCategoryId ?? '',
  set: (value) => emit('update:priceCategoryId', value === '' ? null : Number(value))
})

const localDiameter = computed({
  get: () => props.diameter ?? '',
  set: (value) => emit('update:diameter', value === '' ? null : Number(value))
})

const localWidth = computed({
  get: () => props.width ?? '',
  set: (value) => emit('update:width', value === '' ? null : Number(value))
})

const localHeight = computed({
  get: () => props.height ?? '',
  set: (value) => emit('update:height', value === '' ? null : Number(value))
})

const localWallThickness = computed({
  get: () => props.wallThickness ?? '',
  set: (value) => emit('update:wallThickness', value === '' ? null : Number(value))
})

const localLength = computed({
  get: () => props.length ?? '',
  set: (value) => emit('update:length', value === '' ? null : Number(value))
})

// Shape options
const shapeOptions = STOCK_SHAPE_OPTIONS

// Price category options (filtered by shape)
const priceCategoryOptions = computed(() => {
  const categories = materialsStore.getFilteredCategories(props.shape)
  return categories.map(cat => ({
    value: cat.id,
    label: cat.name
  }))
})

// Conditional field visibility
const dimensionFields = computed(() => getShapeDimensionFields(props.shape))
const showDiameter = computed(() => dimensionFields.value.showDiameter)
const showWidth = computed(() => dimensionFields.value.showWidth)
const showHeight = computed(() => dimensionFields.value.showHeight)
const showWallThickness = computed(() => dimensionFields.value.showWallThickness)

// Handle shape change - clear dimension fields that are not needed
function handleShapeChange() {
  const fields = getShapeDimensionFields(localShape.value)

  if (!fields.showDiameter) {
    emit('update:diameter', null)
  }
  if (!fields.showWidth) {
    emit('update:width', null)
  }
  if (!fields.showHeight) {
    emit('update:height', null)
  }
  if (!fields.showWallThickness) {
    emit('update:wallThickness', null)
  }

  // Auto-select first matching category if current selection is incompatible
  const currentCategory = props.priceCategoryId
  const filteredCategories = materialsStore.getFilteredCategories(localShape.value)
  const isCurrentCategoryValid = currentCategory && filteredCategories.some(c => c.id === currentCategory)

  if (!isCurrentCategoryValid && filteredCategories.length > 0) {
    emit('update:priceCategoryId', filteredCategories[0]!.id)
  }
}
</script>

<style scoped>
.material-dimensions-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-row {
  display: flex;
  gap: var(--pad);
  flex-wrap: wrap;
}

.field-row > * {
  flex: 1;
  min-width: 200px;
}

/* Dimensions row - compact fields */
.dimensions-row > * {
  min-width: 120px;
  max-width: 180px;
}

/* Compact dimensions grid - all fields side by side */
.dimensions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(70px, 1fr));
  gap: 6px;
}
</style>
