<script setup lang="ts">
/**
 * MaterialLinksInfo - Zobrazení navázaných materiálů k operaci
 * BUILDING BLOCKS (L-039): Reusable read-only component
 */

import { ref, onMounted } from 'vue'
import { getOperationMaterials } from '@/api/materialInputs'
import type { MaterialInput } from '@/types/material'

interface Props {
  operationId: number
}

const props = defineProps<Props>()

const materials = ref<MaterialInput[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

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

onMounted(() => {
  loadMaterials()
})
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

    <div v-else-if="materials.length === 0" class="material-status">
      <span class="material-empty">Žádné</span>
    </div>

    <div v-else class="material-list">
      <span
        v-for="(material, index) in materials"
        :key="material.id"
        class="material-item"
      >
        M{{ material.seq }}{{ index < materials.length - 1 ? ', ' : '' }}
      </span>
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
</style>
