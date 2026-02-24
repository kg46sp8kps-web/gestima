<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useOperationsStore } from '@/stores/operations'
import { useItemTypeGuard } from '@/composables/useItemTypeGuard'
import { useDialog } from '@/composables/useDialog'
import * as wcApi from '@/api/work-centers'
import type { ContextGroup } from '@/types/workspace'
import type { Operation } from '@/types/operation'
import type { WorkCenter } from '@/types/work-center'
import Spinner from '@/components/ui/Spinner.vue'
import WcCombobox from '@/components/ui/WcCombobox.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

interface OpDraft {
  setup_time_min: number | null
  operation_time_min: number | null
  work_center_id: number | null
  ke: number
  ko: number
}

const props = defineProps<Props>()
const parts = usePartsStore()
const ops = useOperationsStore()
const typeGuard = useItemTypeGuard(['part'])
const dialog = useDialog()

const part = computed(() => parts.getFocusedPart(props.ctx))

const operations = computed(() => {
  if (!part.value) return []
  return ops.forPart(part.value.id)
})

const workCenters = ref<WorkCenter[]>([])
const drafts = reactive<Record<number, OpDraft>>({})
const activeOpId = ref<number | null>(null)
const openDetails = ref(new Set<number>())

const wcComboRefs = ref<Record<number, { focus: () => void }>>({})
const optimeRefs = ref<Record<number, HTMLInputElement>>({})
const keRefs = ref<Record<number, HTMLInputElement>>({})
const koRefs = ref<Record<number, HTMLInputElement>>({})

function d(opId: number): OpDraft {
  return (
    drafts[opId] ?? {
      setup_time_min: 0,
      operation_time_min: 0,
      work_center_id: null,
      ke: 100,
      ko: 100,
    }
  )
}

function initDraft(op: Operation) {
  if (!drafts[op.id]) {
    drafts[op.id] = {
      setup_time_min: op.setup_time_min,
      operation_time_min: op.operation_time_min,
      work_center_id: op.work_center_id,
      ke: op.machine_utilization_coefficient,
      ko: op.manning_coefficient,
    }
  }
}

function resetDraft(op: Operation) {
  drafts[op.id] = {
    setup_time_min: op.setup_time_min,
    operation_time_min: op.operation_time_min,
    work_center_id: op.work_center_id,
    ke: op.machine_utilization_coefficient,
    ko: op.manning_coefficient,
  }
}

async function saveOp(op: Operation) {
  const draft = drafts[op.id]
  if (!draft || !part.value) return
  const setup =
    draft.setup_time_min == null || isNaN(draft.setup_time_min) ? 0 : draft.setup_time_min
  const optime =
    draft.operation_time_min == null || isNaN(draft.operation_time_min)
      ? 0
      : draft.operation_time_min
  const changed =
    setup !== op.setup_time_min ||
    optime !== op.operation_time_min ||
    draft.work_center_id !== op.work_center_id ||
    draft.ke !== op.machine_utilization_coefficient ||
    draft.ko !== op.manning_coefficient
  if (!changed) return
  draft.setup_time_min = setup
  draft.operation_time_min = optime
  await ops.updateOp(op.id, part.value.id, {
    setup_time_min: setup,
    operation_time_min: optime,
    work_center_id: draft.work_center_id ?? undefined,
    machine_utilization_coefficient: draft.ke,
    manning_coefficient: draft.ko,
    version: op.version,
  })
}

async function onWcSelect(op: Operation, id: number | null) {
  const dr = drafts[op.id]
  if (dr) dr.work_center_id = id
  await saveOp(op)
}

function onEscape(e: KeyboardEvent, op: Operation) {
  e.preventDefault()
  resetDraft(op)
  ;(e.target as HTMLElement).blur()
}

function onTimeInput(e: Event, opId: number, field: 'setup_time_min' | 'operation_time_min') {
  const val = (e.target as HTMLInputElement).value
  const n = parseFloat(val)
  const dr = drafts[opId]
  if (dr) dr[field] = isNaN(n) ? null : n
}

function onCoefInput(e: Event, opId: number, field: 'ke' | 'ko') {
  const val = (e.target as HTMLInputElement).value
  const n = parseFloat(val)
  const dr = drafts[opId]
  if (dr) dr[field] = isNaN(n) ? 100 : n
}

function keTime(draft: OpDraft): number {
  const strojni = draft.operation_time_min ?? 0
  return draft.ke > 0 ? strojni / (draft.ke / 100) : 0
}

function koTime(draft: OpDraft): number {
  return keTime(draft) * (draft.ko / 100)
}

function fmtHint(n: number): string {
  return Math.round(n).toLocaleString('cs')
}

const totalSetup = computed(() =>
  operations.value.reduce((s, o) => s + (drafts[o.id]?.setup_time_min ?? o.setup_time_min), 0),
)

const totalStrojni = computed(() =>
  operations.value.reduce(
    (s, o) => s + (drafts[o.id]?.operation_time_min ?? o.operation_time_min),
    0,
  ),
)

const totalKe = computed(() =>
  operations.value.reduce((s, o) => {
    const dr = drafts[o.id]
    return dr ? s + keTime(dr) : s
  }, 0),
)

const totalKo = computed(() =>
  operations.value.reduce((s, o) => {
    const dr = drafts[o.id]
    return dr ? s + koTime(dr) : s
  }, 0),
)

function toggleDetail(opId: number) {
  const s = new Set(openDetails.value)
  if (s.has(opId)) s.delete(opId)
  else s.add(opId)
  openDetails.value = s
}

function onFocusRow(opId: number) {
  activeOpId.value = opId
}

async function deleteOp(opId: number) {
  const op = operations.value.find((o) => o.id === opId)
  if (!op || !part.value) return
  const confirmed = await dialog.confirm({
    title: 'Smazat operaci',
    message: `Opravdu smazat operaci č. ${op.seq}?`,
    confirmLabel: 'Smazat',
    dangerous: true,
  })
  if (confirmed) {
    await ops.removeOp(op.id, part.value.id)
    if (activeOpId.value === opId) activeOpId.value = null
    const s = new Set(openDetails.value)
    s.delete(opId)
    openDetails.value = s
    delete drafts[opId]
  }
}

async function addOp() {
  if (!part.value) return
  const maxSeq = operations.value.length > 0 ? Math.max(...operations.value.map((o) => o.seq)) : 0
  const newOp = await ops.createOp({
    part_id: part.value.id,
    seq: maxSeq + 10,
    manning_coefficient: 100,
    machine_utilization_coefficient: 100,
  })
  if (newOp) {
    await nextTick()
    wcComboRefs.value[newOp.id]?.focus()
  }
}

async function onEnterLastField(op: Operation) {
  await saveOp(op)
  await addOp()
}

function handleCtrlD() {
  if (activeOpId.value != null) deleteOp(activeOpId.value)
}

function focusOptime(opId: number) {
  optimeRefs.value[opId]?.focus()
}

function focusKe(opId: number) {
  keRefs.value[opId]?.focus()
}

function focusKo(opId: number) {
  koRefs.value[opId]?.focus()
}

watch(operations, (list) => list.forEach(initDraft), { immediate: true })

watch(
  part,
  (p) => {
    if (p && !ops.byPartId[p.id]) ops.fetchByPartId(p.id)
  },
  { immediate: true },
)

onMounted(async () => {
  try {
    workCenters.value = (await wcApi.getAll()).filter((w) => w.is_active)
  } catch {
    // WC seznam je volitelný
  }
})
</script>

<template>
  <div class="wops">
    <div v-if="!typeGuard.isSupported(props.ctx)" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Nedostupné pro {{ typeGuard.focusedTypeName(props.ctx) }}</span>
    </div>

    <div v-else-if="!part" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Vyberte díl ze seznamu</span>
    </div>

    <div v-else-if="ops.loading && !operations.length" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <div v-else-if="!operations.length" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Díl nemá žádné operace</span>
    </div>

    <template v-else>

      <!-- Shortcut bar -->
      <div class="sc-bar">
        <span class="kbd">Tab</span><span class="sc-l">= další pole</span>
        <div class="sc-div" />
        <span class="kbd">↓</span><span class="sc-l">= dropdown WC</span>
        <div class="sc-div" />
        <span class="kbd">↵</span><span class="sc-l">= uloží + nový řádek</span>
        <div class="sc-div" />
        <span class="kbd">Ctrl+D</span><span class="sc-l">= smazat řádek</span>
        <div class="sc-div" />
        <span class="kbd">▶</span><span class="sc-l">= detail</span>
        <div class="sc-div" />
        <span class="kbd">Esc</span><span class="sc-l">= zahodit</span>
      </div>

      <!-- Tabulka -->
      <div class="tbl-wrap" @keydown.ctrl.d.prevent="handleCtrlD">
        <table class="ops">
          <thead>
            <tr>
              <th style="width: 22px" />
              <th style="width: 28px">#</th>
              <th style="width: 160px">Pracoviště</th>
              <th class="r" style="width: 80px">Seřízení</th>
              <th class="r" style="width: 84px">Strojní čas</th>
              <th class="r" style="width: 96px">Ke % <span class="th-sub">· čas stroje</span></th>
              <th class="r" style="width: 96px">Ko % <span class="th-sub">· obsluha</span></th>
              <th style="width: 26px" />
            </tr>
          </thead>
          <tbody>
            <template v-for="op in operations" :key="op.id">

              <tr
                class="op-row"
                :class="{ act: activeOpId === op.id }"
                :data-testid="`op-row-${op.id}`"
                @focusin="onFocusRow(op.id)"
              >
                <td class="seq-cell td-icon">
                  <button
                    class="chev"
                    :class="{ open: openDetails.has(op.id) }"
                    :data-testid="`op-chev-${op.id}`"
                    tabindex="-1"
                    @click.stop="toggleDetail(op.id)"
                  >▶</button>
                </td>

                <td><span class="seq-num">{{ String(op.seq).padStart(2, '0') }}</span></td>

                <td>
                  <WcCombobox
                    :ref="(el) => { if (el) wcComboRefs[op.id] = el as unknown as { focus: () => void } }"
                    :modelValue="d(op.id).work_center_id"
                    :options="workCenters"
                    :data-testid="`op-wc-${op.id}`"
                    @update:modelValue="onWcSelect(op, $event)"
                  />
                </td>

                <td class="r">
                  <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
                  <input
                    v-select-on-focus
                    class="inp num"
                    type="number"
                    step="1"
                    min="0"
                    :value="d(op.id).setup_time_min ?? ''"
                    placeholder="0"
                    :data-testid="`op-setup-${op.id}`"
                    @input="onTimeInput($event, op.id, 'setup_time_min')"
                    @blur="saveOp(op)"
                    @keydown.enter.prevent="focusOptime(op.id)"
                    @keydown.escape="onEscape($event, op)"
                  />
                </td>

                <td class="r">
                  <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
                  <input
                    :ref="(el) => { if (el) optimeRefs[op.id] = el as HTMLInputElement }"
                    v-select-on-focus
                    class="inp num"
                    type="number"
                    step="1"
                    min="0"
                    :value="d(op.id).operation_time_min ?? ''"
                    placeholder="0"
                    :data-testid="`op-optime-${op.id}`"
                    @input="onTimeInput($event, op.id, 'operation_time_min')"
                    @blur="saveOp(op)"
                    @keydown.enter.prevent="focusKe(op.id)"
                    @keydown.escape="onEscape($event, op)"
                  />
                </td>

                <td class="r">
                  <div class="coef-cell">
                    <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
                    <input
                      :ref="(el) => { if (el) keRefs[op.id] = el as HTMLInputElement }"
                      v-select-on-focus
                      class="inp num inp-coef"
                      type="number"
                      step="1"
                      min="0"
                      max="200"
                      :value="d(op.id).ke"
                      :data-testid="`op-ke-${op.id}`"
                      @input="onCoefInput($event, op.id, 'ke')"
                      @blur="saveOp(op)"
                      @keydown.enter.prevent="focusKo(op.id)"
                      @keydown.escape="onEscape($event, op)"
                    />
                    <span class="coef-hint ke-hint">{{ fmtHint(keTime(d(op.id))) }}</span>
                  </div>
                </td>

                <td class="r">
                  <div class="coef-cell">
                    <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
                    <input
                      :ref="(el) => { if (el) koRefs[op.id] = el as HTMLInputElement }"
                      v-select-on-focus
                      class="inp num inp-coef"
                      type="number"
                      step="1"
                      min="0"
                      max="200"
                      :value="d(op.id).ko"
                      :data-testid="`op-ko-${op.id}`"
                      @input="onCoefInput($event, op.id, 'ko')"
                      @blur="saveOp(op)"
                      @keydown.enter.prevent="onEnterLastField(op)"
                      @keydown.escape="onEscape($event, op)"
                    />
                    <span class="coef-hint ko-hint">{{ fmtHint(koTime(d(op.id))) }}</span>
                  </div>
                </td>

                <td class="td-icon">
                  <button
                    class="del-btn"
                    :data-testid="`op-del-${op.id}`"
                    title="Smazat (Ctrl+D)"
                    tabindex="-1"
                    @click="deleteOp(op.id)"
                  >×</button>
                </td>
              </tr>

              <!-- Collapsible detail -->
              <tr v-show="openDetails.has(op.id)" class="detail-tr">
                <td colspan="8">
                  <div class="detail-inner">
                    <div class="detail-section">
                      <div class="ds-head">Navázaný materiál</div>
                      <div class="ds-placeholder">Připravujeme…</div>
                    </div>
                    <div class="detail-section">
                      <div class="ds-head">Nástroje</div>
                      <div class="ds-placeholder">Připravujeme…</div>
                    </div>
                    <div class="detail-section">
                      <div class="ds-head">Řezné podmínky</div>
                      <div class="ds-placeholder">Připravujeme…</div>
                    </div>
                    <div class="detail-section">
                      <div class="ds-head">Kroky operace</div>
                      <div class="ds-placeholder">Připravujeme…</div>
                    </div>
                  </div>
                </td>
              </tr>

            </template>

            <tr class="add-tr">
              <td colspan="8">
                <button class="add-btn" data-testid="op-add-btn" @click="addOp">
                  <span class="add-plus">+</span>
                  Přidat operaci
                  <span class="kbd add-hint">↵ z posledního pole</span>
                </button>
              </td>
            </tr>

          </tbody>
        </table>
      </div>

      <!-- Summary bar — DOLE -->
      <div class="sum-bar">
        <div class="sum-kpi">
          <span class="sum-label">Σ Seřízení</span>
          <div><span class="sum-val">{{ Math.round(totalSetup) }}</span><span class="sum-unit">min</span></div>
        </div>
        <div class="sum-kpi">
          <span class="sum-label">Σ Strojní čas</span>
          <div><span class="sum-val">{{ Math.round(totalStrojni) }}</span><span class="sum-unit">min</span></div>
        </div>
        <div class="sum-kpi">
          <span class="sum-label">Σ Čas stroje</span>
          <div><span class="sum-val">{{ Math.round(totalKe) }}</span><span class="sum-unit">min</span></div>
          <span class="sum-formula sum-formula-ke">Σ (strojní ÷ Ke)</span>
        </div>
        <div class="sum-kpi">
          <span class="sum-label">Σ Čas obsluhy</span>
          <div><span class="sum-val">{{ Math.round(totalKo) }}</span><span class="sum-unit">min</span></div>
          <span class="sum-formula sum-formula-ko">Σ (čas stroje × Ko)</span>
        </div>
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
  padding: 6px var(--pad) var(--pad);
  gap: 6px;
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
.mod-label { font-size: var(--fsm); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

/* ─── Shortcut bar ─── */
.sc-bar {
  display: flex;
  align-items: center;
  gap: 7px;
  flex-wrap: wrap;
  padding: 5px 10px;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  flex-shrink: 0;
}
.kbd {
  display: inline-flex;
  align-items: center;
  padding: 1px 5px;
  background: var(--raised);
  border: 1px solid var(--b3);
  border-radius: var(--rs);
  font-size: var(--fss);
  color: var(--t4);
  font-family: var(--font);
  line-height: 1.5;
  white-space: nowrap;
}
.sc-l { font-size: var(--fss); color: var(--t4); }
.sc-div { width: 1px; height: 10px; background: var(--b2); flex-shrink: 0; }

/* ─── Table wrapper ─── */
.tbl-wrap {
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  overflow: visible;
  flex: 1;
  min-height: 0;
}

/* ─── Table ─── */
.ops { width: 100%; border-collapse: collapse; }
.ops thead { background: rgba(255, 255, 255, 0.02); }
.ops th {
  padding: 5px 8px;
  font-family: var(--font);
  font-size: var(--fsm);
  font-weight: 400;
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  text-align: left;
  border-bottom: 1px solid var(--b2);
  white-space: nowrap;
}
.ops th.r { text-align: right; }
.th-sub { font-size: var(--fss); color: var(--t4); margin-left: 3px; letter-spacing: 0; }

/* ─── Op row ─── */
.op-row {
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  transition: background 60ms var(--ease);
}
.op-row:hover { background: rgba(255, 255, 255, 0.025); }
.op-row.act { background: rgba(255, 255, 255, 0.035); }
.op-row.act .seq-cell { box-shadow: inset 3px 0 0 var(--red); }
.op-row td {
  padding: 4px 8px;
  font-size: var(--fs);
  color: var(--t2);
  vertical-align: middle;
  border: none;
}
.op-row td.r { text-align: right; }
.op-row td.td-icon { padding: 0 4px; text-align: center; }
.op-row:hover .del-btn,
.op-row.act .del-btn { opacity: 1; }

/* ─── Seq ─── */
.seq-num {
  font-family: var(--font);
  font-size: var(--fsm);
  color: var(--t4);
  letter-spacing: 0.04em;
  font-variant-numeric: tabular-nums;
}
.op-row.act .seq-num { color: var(--red); }

/* ─── Chevron ─── */
.chev {
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: var(--fss);
  color: var(--t4);
  background: none;
  border: none;
  border-radius: var(--rs);
  cursor: pointer;
  padding: 0;
  transition: color 80ms var(--ease), background 80ms var(--ease), transform 120ms var(--ease);
}
.chev:hover { background: var(--b2); color: var(--t3); }
.chev.open { transform: rotate(90deg); color: var(--t3); }

/* ─── Inputs ─── */
.inp {
  background: var(--b1);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t2);
  font-family: var(--font);
  font-size: var(--fs);
  padding: 3px 6px;
  outline: none;
  width: 100%;
  transition: border-color 80ms var(--ease), background 80ms var(--ease), color 80ms var(--ease);
}
.inp::placeholder { color: var(--t4); font-size: var(--fss); }
.inp:focus { border-color: var(--b3); background: rgba(255, 255, 255, 0.08); color: var(--t1); }
.inp:focus-visible { outline: 2px solid rgba(255, 255, 255, 0.5); outline-offset: 2px; }
.inp.num { text-align: right; width: 52px; font-variant-numeric: tabular-nums; }
.inp.inp-coef { width: 42px; }
.inp[type='number']::-webkit-outer-spin-button,
.inp[type='number']::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.inp[type='number'] { -moz-appearance: textfield; }
input::selection { background: transparent; }

/* ─── Ke / Ko ─── */
.coef-cell { display: flex; align-items: center; justify-content: flex-end; gap: 5px; }
.coef-hint {
  font-family: var(--font);
  font-size: var(--fsm);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  min-width: 28px;
  text-align: right;
}
.ke-hint { color: var(--chart-material); }
.ko-hint { color: var(--chart-machining); }

/* ─── Delete ─── */
.del-btn {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: 1px solid transparent;
  border-radius: var(--rs);
  color: var(--t4);
  cursor: pointer;
  font-size: var(--fs);
  line-height: 1;
  opacity: 0;
  padding: 0;
  transition: opacity 70ms var(--ease), background 70ms var(--ease),
    color 70ms var(--ease), border-color 70ms var(--ease);
}
.del-btn:hover {
  color: var(--err);
  background: rgba(248, 113, 113, 0.1);
  border-color: rgba(248, 113, 113, 0.25);
}

/* ─── Add row ─── */
.add-tr td { padding: 0; border-top: 1px dashed rgba(255, 255, 255, 0.06); }
.add-btn {
  width: 100%;
  padding: 6px 12px;
  background: none;
  border: none;
  color: var(--t4);
  font-family: var(--font);
  font-size: var(--fsm);
  font-weight: 600;
  cursor: pointer;
  text-align: left;
  letter-spacing: 0.03em;
  display: flex;
  align-items: center;
  gap: 7px;
  transition: background 80ms var(--ease), color 80ms var(--ease);
}
.add-btn:hover { background: var(--b1); color: var(--t2); }
.add-plus { font-size: var(--fs); line-height: 1; color: var(--t3); }
.add-hint { margin-left: auto; }

/* ─── Detail ─── */
.detail-tr { border-bottom: 1px solid rgba(255, 255, 255, 0.04); }
.ops tbody .detail-tr td { padding: 0; background: var(--raised); }
.detail-inner {
  padding: 12px 10px 14px 50px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.ds-head {
  font-family: var(--font);
  font-size: var(--fsm);
  font-weight: 400;
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--b2);
}
.ds-placeholder { font-size: var(--fsm); color: var(--t4); font-style: italic; }

/* ─── Summary bar ─── */
.sum-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--b2);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  overflow: hidden;
  flex-shrink: 0;
}
.sum-kpi {
  background: var(--raised);
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.sum-label {
  font-size: var(--fsm);
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  font-weight: 600;
}
.sum-val {
  font-family: var(--font);
  font-size: var(--fsh);
  color: var(--t1);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
.sum-unit { font-size: var(--fss); color: var(--t4); margin-left: 3px; }
.sum-formula { font-size: var(--fss); font-family: var(--font); margin-top: 1px; }
.sum-formula-ke { color: rgba(96, 165, 250, 0.55); }
.sum-formula-ko { color: rgba(167, 139, 250, 0.5); }
</style>
