<script setup lang="ts">
/**
 * TimeVision - Operation Breakdown Table
 */
import { computed } from 'vue'
import type { TimeVisionEstimation, OperationBreakdown } from '@/types/time-vision'

interface Props {
  estimation: TimeVisionEstimation
}
const props = defineProps<Props>()

const breakdown = computed<OperationBreakdown[]>(() => {
  if (!props.estimation.estimation_breakdown_json) return []
  try {
    return JSON.parse(props.estimation.estimation_breakdown_json)
  } catch {
    return []
  }
})

const totalTime = computed(() => {
  return breakdown.value.reduce((sum, op) => sum + (op.time_min ?? 0), 0)
})
</script>

<template>
  <div v-if="breakdown.length > 0" class="operation-breakdown">
    <h4>Rozpad operací</h4>
    <table>
      <thead>
        <tr>
          <th>Operace</th>
          <th class="num">Čas (min)</th>
          <th>Poznámka</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(op, idx) in breakdown" :key="idx">
          <td class="op-name">{{ op.operation }}</td>
          <td class="num">{{ op.time_min != null ? Number(op.time_min).toFixed(0) : '—' }}</td>
          <td class="notes">{{ op.notes ?? '' }}</td>
        </tr>
      </tbody>
      <tfoot>
        <tr>
          <td><strong>Celkem</strong></td>
          <td class="num"><strong>{{ totalTime.toFixed(0) }}</strong></td>
          <td></td>
        </tr>
      </tfoot>
    </table>
  </div>
</template>

<style scoped>
.operation-breakdown {
  margin-bottom: var(--space-4);
}
.operation-breakdown h4 {
  font-size: var(--text-xs);
  text-transform: uppercase;
  color: var(--text-muted);
  margin: 0 0 var(--space-2) 0;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}
th, td {
  padding: var(--space-1) var(--space-2);
  text-align: left;
  border-bottom: 1px solid var(--border-subtle);
}
th {
  font-size: var(--text-xs);
  color: var(--text-muted);
  font-weight: 600;
}
.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.op-name {
  font-weight: 500;
}
.notes {
  color: var(--text-secondary);
  font-size: var(--text-xs);
}
tfoot td {
  border-top: 2px solid var(--border-default);
  border-bottom: none;
}
</style>
