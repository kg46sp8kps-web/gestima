<script setup lang="ts">
import { computed } from 'vue'
import type { MachiningTimeEstimation } from '@/types/estimation'
import { Clock } from 'lucide-vue-next'
import TimeBreakdownWidget from './TimeBreakdownWidget.vue'
import GeometryInfoWidget from './GeometryInfoWidget.vue'
import ConstraintsWidget from './ConstraintsWidget.vue'

interface Props {
  result: MachiningTimeEstimation
}

const props = defineProps<Props>()

const totalTimeDisplay = computed(() => props.result.total_time_min.toFixed(2))

const hasConstraints = computed(() =>
  props.result.breakdown.critical_constraints?.length > 0
)
</script>

<template>
  <div class="estimation-detail-panel">
    <div class="panel-header">
      <h2>{{ result.filename }}</h2>
      <span class="part-type-badge" :class="result.part_type.toLowerCase()">
        {{ result.part_type }}
      </span>
    </div>

    <div class="total-time-section">
      <div class="total-time-value">
        <Clock :size="32" class="time-icon" />
        <div>
          <div class="time-display">{{ totalTimeDisplay }} min</div>
          <div class="time-label">Total Machining Time</div>
        </div>
      </div>
    </div>

    <TimeBreakdownWidget
      :roughing-min="result.roughing_time_min"
      :finishing-min="result.finishing_time_min"
      :setup-min="result.setup_time_min"
      :total-min="result.total_time_min"
    />

    <GeometryInfoWidget
      :material="result.breakdown.material"
      :stock-volume-mm3="result.breakdown.stock_volume_mm3"
      :part-volume-mm3="result.breakdown.part_volume_mm3"
      :material-to-remove-mm3="result.breakdown.material_to_remove_mm3"
      :material-removal-percent="result.breakdown.material_removal_percent"
      :surface-area-mm2="result.breakdown.surface_area_mm2"
    />

    <ConstraintsWidget
      v-if="hasConstraints"
      :constraints="result.breakdown.critical_constraints"
      :multiplier="result.breakdown.constraint_multiplier"
    />
  </div>
</template>

<style scoped>
.estimation-detail-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: var(--space-6);
  overflow-y: auto;
  height: 100%;
  background: var(--bg-base);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border-default);
}

.panel-header h2 {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
}

.part-type-badge {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  border-radius: var(--radius-sm);
  text-transform: uppercase;
}

.part-type-badge.rot {
  background: var(--color-info);
  color: white;
}

.part-type-badge.pri {
  background: var(--color-success);
  color: white;
}

.total-time-section {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.total-time-value {
  display: flex;
  align-items: center;
  gap: var(--space-5);
}

.time-icon {
  color: var(--color-primary);
}

.time-display {
  font-size: var(--text-5xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  line-height: 1;
}

.time-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-top: var(--space-2);
}
</style>
