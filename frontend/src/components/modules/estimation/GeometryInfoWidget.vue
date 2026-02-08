<script setup lang="ts">
import { Box } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'

interface Props {
  material: string
  stockVolumeMm3: number
  partVolumeMm3: number
  materialToRemoveMm3: number
  materialRemovalPercent: number
  surfaceAreaMm2: number
}

defineProps<Props>()

function volumeInCm3(volumeMm3: number): string {
  return (volumeMm3 / 1000).toFixed(1)
}

function areaInCm2(areaMm2: number): string {
  return (areaMm2 / 100).toFixed(1)
}
</script>

<template>
  <div class="geometry-info-widget">
    <h3>
      <Box :size="ICON_SIZE.STANDARD" />
      Material & Geometry
    </h3>
    <div class="info-grid">
      <div class="info-item">
        <span class="info-label">Material</span>
        <span class="info-value">{{ material }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">Stock Volume</span>
        <span class="info-value">{{ volumeInCm3(stockVolumeMm3) }} cm³</span>
      </div>
      <div class="info-item">
        <span class="info-label">Part Volume</span>
        <span class="info-value">{{ volumeInCm3(partVolumeMm3) }} cm³</span>
      </div>
      <div class="info-item">
        <span class="info-label">Material to Remove</span>
        <span class="info-value removal">
          {{ volumeInCm3(materialToRemoveMm3) }} cm³
          <span class="removal-percent">({{ materialRemovalPercent.toFixed(0) }}%)</span>
        </span>
      </div>
      <div class="info-item">
        <span class="info-label">Surface Area</span>
        <span class="info-value">{{ areaInCm2(surfaceAreaMm2) }} cm²</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.geometry-info-widget {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
}

h3 {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--space-4) 0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-4);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.info-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  text-transform: uppercase;
}

.info-value {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.info-value.removal {
  color: var(--color-primary);
}

.removal-percent {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  margin-left: var(--space-2);
}
</style>
