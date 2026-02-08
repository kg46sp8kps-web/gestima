<script setup lang="ts">
/**
 * Vision Features Panel - Displays extracted features data
 *
 * Shows list of features with:
 * - Feature type and error percentage
 * - Dimension, depth, STEP data
 * - Color-coded by error threshold
 *
 * LOC: ~100 (L-036 compliant)
 */

import type { RefinementFeature } from '@/types/vision'

const props = defineProps<{
  features: RefinementFeature[]
}>()
</script>

<template>
  <div class="vision-features-panel">
    <div class="panel-header">
      <h3>Extraction Data</h3>
    </div>

    <div class="panel-content">
      <div v-if="features.length === 0" class="empty-state">
        <p>No features extracted yet</p>
      </div>

      <div v-else class="feature-cards">
        <div
          v-for="(feature, idx) in features"
          :key="idx"
          :class="['feature-card', {
            'error-low': feature.dimension_error < 5,
            'error-high': feature.dimension_error > 10
          }]"
        >
          <div class="feature-header">
            <span class="feature-type">{{ feature.type || 'unknown' }}</span>
            <span
              v-if="feature.dimension_error != null"
              :class="['feature-error', {
                'success': feature.dimension_error < 5,
                'danger': feature.dimension_error > 10
              }]"
            >
              {{ feature.dimension_error.toFixed(1) }}% error
            </span>
          </div>

          <div class="feature-body">
            <div v-if="feature.dimension != null" class="feature-row">
              <span class="key">Dimension:</span>
              <span class="value">Ø{{ feature.dimension.toFixed(2) }} mm</span>
            </div>
            <div v-if="feature.depth != null" class="feature-row">
              <span class="key">Depth:</span>
              <span class="value">{{ feature.depth.toFixed(2) }} mm</span>
            </div>
            <div v-if="feature.step_data?.r_avg != null" class="feature-row">
              <span class="key">STEP r_avg:</span>
              <span class="value">{{ feature.step_data.r_avg.toFixed(2) }} mm</span>
            </div>
            <div v-if="feature.step_data?.length != null" class="feature-row">
              <span class="key">STEP length:</span>
              <span class="value">{{ feature.step_data.length.toFixed(2) }} mm</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.vision-features-panel {
  display: flex;
  flex-direction: column;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
  height: 100%;
}

.panel-header {
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

.panel-content {
  flex: 1;
  overflow: auto;
  padding: var(--space-3);
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.feature-cards {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.feature-card {
  padding: var(--space-3);
  background: var(--bg-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  transition: border-color var(--duration-fast);
}

.feature-card.error-low {
  border-color: var(--color-success);
}

.feature-card.error-high {
  border-color: var(--color-danger);
}

.feature-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-default);
}

.feature-type {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  text-transform: uppercase;
}

.feature-error {
  font-size: var(--text-2xs);
  font-family: var(--font-mono);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--bg-base);
}

.feature-error.success {
  color: var(--color-success);
  background: var(--color-success-light);
}

.feature-error.danger {
  color: var(--color-danger);
  background: rgba(244, 63, 94, 0.1);
}

.feature-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.feature-row {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-xs);
}

.feature-row .key {
  color: var(--text-secondary);
}

.feature-row .value {
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-weight: var(--font-medium);
}
</style>
