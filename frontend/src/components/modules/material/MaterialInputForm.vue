<template>
  <div class="material-input-form">
    <h3 class="form-title">
      {{ isEditMode ? 'Upravit materiál' : 'Nový materiál' }}
    </h3>

    <form @submit.prevent="handleSubmit" class="form-container">
      <!-- Two-column layout: LEFT (parser + stock) | RIGHT (summary) -->
      <div class="form-layout">
        <!-- LEFT: Parser + Stock placeholder -->
        <div class="form-left">
          <MaterialParserInput
            ref="parserRef"
            :disabled="saving"
            :material-standard="recognizedMaterialStandard"
            @parsed="handleParsed"
          />

          <!-- Stock placeholder (future) -->
          <div class="stock-placeholder">
            <div class="placeholder-icon">📦</div>
            <div class="placeholder-text">
              <div class="placeholder-title">Skladová zásoba</div>
              <div class="placeholder-subtitle">Připravujeme...</div>
            </div>
          </div>
        </div>

        <!-- RIGHT: Price calculations -->
        <div class="form-right">
          <MaterialSummaryPanel
            :summary="summary"
            :all-tiers="priceTiers"
            :loading="calculatingSummary"
          />
        </div>
      </div>

      <!-- Actions -->
      <div class="form-actions">
        <!-- Manual input button (left side) -->
        <button
          type="button"
          class="icon-btn"
          @click="showManualModal = true"
          title="Ruční zadání rozměrů"
        >
          <Edit3Icon :size="ICON_SIZE.STANDARD" />
        </button>

        <div class="actions-right">
          <button
            type="button"
            class="icon-btn"
            :disabled="saving"
            @click="handleCancel"
            title="Zrušit"
          >
            <XIcon :size="ICON_SIZE.STANDARD" />
          </button>

          <button
            type="submit"
            class="icon-btn icon-btn-primary"
            :disabled="!isFormValid || saving"
            title="Vytvořit materiál"
          >
            <CheckIcon :size="ICON_SIZE.STANDARD" />
          </button>
        </div>
      </div>
    </form>

    <!-- Manual input modal -->
    <Modal
      v-model="showManualModal"
      title="Ruční zadání rozměrů materiálu"
      size="lg"
    >
      <MaterialDimensionsFields
        v-model:shape="formData.stock_shape"
        v-model:price-category-id="formData.price_category_id"
        v-model:diameter="formData.stock_diameter"
        v-model:width="formData.stock_width"
        v-model:height="formData.stock_height"
        v-model:wall-thickness="formData.stock_wall_thickness"
        v-model:length="formData.stock_length"
        :disabled="saving"
      />
      <template #footer>
        <Button variant="secondary" @click="showManualModal = false">
          <XIcon :size="ICON_SIZE.STANDARD" />
          Zavřít
        </Button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useMaterialsStore } from '@/stores/materials'
import { calculateMaterialSummary } from '@/api/materialInputs'
import { getPriceTiers } from '@/api/materials'
import type { MaterialInput, MaterialParseResult, MaterialSummary, StockShape, MaterialPriceTier } from '@/types/material'
import type { Operation } from '@/types/operation'
import MaterialParserInput from './MaterialParserInput.vue'
import MaterialDimensionsFields from './MaterialDimensionsFields.vue'
import MaterialSummaryPanel from './MaterialSummaryPanel.vue'
import Button from '@/components/ui/Button.vue'
import Modal from '@/components/ui/Modal.vue'
import { Check as CheckIcon, X as XIcon, Edit3 as Edit3Icon } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  materialInput?: MaterialInput | null
  partId: number
  operations: Operation[]
}

interface Emits {
  (e: 'save', materialInput: MaterialInput): void
  (e: 'cancel'): void
}

const props = withDefaults(defineProps<Props>(), {
  materialInput: null
})

const emit = defineEmits<Emits>()

const materialsStore = useMaterialsStore()

// Refs
const parserRef = ref<InstanceType<typeof MaterialParserInput> | null>(null)

// Form data
const formData = reactive<{
  stock_shape: StockShape
  price_category_id: number | null
  stock_diameter: number | null
  stock_width: number | null
  stock_height: number | null
  stock_wall_thickness: number | null
  stock_length: number | null
}>({
  stock_shape: 'round_bar',
  price_category_id: null,
  stock_diameter: null,
  stock_width: null,
  stock_height: null,
  stock_wall_thickness: null,
  stock_length: null
})

// State
const saving = ref(false)
const calculatingSummary = ref(false)
const summary = ref<MaterialSummary | null>(null)
const priceTiers = ref<MaterialPriceTier[]>([])
const showManualModal = ref(false)
const recognizedMaterialStandard = ref<string | null>(null)

// Computed
const isEditMode = computed(() => props.materialInput !== null)

const isFormValid = computed(() => {
  return (
    formData.price_category_id !== null &&
    formData.stock_length !== null &&
    formData.stock_length > 0
  )
})

// Initialize form data
function initializeForm() {
  if (props.materialInput) {
    // Edit mode - populate from existing material
    formData.stock_shape = props.materialInput.stock_shape
    formData.price_category_id = props.materialInput.price_category_id
    formData.stock_diameter = props.materialInput.stock_diameter
    formData.stock_width = props.materialInput.stock_width
    formData.stock_height = props.materialInput.stock_height
    formData.stock_wall_thickness = props.materialInput.stock_wall_thickness
    formData.stock_length = props.materialInput.stock_length
  } else {
    // Create mode - reset to defaults
    formData.stock_shape = 'round_bar'
    formData.price_category_id = null
    formData.stock_diameter = null
    formData.stock_width = null
    formData.stock_height = null
    formData.stock_wall_thickness = null
    formData.stock_length = null
  }
}

// Handle parser result
function handleParsed(result: MaterialParseResult) {
  console.log('[MaterialInputForm] handleParsed called! This should ONLY happen on Enter.')
  if (result.shape) {
    formData.stock_shape = result.shape
  }
  if (result.diameter !== null) {
    formData.stock_diameter = result.diameter
  }
  if (result.width !== null) {
    formData.stock_width = result.width
  }
  if (result.height !== null) {
    formData.stock_height = result.height
  }
  if (result.thickness !== null) {
    formData.stock_height = result.thickness // height = thickness for plate
  }
  if (result.wall_thickness !== null) {
    formData.stock_wall_thickness = result.wall_thickness
  }
  if (result.length !== null) {
    formData.stock_length = result.length
  }
  if (result.suggested_price_category_id !== null) {
    formData.price_category_id = result.suggested_price_category_id
  }
  if (result.material_norm) {
    recognizedMaterialStandard.value = result.material_norm
  }
}

// Load price tiers for the selected category
async function loadPriceTiers() {
  if (!formData.price_category_id) {
    priceTiers.value = []
    return
  }

  try {
    const tiers = await getPriceTiers(formData.price_category_id)
    console.log('[MaterialInputForm] Loaded tiers:', tiers.length, tiers.map(t => t.id))
    priceTiers.value = tiers
  } catch (error) {
    console.error('Failed to load price tiers:', error)
    priceTiers.value = []
  }
}

// Calculate summary (reactive)
async function updateSummary() {
  // Only calculate if we have minimum required data
  if (!formData.price_category_id || !formData.stock_length) {
    summary.value = null
    return
  }

  calculatingSummary.value = true
  try {
    summary.value = await calculateMaterialSummary({
      price_category_id: formData.price_category_id,
      stock_shape: formData.stock_shape,
      stock_diameter: formData.stock_diameter,
      stock_length: formData.stock_length,
      stock_width: formData.stock_width,
      stock_height: formData.stock_height,
      stock_wall_thickness: formData.stock_wall_thickness,
      quantity: 1
    })
  } catch (error) {
    console.error('Failed to calculate summary:', error)
    summary.value = null
  } finally {
    calculatingSummary.value = false
  }
}

// Watch price category changes to load tiers
watch(
  () => formData.price_category_id,
  async (newCategoryId, oldCategoryId) => {
    // Only load if category actually changed (not on initial mount)
    if (newCategoryId !== oldCategoryId && oldCategoryId !== undefined) {
      await loadPriceTiers()
    }
  }
)

// Watch form data changes for reactive summary calculation
watch(
  () => ({
    price_category_id: formData.price_category_id,
    stock_shape: formData.stock_shape,
    stock_diameter: formData.stock_diameter,
    stock_width: formData.stock_width,
    stock_height: formData.stock_height,
    stock_wall_thickness: formData.stock_wall_thickness,
    stock_length: formData.stock_length
  }),
  () => {
    updateSummary()
  },
  { deep: true }
)

// Submit handler
async function handleSubmit() {
  if (!isFormValid.value) return

  saving.value = true
  try {
    if (isEditMode.value && props.materialInput) {
      // Update existing material
      const updated = await materialsStore.updateMaterialInput(
        props.materialInput.id,
        {
          stock_shape: formData.stock_shape,
          price_category_id: formData.price_category_id!,
          stock_diameter: formData.stock_diameter,
          stock_width: formData.stock_width,
          stock_height: formData.stock_height,
          stock_wall_thickness: formData.stock_wall_thickness,
          stock_length: formData.stock_length,
          quantity: 1,
          version: props.materialInput.version
        },
        null // linkingGroup - assuming null for now
      )
      emit('save', updated)
    } else {
      // Create new material
      const payload = {
        part_id: props.partId,
        stock_shape: formData.stock_shape,
        price_category_id: formData.price_category_id!,
        stock_diameter: formData.stock_diameter,
        stock_width: formData.stock_width,
        stock_height: formData.stock_height,
        stock_wall_thickness: formData.stock_wall_thickness,
        stock_length: formData.stock_length,
        quantity: 1
      }
      console.log('[MaterialInputForm] Creating material with payload:', payload)
      const created = await materialsStore.createMaterialInput(payload, null)
      emit('save', created)

      // Clear parser and reset form after successful creation
      parserRef.value?.clear()
      initializeForm()
    }
  } catch (error: any) {
    // Log detailed validation error
    console.error('Failed to save material:', error)
    if (error?.response?.data?.detail) {
      console.error('Validation errors:', error.response.data.detail)
    }
  } finally {
    saving.value = false
  }
}

// Cancel handler
function handleCancel() {
  emit('cancel')
}

// Watch for parser result changes - clear form when parser is cleared
watch(() => materialsStore.parseResult, (newResult) => {
  if (!newResult || !newResult.confidence || newResult.confidence < 0.4) {
    // Parser cleared or low confidence - reset form data
    initializeForm()
    summary.value = null
    priceTiers.value = []
    recognizedMaterialStandard.value = null
  }
}, { deep: true })

// Lifecycle
onMounted(async () => {
  // Load reference data
  await materialsStore.loadReferenceData()

  // Initialize form
  initializeForm()

  // Load price tiers if category is already selected
  if (formData.price_category_id) {
    await loadPriceTiers()
  }

  // Calculate initial summary if in edit mode
  if (isEditMode.value) {
    await updateSummary()
  }
})
</script>

<style scoped>
.material-input-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
}

.form-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-body);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border-default);
}

.form-container {
  display: flex;
  flex-direction: column;
}

/* Two-column layout: LEFT (parser + stock) | RIGHT (summary) */
.form-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-6);
  margin-bottom: var(--space-4);
}

.form-left,
.form-right {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* Stock placeholder */
.stock-placeholder {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-md);
  opacity: 0.6;
}

.placeholder-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.placeholder-text {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.placeholder-title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.placeholder-subtitle {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-style: italic;
}

/* Actions */
.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) 0;
  border-top: 1px solid var(--border-default);
}

.actions-right {
  display: flex;
  gap: var(--space-3);
}
</style>
