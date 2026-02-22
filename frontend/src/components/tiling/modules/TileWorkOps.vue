<script setup lang="ts">
import { computed, watch } from 'vue'
import { Clock, Wrench, Users } from 'lucide-vue-next'
import { usePartsStore } from '@/stores/parts'
import { useOperationsStore } from '@/stores/operations'
import type { ContextGroup } from '@/types/workspace'
import type { Operation } from '@/types/operation'
import { formatDuration } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'
import { ICON_SIZE_SM } from '@/config/design'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()
const ops = useOperationsStore()

const part = computed(() => parts.getFocusedPart(props.ctx))

const operations = computed<Operation[]>(() => {
  if (!part.value) return []
  return ops.forPart(part.value.id)
})

const totalSetup = computed(() =>
  operations.value.reduce((s, o) => s + o.setup_time_min, 0)
)
const totalOp = computed(() =>
  operations.value.reduce((s, o) => s + o.operation_time_min, 0)
)

function cuttingModeLabel(mode: string): string {
  switch (mode) {
    case 'low': return 'LOW'
    case 'high': return 'HIGH'
    default: return 'MID'
  }
}

function cuttingModeClass(mode: string): string {
  switch (mode) {
    case 'low': return 'cm-low'
    case 'high': return 'cm-high'
    default: return 'cm-mid'
  }
}

watch(part, (p) => {
  if (p && !ops.byPartId[p.id]) {
    ops.fetchByPartId(p.id)
  }
}, { immediate: true })
</script>

<template>
  <div class="wops">
    <!-- Empty: no part selected -->
    <div v-if="!part" class="wops-state">
      <div class="wops-state-dot" />
      <div class="wops-state-label">Vyberte díl ze seznamu</div>
    </div>

    <!-- Loading -->
    <div v-else-if="ops.loading && !operations.length" class="wops-state">
      <Spinner size="sm" text="Načítám operace..." />
    </div>

    <!-- No operations -->
    <div v-else-if="!operations.length" class="wops-state">
      <div class="wops-state-dot" />
      <div class="wops-state-label">Díl nemá žádné operace</div>
    </div>

    <!-- Operations list -->
    <div v-else class="wops-list">
      <!-- Summary row -->
      <div class="wops-summary">
        <div class="wops-sum-item">
          <Clock :size="ICON_SIZE_SM" />
          <span>Seřízení: {{ formatDuration(totalSetup) }}</span>
        </div>
        <div class="wops-sum-item">
          <Clock :size="ICON_SIZE_SM" />
          <span>Výroba: {{ formatDuration(totalOp) }}</span>
        </div>
        <div class="wops-sum-item">
          <span class="wops-count">{{ operations.length }} op.</span>
        </div>
      </div>

      <!-- Operation rows -->
      <div
        v-for="op in operations"
        :key="op.id"
        class="oprow"
        :data-testid="`op-row-${op.id}`"
      >
        <div class="oprow-seq">{{ op.seq }}</div>
        <div class="oprow-body">
          <div class="oprow-top">
            <div class="oprow-name">{{ op.name || 'Bez názvu' }}</div>
            <div v-if="op.is_coop" class="oprow-coop">
              <Users :size="ICON_SIZE_SM" />
              <span>Kooperace</span>
            </div>
            <div v-else :class="['oprow-cm', cuttingModeClass(op.cutting_mode)]">
              {{ cuttingModeLabel(op.cutting_mode) }}
            </div>
          </div>
          <div class="oprow-times">
            <span class="oprow-time">
              <Clock :size="ICON_SIZE_SM" />
              Seřízení: {{ formatDuration(op.setup_time_min) }}
            </span>
            <span class="oprow-time">
              <Wrench :size="ICON_SIZE_SM" />
              Výroba: {{ formatDuration(op.operation_time_min) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wops {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  container-type: inline-size;
}

/* ─── States ─── */
.wops-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
}
.wops-state-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--b2);
}
.wops-state-label { font-size: var(--fs); }

/* ─── List ─── */
.wops-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* ─── Summary row ─── */
.wops-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px var(--pad);
  border-bottom: 1px solid var(--b1);
  background: var(--raised);
  flex-shrink: 0;
}
.wops-sum-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fsl);
  color: var(--t3);
}
.wops-count {
  font-family: var(--mono);
  font-size: var(--fsl);
  color: var(--t4);
  margin-left: auto;
}

/* ─── Operation row ─── */
.oprow {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px var(--pad);
  border-bottom: 1px solid var(--b1);
}
.oprow:last-child { border-bottom: none; }
.oprow:hover { background: rgba(255,255,255,0.02); }

.oprow-seq {
  font-family: var(--mono);
  font-size: var(--fsl);
  color: var(--t4);
  width: 24px;
  flex-shrink: 0;
  padding-top: 2px;
}

.oprow-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.oprow-top {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.oprow-name {
  font-size: var(--fs);
  color: var(--t1);
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Cutting mode badge */
.oprow-cm {
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.08em;
  padding: 1px 5px;
  border-radius: var(--rs);
  flex-shrink: 0;
}
.cm-low { background: var(--b1); color: var(--t3); }
.cm-mid { background: var(--b1); color: var(--t2); }
.cm-high { background: var(--red-10); color: var(--red); }

/* Coop badge */
.oprow-coop {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: var(--fsl);
  color: var(--t3);
  flex-shrink: 0;
}

.oprow-times {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.oprow-time {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: var(--fsl);
  font-family: var(--mono);
  color: var(--t3);
}
</style>
