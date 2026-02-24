<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useOperationsStore } from '@/stores/operations'
import { useItemTypeGuard } from '@/composables/useItemTypeGuard'
import * as wcApi from '@/api/work-centers'
import type { ContextGroup } from '@/types/workspace'
import type { Operation, CuttingMode } from '@/types/operation'
import type { WorkCenter } from '@/types/work-center'
import { formatDuration } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

interface OpDraft {
  name: string
  setup_time_min: number
  operation_time_min: number
  work_center_id: number | null
  cutting_mode: CuttingMode
}

const props = defineProps<Props>()
const parts = usePartsStore()
const ops = useOperationsStore()
const typeGuard = useItemTypeGuard(['part'])

const part = computed(() => parts.getFocusedPart(props.ctx))

const operations = computed(() => {
  if (!part.value) return []
  return ops.forPart(part.value.id)
})

const totalSetup = computed(() => operations.value.reduce((s, o) => s + o.setup_time_min, 0))
const totalOp = computed(() => operations.value.reduce((s, o) => s + o.operation_time_min, 0))

const workCenters = ref<WorkCenter[]>([])
const drafts = reactive<Record<number, OpDraft>>({})

/** Safe accessor — always returns the reactive draft object */
function d(opId: number): OpDraft {
  return drafts[opId] ?? { name: '', setup_time_min: 0, operation_time_min: 0, work_center_id: null, cutting_mode: 'mid' }
}

function initDraft(op: Operation) {
  if (!drafts[op.id]) {
    drafts[op.id] = {
      name: op.name,
      setup_time_min: op.setup_time_min,
      operation_time_min: op.operation_time_min,
      work_center_id: op.work_center_id,
      cutting_mode: op.cutting_mode,
    }
  }
}

function resetDraft(op: Operation) {
  drafts[op.id] = {
    name: op.name,
    setup_time_min: op.setup_time_min,
    operation_time_min: op.operation_time_min,
    work_center_id: op.work_center_id,
    cutting_mode: op.cutting_mode,
  }
}

async function saveOp(op: Operation) {
  const draft = drafts[op.id]
  if (!draft || !part.value) return
  const setup = isNaN(draft.setup_time_min) ? 0 : draft.setup_time_min
  const optime = isNaN(draft.operation_time_min) ? 0 : draft.operation_time_min
  const changed =
    draft.name !== op.name ||
    setup !== op.setup_time_min ||
    optime !== op.operation_time_min ||
    draft.work_center_id !== op.work_center_id ||
    draft.cutting_mode !== op.cutting_mode
  if (!changed) return
  draft.setup_time_min = setup
  draft.operation_time_min = optime
  await ops.updateOp(op.id, part.value.id, {
    name: draft.name,
    setup_time_min: setup,
    operation_time_min: optime,
    work_center_id: draft.work_center_id ?? undefined,
    cutting_mode: draft.cutting_mode,
    version: op.version,
  })
}

function onWcChange(op: Operation, e: Event) {
  const val = (e.target as HTMLSelectElement).value
  const dr = drafts[op.id]
  if (dr) dr.work_center_id = val ? Number(val) : null
  saveOp(op)
}

function onModeChange(op: Operation, e: Event) {
  const val = (e.target as HTMLSelectElement).value as CuttingMode
  const dr = drafts[op.id]
  if (dr) dr.cutting_mode = val
  saveOp(op)
}

function onEscape(e: KeyboardEvent, op: Operation) {
  e.preventDefault()
  resetDraft(op)
  ;(e.target as HTMLElement).blur()
}

watch(
  operations,
  (list) => { list.forEach(initDraft) },
  { immediate: true },
)

watch(
  part,
  (p) => {
    if (p && !ops.byPartId[p.id]) ops.fetchByPartId(p.id)
  },
  { immediate: true },
)

onMounted(async () => {
  try {
    workCenters.value = (await wcApi.getAll()).filter(w => w.is_active)
  } catch {
    // WC list is optional
  }
})
</script>

<template>
  <div class="wops">
    <!-- Unsupported item type -->
    <div v-if="!typeGuard.isSupported(props.ctx)" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Nedostupné pro {{ typeGuard.focusedTypeName(props.ctx) }}</span>
    </div>

    <!-- No part selected -->
    <div v-else-if="!part" class="mod-placeholder">
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

    <!-- Operations -->
    <template v-else>
      <!-- Summary ribbon -->
      <div class="rib">
        <div class="rib-r">
          <div class="rib-i">
            <span class="rib-l">Seřízení</span>
            <span class="rib-v">{{ formatDuration(totalSetup) }}</span>
          </div>
          <div class="rib-i">
            <span class="rib-l">Výroba</span>
            <span class="rib-v">{{ formatDuration(totalOp) }}</span>
          </div>
          <div class="rib-i">
            <span class="rib-l">Operací</span>
            <span class="rib-v">{{ operations.length }}</span>
          </div>
        </div>
      </div>

      <!-- Operations table -->
      <div class="ot-wrap">
        <table class="ot">
          <thead>
            <tr>
              <th style="width:28px">#</th>
              <th>Název</th>
              <th style="width:96px">Pracoviště</th>
              <th class="r" style="width:66px">Seř. (min)</th>
              <th class="r" style="width:66px">Výr. (min)</th>
              <th class="r" style="width:48px">Mode</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="op in operations"
              :key="op.id"
              :data-testid="`op-row-${op.id}`"
              class="op-row"
            >
              <td class="t4">{{ op.seq }}</td>
              <td>
                <input
                  class="gi gi-text"
                  type="text"
                  :value="d(op.id).name"
                  placeholder="Název…"
                  :data-testid="`op-name-${op.id}`"
                  @input="d(op.id).name = ($event.target as HTMLInputElement).value"
                  @blur="saveOp(op)"
                  @keydown.enter.prevent="($event.target as HTMLElement).blur()"
                  @keydown.escape="onEscape($event, op)"
                />
              </td>
              <td>
                <select
                  class="gi gi-sel"
                  :value="d(op.id).work_center_id ?? ''"
                  :data-testid="`op-wc-${op.id}`"
                  @change="onWcChange(op, $event)"
                  @keydown.escape="onEscape($event, op)"
                >
                  <option value="">—</option>
                  <option v-for="wc in workCenters" :key="wc.id" :value="wc.id">{{ wc.name }}</option>
                </select>
              </td>
              <td class="r">
                <input
                  v-model.number="d(op.id).setup_time_min"
                  class="gi gi-num"
                  type="number"
                  step="1"
                  min="0"
                  :data-testid="`op-setup-${op.id}`"
                  @blur="saveOp(op)"
                  @keydown.enter.prevent="($event.target as HTMLElement).blur()"
                  @keydown.escape="onEscape($event, op)"
                />
              </td>
              <td class="r">
                <input
                  v-model.number="d(op.id).operation_time_min"
                  class="gi gi-num"
                  type="number"
                  step="1"
                  min="0"
                  :data-testid="`op-optime-${op.id}`"
                  @blur="saveOp(op)"
                  @keydown.enter.prevent="($event.target as HTMLElement).blur()"
                  @keydown.escape="onEscape($event, op)"
                />
              </td>
              <td class="r">
                <select
                  v-if="!op.is_coop"
                  class="gi gi-sel-sm"
                  :value="d(op.id).cutting_mode"
                  :data-testid="`op-mode-${op.id}`"
                  @change="onModeChange(op, $event)"
                  @keydown.escape="onEscape($event, op)"
                >
                  <option value="low">LOW</option>
                  <option value="mid">MID</option>
                  <option value="high">HIGH</option>
                </select>
                <span v-else class="cm-badge coop">COOP</span>
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
.mod-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--b2); }
.mod-label { font-size: var(--fsl); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

/* ─── Summary ribbon ─── */
.rib {
  padding: 6px var(--pad);
  background: rgba(255,255,255,0.02);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.rib-r { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; }
.rib-i { display: flex; align-items: baseline; gap: 4px; }
.rib-l { font-size: var(--fsm); color: var(--t4); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 500; }
.rib-v { font-size: var(--fs); color: var(--t1); font-weight: 500; }

/* ─── Table wrapper ─── */
.ot-wrap { flex: 1; overflow-y: auto; overflow-x: hidden; min-height: 0; }

/* ─── Table ─── */
.t4 { color: var(--t4); }
.r { text-align: right; }
.op-row:hover td { background: rgba(255,255,255,0.015); }

/* ─── Ghost inputs — zero layout shift ─── */
.gi {
  background: transparent;
  border: none;
  border-bottom: 1px solid transparent;
  color: var(--t2);
  font-size: var(--fs);
  font-family: var(--font);
  padding: 0;
  margin: 0;
  line-height: inherit;
  outline: none;
  transition: border-bottom-color 120ms var(--ease), color 100ms var(--ease);
}
.gi::placeholder { color: var(--t4); }
.gi:hover { border-bottom-color: var(--b2); }
.gi:focus { border-bottom-color: var(--b3); color: var(--t1); }

.gi-text { width: 100%; }

.gi-num {
  font-family: var(--mono);
  font-size: var(--fsm);
  color: var(--t3);
  width: 54px;
  text-align: right;
}
.gi-num:focus { color: var(--t1); }
/* Hide native number spinners */
.gi-num::-webkit-outer-spin-button,
.gi-num::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.gi-num[type=number] { -moz-appearance: textfield; }

.gi-sel {
  cursor: pointer;
  color: var(--t4);
  width: 100%;
  appearance: none;
  -webkit-appearance: none;
}
.gi-sel:focus { color: var(--t2); }

.gi-sel-sm {
  cursor: pointer;
  font-size: var(--fss);
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--t3);
  width: 44px;
  appearance: none;
  -webkit-appearance: none;
}
.gi-sel-sm:focus { color: var(--t2); }

/* ─── Cutting mode badge (coop only) ─── */
.cm-badge {
  font-size: var(--fss);
  font-weight: 600;
  letter-spacing: 0.06em;
  padding: 1px 4px;
  border-radius: var(--rs);
}
.coop { background: var(--b1); color: var(--t3); }
</style>
