<script setup lang="ts">
/**
 * MaterialLinksInfo - Zobrazení (a editace) navázaných materiálů k operaci
 * BUILDING BLOCKS (L-039): Reusable component with optional edit mode
 */

import { ref, onMounted, watch } from 'vue'
import { getOperationMaterials } from '@/api/materialInputs'
import type { MaterialInput, MaterialInputWithOperations } from '@/types/material'
import { Link as LinkIcon, X as XIcon } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  operationId: number
  editable?: boolean  // Enable add/remove functionality
  availableMaterials?: MaterialInputWithOperations[]  // All materials for the part (for dropdown)
}

const props = withDefaults(defineProps<Props>(), {
  editable: false,
  availableMaterials: () => []
})

const emit = defineEmits<{
  linkMaterial: [materialId: number]
  unlinkMaterial: [materialId: number]
}>()

const materials = ref<MaterialInput[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const selectedMaterialId = ref<number | null>(null)

async function loadMaterials() {
  if (!props.operationId) return

  loading.value = true
  error.value = null

  try {
    materials.value = await getOperationMaterials(props.operationId)
  } catch (err) {
    error.value = 'Nepodařilo se načíst materiály'
    console.error('Failed to load operation materials:', err)
  } finally {
    loading.value = false
  }
}

// Get materials not yet linked (for dropdown)
function getUnlinkedMaterials(): MaterialInputWithOperations[] {
  const linkedIds = materials.value.map(m => m.id)
  return props.availableMaterials.filter(m => !linkedIds.includes(m.id))
}

// Format material dimensions for display
function formatMaterialDimensions(material: MaterialInput | MaterialInputWithOperations): string {
  const parts: string[] = []

  if (material.stock_diameter) {
    parts.push(`Ø${material.stock_diameter}`)
  }
  if (material.stock_width) {
    parts.push(`${material.stock_width}`)
  }
  if (material.stock_height) {
    parts.push(`×${material.stock_height}`)
  }
  if (material.stock_length) {
    parts.push(`L${material.stock_length}`)
  }

  if (parts.length === 0 && 'weight_kg' in material && material.weight_kg) {
    return `${material.weight_kg.toFixed(2)}kg`
  }

  return parts.join(' ') || 'bez rozměrů'
}

// Handle link material
async function handleLinkMaterial() {
  if (selectedMaterialId.value) {
    emit('linkMaterial', selectedMaterialId.value)
    selectedMaterialId.value = null
    // Reload materials after linking
    await loadMaterials()
  }
}

// Handle unlink material
async function handleUnlinkMaterial(materialId: number) {
  emit('unlinkMaterial', materialId)
  // Reload materials after unlinking
  await loadMaterials()
}

onMounted(() => {
  loadMaterials()
})

// Watch operationId changes (e.g., when operation is created/updated)
watch(() => props.operationId, () => {
  loadMaterials()
})

// Watch availableMaterials changes (e.g., when materials are linked/unlinked elsewhere)
watch(() => props.availableMaterials, () => {
  loadMaterials()
}, { deep: true })
</script>

<template>
  <div class="material-links-info">
    <label class="material-label">Navázané materiály:</label>

    <div v-if="loading" class="material-status">
      <span class="material-loading">Načítám...</span>
    </div>

    <div v-else-if="error" class="material-status">
      <span class="material-error">{{ error }}</span>
    </div>

    <div v-else-if="materials.length === 0 && !editable" class="material-status">
      <span class="material-empty">Žádné</span>
    </div>

    <!-- READ-ONLY MODE (original) -->
    <div v-else-if="!editable" class="material-list">
      <span
        v-for="(material, index) in materials"
        :key="material.id"
        class="material-item"
      >
        M{{ material.seq }}{{ index < materials.length - 1 ? ', ' : '' }}
      </span>
    </div>

    <!-- EDITABLE MODE (detailed chips) -->
    <div v-else class="material-edit-inline">
      <!-- Existing linked materials (with dimensions) -->
      <span
        v-for="material in materials"
        :key="material.id"
        class="material-chip-detailed"
      >
        <span class="mat-seq">M{{ material.seq }}</span>
        <span class="mat-dims">{{ formatMaterialDimensions(material) }}</span>
        <button
          type="button"
          class="unlink-btn-compact"
          @click.stop="handleUnlinkMaterial(material.id)"
          title="Odpojit"
        >
          ×
        </button>
      </span>

      <!-- Add material dropdown (with dimensions) -->
      <select
        v-if="getUnlinkedMaterials().length > 0"
        v-model="selectedMaterialId"
        class="material-select-detailed"
        @change="handleLinkMaterial"
        @click.stop
      >
        <option :value="null">+ Materiál</option>
        <option
          v-for="mat in getUnlinkedMaterials()"
          :key="mat.id"
          :value="mat.id"
        >
          M{{ mat.seq }}: {{ formatMaterialDimensions(mat) }}
        </option>
      </select>
    </div>
  </div>
</template>

<style scoped>
.material-links-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs);
}

.material-label {
  color: var(--t3);
  font-weight: 500;
}

.material-status {
  color: var(--t3);
  font-style: italic;
}

.material-loading {
  color: var(--t3);
}

.material-error {
  color: var(--err);
}

.material-empty {
  color: var(--t3);
}

.material-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.material-item {
  color: var(--t1);
  font-weight: 500;
  font-family: var(--mono);
}

/* === EDITABLE MODE (DETAILED WITH DIMENSIONS) === */
.material-edit-inline {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.material-chip-detailed {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;
  background: var(--t3);
  border: 1px solid var(--t3);
  border-radius: var(--rs);
  font-size: var(--fs);
  font-weight: 500;
  font-family: var(--mono);
  color: var(--t1);
  white-space: nowrap;
}

.mat-seq {
  font-weight: 600;
  color: var(--t1);
}

.mat-dims {
  font-size: var(--fs);
  color: var(--t3);
  opacity: 0.8;
}

.unlink-btn-compact {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: var(--t3);
  cursor: pointer;
  padding: 0;
  margin-left: 4px;
  font-size: var(--fs);
  line-height: 1;
  transition: color all 100ms var(--ease);
}

.unlink-btn-compact:hover {
  color: var(--err);
}

.material-select-detailed {
  min-width: 140px;
  padding: 4px 6px;
  background: var(--ground);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  font-size: var(--fs);
  font-weight: 500;
  font-family: var(--mono);
  color: var(--t2);
  cursor: pointer;
}

.material-select-detailed:focus {
  outline: none;
  border-color: rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.03);
}
</style>
