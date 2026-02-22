<script setup lang="ts">
/**
 * TimeVision Time Ribbon - Compact 2-row time display under PDF
 * Row 1 (V1): AI čas | Lidský odhad | Skutečný čas
 * Row 2 (V2): Výpočet | Lidský odhad | Skutečný čas
 */
import type { TimeVisionEstimation } from '@/types/time-vision'

interface Props {
  openaiEstimation: TimeVisionEstimation | null
  featuresEstimation: TimeVisionEstimation | null
  activeModel: 'time_v1' | 'features_v2'
}
defineProps<Props>()
const emit = defineEmits<{ switchModel: ['time_v1' | 'features_v2'] }>()

function fmt(val: number | null | undefined): string {
  if (val == null) return '—'
  return val.toFixed(1)
}
</script>

<template>
  <div class="time-ribbon">
    <div class="ribbon-row" :class="{ active: activeModel === 'time_v1' }" @click="emit('switchModel', 'time_v1')">
      <span class="row-label">V1</span>
      <div class="time-cell ai">
        <span class="cell-label">AI</span>
        <span class="cell-value">{{ fmt(openaiEstimation?.estimated_time_min) }}</span>
      </div>
      <div class="time-cell human">
        <span class="cell-label">Odhad</span>
        <span class="cell-value">{{ fmt(openaiEstimation?.human_estimate_min) }}</span>
      </div>
      <div class="time-cell actual">
        <span class="cell-label">Skut.</span>
        <span class="cell-value">{{ fmt(openaiEstimation?.actual_time_min) }}</span>
      </div>
    </div>
    <div class="ribbon-row" :class="{ active: activeModel === 'features_v2' }" @click="emit('switchModel', 'features_v2')">
      <span class="row-label">V2</span>
      <div class="time-cell calc">
        <span class="cell-label">Výp.</span>
        <span class="cell-value">{{ fmt(featuresEstimation?.calculated_time_min) }}</span>
      </div>
      <div class="time-cell human">
        <span class="cell-label">Odhad</span>
        <span class="cell-value">{{ fmt(featuresEstimation?.human_estimate_min) }}</span>
      </div>
      <div class="time-cell actual">
        <span class="cell-label">Skut.</span>
        <span class="cell-value">{{ fmt(featuresEstimation?.actual_time_min) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.time-ribbon {
  flex-shrink: 0;
  border-top: 1px solid var(--b2);
  background: var(--surface);
}
.ribbon-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px var(--pad);
  cursor: pointer;
  transition: background 0.15s;
  border-left: 3px solid transparent;
}
.ribbon-row:first-child {
  border-bottom: 1px solid var(--b2);
}
.ribbon-row:hover { background: var(--b1); }
.ribbon-row.active { border-left-color: var(--b3); background: var(--b1); }
.row-label {
  width: 24px;
  font-size: var(--fs);
  font-weight: 700;
  color: var(--t3);
  flex-shrink: 0;
}
.time-cell {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
}
.cell-label {
  font-size: var(--fs);
  text-transform: uppercase;
  color: var(--t3);
  letter-spacing: 0.03em;
}
.cell-value {
  font-size: var(--fs);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--t1);
}
.time-cell.ai .cell-value { color: var(--red); }
.time-cell.calc .cell-value { color: var(--red); }
.time-cell.human .cell-value { color: var(--t3); }
.time-cell.actual .cell-value { color: var(--ok); }
</style>
