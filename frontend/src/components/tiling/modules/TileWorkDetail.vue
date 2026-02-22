<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useOperationsStore } from '@/stores/operations'
import { useWorkspaceStore } from '@/stores/workspace'
import type { ContextGroup, ModuleId } from '@/types/workspace'
import type { Operation, CuttingMode } from '@/types/operation'
import type { WorkCenter } from '@/types/work-center'
import { formatMinSec } from '@/utils/formatters'
import * as wcApi from '@/api/work-centers'
import Spinner from '@/components/ui/Spinner.vue'
import TileWorkMaterials from './TileWorkMaterials.vue'
import TileWorkPricing from './TileWorkPricing.vue'
import TileWorkDrawing from './TileWorkDrawing.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()
const ops = useOperationsStore()
const ws = useWorkspaceStore()

const part = computed(() => parts.getFocusedPart(props.ctx))

// ─── Tabs ───
type Tab = 'ops' | 'pricing' | 'materials' | 'drawing'
const activeTab = ref<Tab>('ops')

const TAB_MODULE: Record<Tab, ModuleId> = {
  ops: 'work-ops',
  pricing: 'work-pricing',
  materials: 'work-materials',
  drawing: 'work-drawing',
}

function onTabDragStart(e: DragEvent, tab: Tab) {
  const moduleId = TAB_MODULE[tab]
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', moduleId)
  }
  setTimeout(() => ws.startDrag(null, moduleId, props.ctx), 0)
}
function onTabDragEnd() { ws.endDrag() }

// ─── Operations — local copy kept alive during refetch to avoid flash ───
const displayedOps = ref<Operation[]>([])
const loadingOps = ref(false)
const isRefetching = computed(() => loadingOps.value && displayedOps.value.length > 0)

const totalSetup = computed(() => displayedOps.value.reduce((s, o) => s + o.setup_time_min, 0))
const totalOp = computed(() => displayedOps.value.reduce((s, o) => s + o.operation_time_min, 0))

function cuttingLabel(mode: string): string {
  if (mode === 'low') return 'LOW'
  if (mode === 'high') return 'HIGH'
  return 'MID'
}

// ─── Status / source badge dots ───
function statusDot(status: string): string {
  if (status === 'active') return 'ok'
  if (status === 'draft') return 'w'
  if (status === 'archived') return 'e'
  return 'o'
}
function sourceDot(source: string): string {
  if (source === 'infor_import') return 'o'
  if (source === 'quote_request') return 'w'
  return 'o'
}
function statusLabel(status: string): string {
  if (status === 'active') return 'Aktivní'
  if (status === 'draft') return 'Rozpr.'
  if (status === 'archived') return 'Arch.'
  return 'Nabídka'
}
function sourceLabel(source: string): string {
  if (source === 'infor_import') return 'Infor'
  if (source === 'quote_request') return 'Nabídka'
  return 'Manuální'
}

// Fetch operations when part changes — keep stale data to avoid flash
watch(
  part,
  async (p) => {
    if (!p) { displayedOps.value = []; cancelEdit(); return }
    if (ops.byPartId[p.id] !== undefined) {
      displayedOps.value = ops.forPart(p.id)
      return
    }
    loadingOps.value = true
    await ops.fetchByPartId(p.id)
    displayedOps.value = ops.forPart(p.id)
    loadingOps.value = false
  },
  { immediate: true },
)
// Live updates when ops are modified (add/delete/edit)
watch(
  () => part.value ? ops.forPart(part.value.id) : [],
  (fresh) => { if (!loadingOps.value) displayedOps.value = fresh },
)

// ─── Work Centers — fetch once, cache locally ───
const workCenters = ref<WorkCenter[]>([])
onMounted(async () => {
  try {
    workCenters.value = await wcApi.getAll()
  } catch {
    // non-critical — typeahead just won't have data
  }
})

// ─── Inline editing ───
interface EditDraft {
  seq: number
  work_center_id: number | null
  work_center_name: string | null
  setup_time_min: number
  operation_time_min: number
  cutting_mode: CuttingMode
  is_coop: boolean
  version: number
}

const editingOpId = ref<number | null>(null)
const editDraft = ref<EditDraft | null>(null)
const saving = ref(false)

// WC typeahead state
const wcQuery = ref('')
const wcOpen = ref(false)
const wcHiIdx = ref(0)

const filteredWcs = computed(() => {
  const q = wcQuery.value.trim().toLowerCase()
  if (!q) return workCenters.value.slice(0, 20)
  return workCenters.value.filter(wc =>
    wc.name.toLowerCase().includes(q) || wc.work_center_number.includes(q)
  ).slice(0, 20)
})

type EditField = 'seq' | 'wc' | 'setup' | 'optime'

const FIELD_SELECTOR: Record<EditField, string> = {
  seq:    '.op-editing [data-testid="edit-seq"]',
  wc:     '.op-editing [data-testid="edit-wc"]',
  setup:  '.op-editing [data-testid="edit-setup"]',
  optime: '.op-editing [data-testid="edit-optime"]',
}

async function startEdit(op: Operation, field: EditField = 'wc') {
  if (editingOpId.value !== op.id) {
    if (editingOpId.value !== null) saveEdit()
    editingOpId.value = op.id
    editDraft.value = {
      seq: op.seq,
      work_center_id: op.work_center_id,
      work_center_name: op.work_center_name,
      setup_time_min: op.setup_time_min,
      operation_time_min: op.operation_time_min,
      cutting_mode: op.cutting_mode,
      is_coop: op.is_coop,
      version: op.version,
    }
    wcQuery.value = op.work_center_name ?? ''
    wcOpen.value = false
    wcHiIdx.value = 0
  }
  await nextTick()
  focusField(field)
}

function parseNum(e: Event): number {
  const raw = (e.target as HTMLInputElement).value.replace(',', '.')
  const n = parseFloat(raw)
  return isNaN(n) ? 0 : n
}

function focusField(field: EditField) {
  const el = document.querySelector<HTMLInputElement>(FIELD_SELECTOR[field])
  if (!el) return
  el.focus()
  el.select()
}

function cancelEdit() {
  editingOpId.value = null
  editDraft.value = null
  wcOpen.value = false
}

async function saveEdit() {
  if (!editDraft.value || editingOpId.value === null || !part.value) return
  const opId = editingOpId.value
  const draft = editDraft.value
  editingOpId.value = null
  editDraft.value = null
  wcOpen.value = false
  saving.value = true
  await ops.updateOp(opId, part.value.id, {
    seq: draft.seq,
    work_center_id: draft.work_center_id ?? undefined,
    setup_time_min: draft.setup_time_min,
    operation_time_min: draft.operation_time_min,
    cutting_mode: draft.cutting_mode,
    is_coop: draft.is_coop,
    version: draft.version,
  })
  saving.value = false
}

function onRowKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') { e.preventDefault(); saveEdit() }
  if (e.key === 'Escape') { e.preventDefault(); cancelEdit() }
}

// Cutting mode / coop cycling
function cycleCutting(e: MouseEvent) {
  e.stopPropagation()
  if (!editDraft.value) return
  const d = editDraft.value
  if (d.is_coop) { d.is_coop = false; d.cutting_mode = 'low'; return }
  if (d.cutting_mode === 'low') { d.cutting_mode = 'mid'; return }
  if (d.cutting_mode === 'mid') { d.cutting_mode = 'high'; return }
  d.is_coop = true
}

// ─── WC typeahead handlers ───
function onWcFocus() {
  wcOpen.value = true
  wcHiIdx.value = 0
}
function onWcInput() {
  wcOpen.value = true
  wcHiIdx.value = 0
}
function onWcKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    wcHiIdx.value = Math.min(wcHiIdx.value + 1, filteredWcs.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    wcHiIdx.value = Math.max(wcHiIdx.value - 1, 0)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    e.stopPropagation()
    const hit = filteredWcs.value[wcHiIdx.value]
    if (wcOpen.value && hit) {
      selectWc(hit)
    } else {
      saveEdit()
    }
  } else if (e.key === 'Escape') {
    e.preventDefault()
    e.stopPropagation()
    wcOpen.value = false
    cancelEdit()
  } else if (e.key === 'Tab') {
    const hit = filteredWcs.value[wcHiIdx.value]
    if (wcOpen.value && hit) {
      selectWc(hit)
    }
    wcOpen.value = false
  }
}
function selectWc(wc: WorkCenter) {
  if (!editDraft.value) return
  editDraft.value.work_center_id = wc.id
  editDraft.value.work_center_name = wc.name
  wcQuery.value = wc.name
  wcOpen.value = false
}
function clearWc() {
  if (!editDraft.value) return
  editDraft.value.work_center_id = null
  editDraft.value.work_center_name = null
  wcQuery.value = ''
  nextTick(() => focusField('wc'))
}
function onWcBlur() {
  // small delay so mousedown on option fires first
  setTimeout(() => { wcOpen.value = false }, 120)
}
</script>

<template>
  <div :class="['wdet', { refetching: isRefetching }]">
    <!-- ── Empty state ── -->
    <div v-if="!part" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Vyberte díl ze seznamu</span>
      <span class="mod-hint">Klikněte na díl v panelu Díly</span>
    </div>

    <!-- ── Part loaded ── -->
    <template v-else>

      <!-- Compact info bar -->
      <div class="det-bar">
        <span class="det-pn">{{ part.part_number }}</span>
        <span class="det-nm">{{ part.name || part.article_number || '—' }}</span>
        <div class="det-bgs">
          <span class="bdg">
            <span :class="['dot', statusDot(part.status)]" />
            {{ statusLabel(part.status) }}
          </span>
          <span v-if="part.source !== 'manual'" class="bdg">
            <span :class="['dot', sourceDot(part.source)]" />
            {{ sourceLabel(part.source) }}
          </span>
        </div>
      </div>

      <!-- Fields ribbon -->
      <div class="rib">
        <div class="rib-r">
          <div v-if="part.article_number" class="rib-i">
            <span class="rib-l">Artikl</span>
            <span class="rib-v m">{{ part.article_number }}</span>
          </div>
          <div v-if="part.drawing_number" class="rib-i">
            <span class="rib-l">Výkres</span>
            <span class="rib-v m">{{ part.drawing_number }}</span>
          </div>
          <div v-if="part.revision" class="rib-i">
            <span class="rib-l">Rev.</span>
            <span class="rib-v m">{{ part.revision }}</span>
          </div>
          <div v-if="part.customer_revision" class="rib-i">
            <span class="rib-l">Rev. zák.</span>
            <span class="rib-v m">{{ part.customer_revision }}</span>
          </div>
          <div v-if="displayedOps.length" class="rib-i">
            <span class="rib-l">Ops</span>
            <span class="rib-v m">{{ displayedOps.length }}</span>
          </div>
        </div>
      </div>

      <!-- Tab strip -->
      <div class="ptabs">
        <button
          :class="['ptab', activeTab === 'ops' ? 'on' : '']"
          draggable="true"
          @click="activeTab = 'ops'"
          @dragstart="onTabDragStart($event, 'ops')"
          @dragend="onTabDragEnd"
        >
          Operace
          <span v-if="displayedOps.length" class="n">{{ displayedOps.length }}</span>
        </button>
        <button
          :class="['ptab', activeTab === 'pricing' ? 'on' : '']"
          draggable="true"
          @click="activeTab = 'pricing'"
          @dragstart="onTabDragStart($event, 'pricing')"
          @dragend="onTabDragEnd"
        >Kalkulace</button>
        <button
          :class="['ptab', activeTab === 'materials' ? 'on' : '']"
          draggable="true"
          @click="activeTab = 'materials'"
          @dragstart="onTabDragStart($event, 'materials')"
          @dragend="onTabDragEnd"
        >Materiály</button>
        <button
          :class="['ptab', activeTab === 'drawing' ? 'on' : '']"
          draggable="true"
          @click="activeTab = 'drawing'"
          @dragstart="onTabDragStart($event, 'drawing')"
          @dragend="onTabDragEnd"
        >Výkres</button>
      </div>

      <!-- ── Tab: Operace ── -->
      <div v-if="activeTab === 'ops'" class="tab-body">
        <!-- Loading -->
        <div v-if="loadingOps && !displayedOps.length" class="tab-state">
          <Spinner size="sm" />
        </div>
        <!-- Empty -->
        <div v-else-if="!displayedOps.length" class="tab-state">
          <div class="mod-dot" />
          <span class="mod-label">Žádné operace</span>
        </div>
        <!-- Summary + table -->
        <template v-else>
          <div class="rib rib-sep">
            <div class="rib-r">
              <div class="rib-i">
                <span class="rib-l">Seřízení</span>
                <span class="rib-v m">{{ formatMinSec(totalSetup) }}</span>
              </div>
              <div class="rib-i">
                <span class="rib-l">Výroba</span>
                <span class="rib-v m">{{ formatMinSec(totalOp) }}</span>
              </div>
            </div>
          </div>
          <table class="ot">
            <thead>
              <tr>
                <th style="width:28px">#</th>
                <th>Pracoviště</th>
                <th class="r" style="width:85px">Seřízení</th>
                <th class="r" style="width:85px">Výroba</th>
                <th class="r" style="width:36px">M</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="op in displayedOps"
                :key="op.id"
                :class="['op-row', { 'op-editing': editingOpId === op.id }]"
                :data-testid="`op-row-${op.id}`"
              >
                <!-- ── Edit mode ── -->
                <template v-if="editingOpId === op.id && editDraft">
                  <td @click.stop="focusField('seq')">
                    <input
                      class="ei ei-num"
                      type="text"
                      inputmode="numeric"
                      :value="editDraft.seq"
                      data-testid="edit-seq"
                      @change="editDraft.seq = parseNum($event)"
                      @keydown="onRowKeydown"
                    />
                  </td>
                  <td class="wc-td">
                    <div class="wc-wrap">
                      <input
                        class="ei ei-wc"
                        type="text"
                        :value="wcQuery"
                        placeholder="Filtruj pracoviště…"
                        autocomplete="off"
                        data-testid="edit-wc"
                        @input="wcQuery = ($event.target as HTMLInputElement).value; onWcInput()"
                        @focus="onWcFocus"
                        @blur="onWcBlur"
                        @keydown="onWcKeydown"
                      />
                      <button
                        v-if="editDraft.work_center_id"
                        class="wc-clr"
                        tabindex="-1"
                        @mousedown.prevent="clearWc"
                        title="Odebrat pracoviště"
                      >×</button>
                      <!-- Dropdown -->
                      <div v-if="wcOpen && filteredWcs.length" class="wc-drop">
                        <div
                          v-for="(wc, i) in filteredWcs"
                          :key="wc.id"
                          :class="['wc-opt', { hi: i === wcHiIdx }]"
                          @mousedown.prevent="selectWc(wc)"
                        >
                          <span class="wc-num">{{ wc.work_center_number }}</span>
                          <span class="wc-nm">{{ wc.name }}</span>
                        </div>
                      </div>
                    </div>
                  </td>
                  <td class="r" @click.stop="focusField('setup')">
                    <input
                      class="ei ei-num r"
                      type="text"
                      inputmode="decimal"
                      :value="editDraft.setup_time_min"
                      data-testid="edit-setup"
                      @change="editDraft.setup_time_min = parseNum($event)"
                      @keydown="onRowKeydown"
                    />
                  </td>
                  <td class="r" @click.stop="focusField('optime')">
                    <input
                      class="ei ei-num r"
                      type="text"
                      inputmode="decimal"
                      :value="editDraft.operation_time_min"
                      data-testid="edit-optime"
                      @change="editDraft.operation_time_min = parseNum($event)"
                      @keydown="onRowKeydown"
                    />
                  </td>
                  <td class="r" @click.stop="cycleCutting">
                    <span v-if="editDraft.is_coop" class="cm-badge coop" title="Klikni pro změnu">CO</span>
                    <span v-else :class="['cm-badge', `cm-${editDraft.cutting_mode}`]" title="Klikni pro změnu">
                      {{ cuttingLabel(editDraft.cutting_mode) }}
                    </span>
                  </td>
                </template>

                <!-- ── Display mode ── -->
                <template v-else>
                  <td class="mono t4" @click="startEdit(op, 'seq')">{{ op.seq }}</td>
                  <td class="wc-cell" @click="startEdit(op, 'wc')">{{ op.work_center_name || '—' }}</td>
                  <td class="r" @click="startEdit(op, 'setup')">
                    <span class="tb s"><span class="d" />{{ formatMinSec(op.setup_time_min) }}</span>
                  </td>
                  <td class="r" @click="startEdit(op, 'optime')">
                    <span class="tb o"><span class="d" />{{ formatMinSec(op.operation_time_min) }}</span>
                  </td>
                  <td class="r" @click="startEdit(op, 'wc')">
                    <span v-if="op.is_coop" class="cm-badge coop">CO</span>
                    <span v-else :class="['cm-badge', `cm-${op.cutting_mode}`]">{{ cuttingLabel(op.cutting_mode) }}</span>
                  </td>
                </template>
              </tr>
            </tbody>
          </table>
          <!-- Edit hint -->
          <div v-if="editingOpId !== null" class="edit-hint">
            <span>Enter uloží · Esc zruší</span>
          </div>
        </template>
      </div>

      <!-- ── Tab: Kalkulace ── -->
      <TileWorkPricing v-else-if="activeTab === 'pricing'" :leaf-id="leafId" :ctx="ctx" class="tab-body" />

      <!-- ── Tab: Materiály ── -->
      <TileWorkMaterials v-else-if="activeTab === 'materials'" :leaf-id="leafId" :ctx="ctx" class="tab-body" />

      <!-- ── Tab: Výkres ── -->
      <TileWorkDrawing v-else-if="activeTab === 'drawing'" :leaf-id="leafId" :ctx="ctx" class="tab-body" />

    </template>
  </div>
</template>

<style scoped>
.wdet {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  transition: opacity 0.15s;
}
.wdet.refetching { opacity: 0.4; }

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
.mod-hint { font-size: 10px; opacity: 0.6; }

/* ─── Compact info bar ─── */
.det-bar {
  height: 30px;
  padding: 0 var(--pad);
  border-bottom: 1px solid var(--b1);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  overflow: hidden;
}
.det-pn { font-family: var(--mono); font-size: 12px; font-weight: 600; color: var(--t1); flex-shrink: 0; letter-spacing: 0.02em; }
.det-nm { font-size: var(--fs); color: var(--t3); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.det-bgs { display: flex; gap: 3px; flex-shrink: 0; }

/* ─── Badge ─── */
.bdg { display: inline-flex; align-items: center; gap: 3px; padding: 1px 5px; font-size: 10px; font-weight: 500; border-radius: 99px; background: var(--b1); color: var(--t2); }
.bdg .dot { width: 4px; height: 4px; border-radius: 50%; flex-shrink: 0; }
.dot.ok { background: var(--ok); }
.dot.w  { background: var(--warn); }
.dot.e  { background: var(--err); }
.dot.o  { background: var(--t4); }

/* ─── Ribbon ─── */
.rib { padding: 4px var(--pad); background: rgba(255,255,255,0.02); border-bottom: 1px solid var(--b1); flex-shrink: 0; }
.rib-sep { border-top: 1px solid var(--b1); }
.rib-r { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.rib-i { display: flex; align-items: baseline; gap: 4px; }
.rib-l { font-size: 10px; color: var(--t4); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 500; }
.rib-v { font-size: var(--fs); color: var(--t1); font-weight: 500; }
.rib-v.m { font-family: var(--mono); }

/* ─── Tab strip ─── */
.ptabs { display: flex; gap: 1px; padding: 3px var(--pad); border-bottom: 1px solid var(--b2); flex-shrink: 0; background: rgba(255,255,255,0.015); }
.ptab { padding: 3px 7px; font-size: 10.5px; font-weight: 500; color: var(--t4); background: transparent; border: none; border-radius: var(--rs); cursor: pointer; font-family: var(--font); display: flex; align-items: center; gap: 3px; }
.ptab:hover { color: var(--t3); }
.ptab.on { color: var(--t1); background: var(--b1); }
.ptab[draggable="true"] { cursor: grab; }
.ptab[draggable="true"]:active { cursor: grabbing; }
.n { font-family: var(--mono); font-size: 10px; color: var(--t4); padding: 1px 4px; background: var(--b1); border-radius: 2px; }

/* ─── Tab body ─── */
.tab-body { flex: 1; overflow-y: auto; overflow-x: hidden; min-height: 0; display: flex; flex-direction: column; }
.tab-state { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; color: var(--t4); }
.tab-placeholder { align-items: center; justify-content: center; gap: 8px; color: var(--t4); }

/* ─── Operations table ─── */
.ot { width: 100%; border-collapse: collapse; }
.ot thead { background: rgba(255,255,255,0.025); position: sticky; top: 0; z-index: 2; }
.ot th { padding: 4px var(--pad); font-size: 10px; font-weight: 600; color: var(--t4); text-transform: uppercase; letter-spacing: 0.04em; text-align: left; border-bottom: 1px solid var(--b2); white-space: nowrap; }
.ot th.r { text-align: right; }
.ot td { padding: 2px var(--pad); font-size: var(--fs); color: var(--t2); border-bottom: 1px solid rgba(255,255,255,0.025); }
.ot td.r { text-align: right; }
.ot tbody tr:hover td { background: var(--b1); cursor: pointer; }
.mono { font-family: var(--mono); }
.t4 { color: var(--t4); }
.wc-cell { font-family: var(--mono); font-size: 10px; color: var(--t3); }

/* ─── Editing row ─── */
.op-editing td { background: var(--raised) !important; border-bottom-color: var(--b3) !important; padding-top: 1px; padding-bottom: 1px; }
.op-editing:hover td { background: var(--raised) !important; }

/* ─── Inline edit inputs ─── */
.ei {
  background: var(--surface);
  border: 1px solid var(--b3);
  border-radius: var(--rs);
  color: var(--t1);
  font-family: var(--mono);
  font-size: 11px;
  padding: 2px 4px;
  outline: none;
  width: 100%;
  box-sizing: border-box;
}
.ei:focus { border-color: rgba(255,255,255,0.3); }
.ei-num { width: 48px; text-align: center; }
.ei-num.r { text-align: right; }
.ei-num { text-align: center; }
.ei-num.r { text-align: right; }
.ei::selection { background: transparent; }

/* ─── WC typeahead ─── */
.wc-td { position: relative; }
.wc-wrap { position: relative; display: flex; align-items: center; gap: 2px; }
.ei-wc { flex: 1; min-width: 0; font-family: var(--font); font-size: 11px; }
.wc-clr {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  background: none;
  border: none;
  color: var(--t4);
  cursor: pointer;
  font-size: 13px;
  line-height: 1;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.wc-clr:hover { color: var(--t1); }
.wc-drop {
  position: absolute;
  top: calc(100% + 2px);
  left: 0;
  right: 0;
  min-width: 200px;
  background: var(--raised);
  border: 1px solid var(--b3);
  border-radius: var(--rs);
  z-index: 100;
  max-height: 180px;
  overflow-y: auto;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
}
.wc-opt {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 4px 8px;
  cursor: pointer;
  font-size: var(--fs);
}
.wc-opt:hover, .wc-opt.hi { background: var(--b2); }
.wc-num { font-family: var(--mono); font-size: 10px; color: var(--t4); flex-shrink: 0; }
.wc-nm { color: var(--t1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ─── Edit hint ─── */
.edit-hint {
  padding: 3px var(--pad);
  font-size: 10px;
  color: var(--t4);
  border-top: 1px solid var(--b1);
  flex-shrink: 0;
  text-align: right;
}

/* ─── Time badge ─── */
.tb { display: inline-flex; align-items: center; gap: 3px; padding: 1px 5px; font-family: var(--mono); font-size: 10px; border-radius: 99px; background: var(--b1); color: var(--t2); white-space: nowrap; }
.tb .d { width: 3px; height: 3px; border-radius: 50%; flex-shrink: 0; }
.tb.s .d { background: var(--red); }
.tb.o .d { background: var(--ok); }

/* ─── Cutting mode badge ─── */
.cm-badge { font-family: var(--mono); font-size: 9px; font-weight: 600; letter-spacing: 0.06em; padding: 1px 4px; border-radius: var(--rs); }
.cm-low  { background: var(--b1); color: var(--t3); }
.cm-mid  { background: var(--b1); color: var(--t2); }
.cm-high { background: var(--red-10); color: var(--red); }
.coop   { background: var(--b1); color: var(--t3); }
.op-editing .cm-badge { cursor: pointer; }
.op-editing .cm-badge:hover { opacity: 0.75; }
</style>
