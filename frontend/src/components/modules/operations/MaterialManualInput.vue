<template>
  <div class="parse-preview">
    <div class="preview-header">
      <span class="preview-label">Manuální zadání</span>
    </div>

    <div class="preview-content">
      <div class="manual-grid">
        <!-- Shape selector -->
        <div class="manual-field">
          <label class="manual-label">Tvar *</label>
          <select v-model="manualShape" class="manual-control" data-testid="manual-shape">
            <option value="">— vyberte —</option>
            <option v-for="s in SHAPES" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>

        <!-- W.Nr -->
        <div class="manual-field">
          <label class="manual-label">W.Nr *</label>
          <input
            v-model="manualWnr"
            type="text"
            placeholder="např. 1.7225"
            class="manual-control"
            data-testid="manual-wnr"
          />
        </div>

        <!-- Dynamic dimensions -->
        <div v-for="dim in activeDimensions" :key="dim.key" class="manual-field">
          <label class="manual-label">{{ dim.label }}</label>
          <input
            :value="dimensions[dim.key] ?? ''"
            type="number"
            step="0.1"
            min="0"
            class="manual-control"
            @input="dimensions[dim.key] = parseFloat(($event.target as HTMLInputElement).value) || undefined"
          />
        </div>
      </div>

      <!-- Price category + weight + price — compact inline row -->
      <div class="info-row">
        <div class="info-item info-category">
          <span class="info-label">Kat:</span>
          <span
            v-if="loadingCategory"
            class="info-value info-muted"
          >načítám...</span>
          <span
            v-else-if="selectedPriceCategoryName"
            class="info-value"
            :title="selectedPriceCategoryName"
          >{{ selectedPriceCategoryName }}</span>
          <span
            v-else-if="manualWnr && manualShape"
            class="info-value info-error"
          >nenalezena</span>
          <span v-else class="info-value info-muted">—</span>
        </div>

        <div v-if="estimatedWeight !== null" class="info-item">
          <span class="info-label">Váha:</span>
          <span class="info-value info-mono">{{ estimatedWeight.toFixed(2) }} kg</span>
        </div>

        <div v-if="estimatedPrice !== null" class="info-item">
          <span class="info-label">Cena:</span>
          <span class="info-value info-mono info-price">{{ estimatedPrice.toFixed(0) }} Kč</span>
        </div>
      </div>

      <p v-if="validationError" class="preview-warning">
        {{ validationError }}
      </p>
    </div>

    <div class="preview-actions">
      <button
        class="btn-confirm"
        :disabled="!manualShape"
        data-testid="manual-create-btn"
        @click="handleCreate"
      >
        <Check :size="ICON_SIZE.SMALL" />
        Vytvořit
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, reactive } from 'vue'
import { Check } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import { apiClient } from '@/api/client'
import type { ParsedMaterial } from '@/types/material'
import { SHAPES, SHAPE_DIMENSIONS, SHAPE_TO_STOCK_SHAPE } from './materialConstants'

const emit = defineEmits<{ create: [material: ParsedMaterial] }>()

const manualShape = ref('')
const manualWnr = ref('')
const dimensions = reactive<Record<string, number | undefined>>({})
const selectedPriceCategoryId = ref<number | null>(null)
const selectedPriceCategoryName = ref<string>('')
const validationError = ref('')
const loadingCategory = ref(false)

// Data for weight/price calculation
const density = ref<number | null>(null) // kg/dm³ from MaterialGroup
const priceTiers = ref<{ min_weight: number; max_weight: number | null; price_per_kg: number }[]>([])

const activeDimensions = computed(() => SHAPE_DIMENSIONS[manualShape.value] || [])

// Watch shape to reset dimensions
watch(manualShape, (newShape, oldShape) => {
  if (newShape !== oldShape) {
    Object.keys(dimensions).forEach((k) => { dimensions[k] = undefined })
  }
})

// Watch both shape and w_nr to auto-load price category + tiers
watch([manualShape, manualWnr], async ([shape, wnr]) => {
  selectedPriceCategoryId.value = null
  selectedPriceCategoryName.value = ''
  validationError.value = ''
  density.value = null
  priceTiers.value = []

  if (!shape) {
    loadingCategory.value = false
    return
  }

  const stockShape = SHAPE_TO_STOCK_SHAPE[shape]
  if (!stockShape) {
    validationError.value = `Neznámý tvar: ${shape}`
    loadingCategory.value = false
    return
  }

  const trimmedWnr = wnr?.trim()
  if (!trimmedWnr) return

  loadingCategory.value = true
  try {
    const response = await apiClient.get('/materials/price-category-for-input', {
      params: { shape: stockShape, w_nr: trimmedWnr }
    })

    if (response.data) {
      selectedPriceCategoryId.value = response.data.id
      selectedPriceCategoryName.value = response.data.name
      validationError.value = ''

      // Get density from material_group (eager-loaded in response)
      density.value = response.data.material_group?.density ?? response.data.density ?? null

      // Load tiers for this category
      const tiersResp = await apiClient.get('/materials/price-tiers', {
        params: { category_id: response.data.id }
      })
      priceTiers.value = tiersResp.data ?? []
    } else {
      selectedPriceCategoryId.value = null
      selectedPriceCategoryName.value = ''
      validationError.value = `Nenalezena kategorie pro ${wnr} + ${shape}`
    }
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } }; message?: string }
    selectedPriceCategoryId.value = null
    selectedPriceCategoryName.value = ''
    validationError.value = `Chyba načítání kategorie: ${err.response?.data?.detail || err.message}`
  } finally {
    loadingCategory.value = false
  }
})

// Estimate weight from dimensions + density (preview only — backend calculates real value)
const estimatedWeight = computed(() => {
  if (!density.value) return null

  const stockShape = SHAPE_TO_STOCK_SHAPE[manualShape.value]
  let volumeCm3 = 0

  if (stockShape === 'round_bar' && dimensions.diameter) {
    const radiusCm = (dimensions.diameter / 10) / 2
    const lengthCm = (dimensions.length ?? 0) / 10
    if (lengthCm > 0) volumeCm3 = Math.PI * radiusCm * radiusCm * lengthCm
  } else if (stockShape === 'square_bar' && dimensions.width) {
    const wCm = dimensions.width / 10
    const lengthCm = (dimensions.length ?? 0) / 10
    if (lengthCm > 0) volumeCm3 = wCm * wCm * lengthCm
  } else if ((stockShape === 'flat_bar' || stockShape === 'plate') && dimensions.width && dimensions.height) {
    if (stockShape === 'plate' && dimensions.thickness) {
      // Plate: width × height × thickness
      volumeCm3 = (dimensions.width / 10) * (dimensions.height / 10) * (dimensions.thickness / 10)
    } else if (dimensions.length) {
      // Flat bar: width × height × length
      volumeCm3 = (dimensions.width / 10) * (dimensions.height / 10) * (dimensions.length / 10)
    }
  } else if (stockShape === 'tube' && dimensions.diameter && dimensions.thickness && dimensions.length) {
    const outerR = (dimensions.diameter / 10) / 2
    const innerR = outerR - (dimensions.thickness / 10)
    const lengthCm = dimensions.length / 10
    if (innerR > 0) volumeCm3 = Math.PI * (outerR * outerR - innerR * innerR) * lengthCm
  } else if (stockShape === 'hexagonal_bar' && dimensions.width && dimensions.length) {
    // Hexagon: (3√3/2) × s² × L, where s = width/2
    const sCm = (dimensions.width / 10) / 2
    const lengthCm = dimensions.length / 10
    volumeCm3 = (3 * Math.sqrt(3) / 2) * sCm * sCm * lengthCm
  }

  if (volumeCm3 === 0) return null

  // density is kg/dm³ = kg / 1000cm³
  return (volumeCm3 / 1000) * density.value
})

// Estimate price from weight + tiers
const estimatedPrice = computed(() => {
  if (estimatedWeight.value === null || priceTiers.value.length === 0) return null

  const w = estimatedWeight.value
  // Find matching tier for this weight
  const tier = priceTiers.value.find(
    t => w >= t.min_weight && (t.max_weight === null || w < t.max_weight)
  )
  if (!tier) return null

  return w * tier.price_per_kg
})

function handleCreate() {
  validationError.value = ''
  if (!manualShape.value) { validationError.value = 'Vyberte tvar materiálu'; return }
  if (!manualWnr.value) { validationError.value = 'Zadejte W.Nr normu'; return }
  if (!selectedPriceCategoryId.value) { validationError.value = 'Cenová kategorie nebyla nalezena - zkontrolujte tvar a W.Nr'; return }

  const mat: ParsedMaterial = {
    shape: manualShape.value,
    w_nr: manualWnr.value || undefined,
    price_category_id: selectedPriceCategoryId.value,
    match_type: 'manual',
  }
  for (const dim of activeDimensions.value) {
    if (dimensions[dim.key] !== undefined) {
      (mat as Record<string, unknown>)[dim.key] = dimensions[dim.key]
    }
  }
  emit('create', mat)

  // Reset
  manualShape.value = ''
  manualWnr.value = ''
  Object.keys(dimensions).forEach((k) => { dimensions[k] = undefined })
  selectedPriceCategoryId.value = null
  selectedPriceCategoryName.value = ''
  density.value = null
  priceTiers.value = []
}
</script>

<style scoped>
.parse-preview {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 6px;
  background: var(--raised);
  border: 1px solid var(--b2);
  border-radius: var(--r);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-label {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t3);
  text-transform: uppercase;
}

.preview-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.manual-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
}

.manual-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.manual-label {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t3);
  display: flex;
  align-items: center;
  gap: 4px;
}

.manual-control {
  padding: 4px 6px;
  background: var(--ground);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  font-family: inherit;
  transition: all 100ms var(--ease);
}

.manual-control:focus {
  outline: none;
  border-color: var(--b3);
  background: var(--base);
}

.manual-control:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.manual-control::placeholder {
  color: var(--t3);
}

/* Compact info row: category + weight + price */
.info-row {
  display: flex;
  align-items: center;
  gap: var(--pad);
  padding: 4px 6px;
  background: var(--base);
  border-radius: var(--rs);
  min-height: 24px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.info-category {
  flex: 1;
  min-width: 0;
}

.info-label {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t3);
  flex-shrink: 0;
}

.info-value {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t1);
  overflow: hidden;
  text-overflow: ellipsis;
}

.info-muted {
  color: var(--t3);
  font-style: italic;
}

.info-error {
  color: var(--err);
}

.info-mono {
  font-family: var(--mono);
  font-weight: 600;
}

.info-price {
  color: var(--ok);
}

.preview-warning {
  font-size: var(--fs);
  color: var(--err);
  padding: 4px 6px;
  background: var(--base);
  border-radius: var(--rs);
}

.preview-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}

.btn-confirm {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;
  background: var(--ok);
  color: white;
  border: none;
  border-radius: var(--rs);
  font-weight: 600;
  font-size: var(--fs);
  cursor: pointer;
  transition: all 100ms var(--ease);
}

.btn-confirm:hover:not(:disabled) {
  background: var(--green);
}

.btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
