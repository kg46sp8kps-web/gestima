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
  gap: var(--space-2);
  font-size: var(--text-xs);
}

.material-label {
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

.material-status {
  color: var(--text-tertiary);
  font-style: italic;
}

.material-loading {
  color: var(--text-secondary);
}

.material-error {
  color: var(--color-danger);
}

.material-empty {
  color: var(--text-tertiary);
}

.material-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.material-item {
  color: var(--text-primary);
  font-weight: var(--font-medium);
  font-family: var(--font-mono);
}

/* === EDITABLE MODE (DETAILED WITH DIMENSIONS) === */
.material-edit-inline {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

.material-chip-detailed {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  background: var(--palette-info, rgba(37, 99, 235, 0.2));
  border: 1px solid var(--palette-info);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  font-family: var(--font-mono);
  color: var(--text-primary);
  white-space: nowrap;
}

.mat-seq {
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.mat-dims {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  opacity: 0.8;
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
  margin-left: var(--space-1);
  font-size: var(--text-sm);
  line-height: 1;
  transition: color var(--transition-fast);
}

.unlink-btn-compact:hover {
  color: var(--palette-danger);
}

.material-select-detailed {
  min-width: 140px;
  padding: var(--space-1) var(--space-2);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  font-family: var(--font-mono);
  color: var(--text-body);
  cursor: pointer;
}

.material-select-detailed:focus {
  outline: none;
  border-color: var(--state-focus-border);
  background: var(--state-focus-bg);
}
</style>
