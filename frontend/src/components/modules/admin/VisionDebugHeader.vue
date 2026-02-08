<script setup lang="ts">
/**
 * Vision Debug Header - Part selector and analyze controls
 * LOC: ~60 (L-036 compliant)
 */

import type { VisionDebugPart } from '@/types/vision'
import { Play, Loader } from 'lucide-vue-next'

const props = defineProps<{
  parts: VisionDebugPart[]
  loading: boolean
  analyzing: boolean
  selectedPart: VisionDebugPart | null
}>()

const emit = defineEmits<{
  (e: 'select-part', event: Event): void
  (e: 'analyze'): void
}>()
</script>

<template>
  <div class="vision-debug-header">
    <div class="header-left">
      <h2>Vision Debug - PDF Annotation Refinement</h2>
      <p class="subtitle">Real-time AI-powered feature extraction with error minimization</p>
    </div>

    <div class="header-controls">
      <select
        :value="selectedPart?.id"
        @change="emit('select-part', $event)"
        class="part-selector"
        :disabled="loading || analyzing"
      >
        <option :value="null" disabled>Select a part...</option>
        <option v-for="part in parts" :key="part.id" :value="part.id">
          {{ part.part_number }} - {{ part.description || 'No description' }}
        </option>
      </select>

      <button
        class="btn btn-primary"
        @click="emit('analyze')"
        :disabled="!selectedPart || analyzing"
      >
        <Play :size="16" v-if="!analyzing" />
        <Loader :size="16" v-else class="spin" />
        {{ analyzing ? 'Analyzing...' : 'Analyze' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.vision-debug-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
}

.header-left h2 {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.subtitle {
  margin: var(--space-1) 0 0;
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.header-controls {
  display: flex;
  gap: var(--space-3);
  align-items: center;
}

.part-selector {
  min-width: 300px;
  padding: var(--space-2) var(--space-3);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
