<script setup lang="ts">
import { computed, watch } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useOperationsStore } from '@/stores/operations'
import type { ContextGroup } from '@/types/workspace'
import { formatDuration } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()
const ops = useOperationsStore()

const part = computed(() => parts.getFocusedPart(props.ctx))

const operations = computed(() => {
  if (!part.value) return []
  return ops.forPart(part.value.id)
})

const totalSetup = computed(() => operations.value.reduce((s, o) => s + o.setup_time_min, 0))
const totalOp = computed(() => operations.value.reduce((s, o) => s + o.operation_time_min, 0))

function cuttingLabel(mode: string): string {
  if (mode === 'low') return 'LOW'
  if (mode === 'high') return 'HIGH'
  return 'MID'
}

watch(
  part,
  (p) => {
    if (p && !ops.byPartId[p.id]) ops.fetchByPartId(p.id)
  },
  { immediate: true },
)
</script>

<template>
  <div class="wops">
    <!-- No part selected -->
    <div v-if="!part" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Vyberte díl ze seznamu</span>
    </div>

    <!-- Loading -->
    <div v-else-if="ops.loading && !operations.length" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- No operations -->
    <div v-else-if="!operations.length" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Díl nemá žádné operace</span>
    </div>

    <!-- Operations — reference .rib + .ot table pattern -->
    <template v-else>
      <!-- Summary ribbon -->
      <div class="rib">
        <div class="rib-r">
          <div class="rib-i">
            <span class="rib-l">Seřízení</span>
            <span class="rib-v m">{{ formatDuration(totalSetup) }}</span>
          </div>
          <div class="rib-i">
            <span class="rib-l">Výroba</span>
            <span class="rib-v m">{{ formatDuration(totalOp) }}</span>
          </div>
          <div class="rib-i">
            <span class="rib-l">Operací</span>
            <span class="rib-v m">{{ operations.length }}</span>
          </div>
        </div>
      </div>

      <!-- Operations table — reference .ot pattern -->
      <div class="ot-wrap">
        <table class="ot">
          <thead>
            <tr>
              <th style="width:32px">#</th>
              <th>Název</th>
              <th class="r" style="width:90px">Seřízení</th>
              <th class="r" style="width:90px">Výroba</th>
              <th class="r" style="width:38px">Mode</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="op in operations"
              :key="op.id"
              :data-testid="`op-row-${op.id}`"
            >
              <td class="mono t4">{{ op.seq }}</td>
              <td>{{ op.name || 'Bez názvu' }}</td>
              <td class="r">
                <span class="tb s">
                  <span class="d" />
                  {{ formatDuration(op.setup_time_min) }}
                </span>
              </td>
              <td class="r">
                <span class="tb o">
                  <span class="d" />
                  {{ formatDuration(op.operation_time_min) }}
                </span>
              </td>
              <td class="r">
                <span v-if="op.is_coop" class="cm-badge coop">COOP</span>
                <span v-else :class="['cm-badge', `cm-${op.cutting_mode}`]">
                  {{ cuttingLabel(op.cutting_mode) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wops {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* ─── Placeholder ─── */
.mod-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
}
.mod-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--b2);
}
.mod-label { font-size: var(--fsl); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

/* ─── Summary ribbon — reference .rib ─── */
.rib {
  padding: 6px var(--pad);
  background: rgba(255,255,255,0.02);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.rib-r { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.rib-i { display: flex; align-items: baseline; gap: 4px; }
.rib-l { font-size: 10px; color: var(--t4); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 500; }
.rib-v { font-size: var(--fs); color: var(--t1); font-weight: 500; }
.rib-v.m { font-family: var(--mono); }

/* ─── Table wrapper ─── */
.ot-wrap {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

/* ─── Operations table — reference .ot ─── */
.ot {
  width: 100%;
  border-collapse: collapse;
}
.ot thead {
  background: rgba(255,255,255,0.025);
  position: sticky;
  top: 0;
  z-index: 2;
}
.ot th {
  padding: 4px var(--pad);
  font-size: 10px;
  font-weight: 600;
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  text-align: left;
  border-bottom: 1px solid var(--b2);
  white-space: nowrap;
}
.ot th.r { text-align: right; }
.ot td {
  padding: 4px var(--pad);
  font-size: var(--fs);
  color: var(--t2);
  border-bottom: 1px solid rgba(255,255,255,0.025);
}
.ot td.r { text-align: right; }
.ot tbody tr:hover td { background: var(--b1); }
.mono { font-family: var(--mono); }
.t4 { color: var(--t4); }

/* ─── Time badge — reference .tb ─── */
.tb {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 5px;
  font-family: var(--mono);
  font-size: 10px;
  border-radius: 99px;
  background: var(--b1);
  color: var(--t2);
  white-space: nowrap;
}
.tb .d {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  flex-shrink: 0;
}
.tb.s .d { background: var(--red); }  /* setup = red dot */
.tb.o .d { background: var(--ok); }   /* operation = green dot */

/* ─── Cutting mode badge ─── */
.cm-badge {
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.06em;
  padding: 1px 4px;
  border-radius: var(--rs);
}
.cm-low  { background: var(--b1); color: var(--t3); }
.cm-mid  { background: var(--b1); color: var(--t2); }
.cm-high { background: var(--red-10); color: var(--red); }
.coop   { background: var(--b1); color: var(--t3); }
</style>
