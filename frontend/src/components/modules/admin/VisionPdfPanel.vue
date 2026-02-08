<script setup lang="ts">
/**
 * Vision PDF Panel - Displays PDF with optional iteration badge
 *
 * Reusable panel for showing original or annotated PDFs
 * LOC: ~50 (L-036 compliant)
 */

import { Loader } from 'lucide-vue-next'

const props = defineProps<{
  title: string
  pdfUrl: string
  iteration?: number
  loading?: boolean
}>()
</script>

<template>
  <div class="vision-pdf-panel">
    <div class="panel-header">
      <h3>{{ title }}</h3>
      <div v-if="iteration && iteration > 0" class="iteration-badge">
        Iteration {{ iteration }}
      </div>
    </div>

    <div class="panel-content">
      <embed
        v-if="pdfUrl"
        :src="pdfUrl"
        type="application/pdf"
        class="pdf-viewer"
      />
      <div v-else class="empty-state">
        <Loader v-if="loading" :size="48" class="spin" />
        <p v-else>{{ title === 'Original PDF' ? 'No PDF selected' : 'Click "Analyze" to start' }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.vision-pdf-panel {
  display: flex;
  flex-direction: column;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
  height: 100%;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--bg-raised);
  border-bottom: 1px solid var(--border-default);
}

.panel-header h3 {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.iteration-badge {
  padding: var(--space-1) var(--space-2);
  background: var(--color-info);
  color: white;
  border-radius: var(--radius-sm);
  font-size: var(--text-2xs);
  font-weight: var(--font-medium);
}

.panel-content {
  flex: 1;
  overflow: auto;
  position: relative;
}

.pdf-viewer {
  width: 100%;
  height: 100%;
  border: none;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-secondary);
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
