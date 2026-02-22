<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useOperationsStore } from '@/stores/operations'
import { useWorkspaceStore } from '@/stores/workspace'
import type { ContextGroup, ModuleId } from '@/types/workspace'
import { formatDuration } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'

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
  // Defer same as panel drag — ensures drop zones appear after drag gesture is captured
  setTimeout(() => ws.startDrag(null, moduleId), 0)
}

function onTabDragEnd() {
  ws.endDrag()
}

// ─── Operations ───
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

// Fetch operations when part changes
watch(
  part,
  (p) => {
    if (p && !ops.byPartId[p.id]) ops.fetchByPartId(p.id)
  },
  { immediate: true },
)
</script>

<template>
  <div class="wdet">
    <!-- ── Empty state ── -->
    <div v-if="!part" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Vyberte díl ze seznamu</span>
      <span class="mod-hint">Klikněte na díl v panelu Díly</span>
    </div>

    <!-- ── Part loaded ── -->
    <template v-else>

      <!-- Compact info bar — part number · name · badges on one line (v3 style) -->
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

      <!-- Fields ribbon — article · drawing · revisions · ops count -->
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
          <div v-if="operations.length" class="rib-i">
            <span class="rib-l">Ops</span>
            <span class="rib-v m">{{ operations.length }}</span>
          </div>
        </div>
      </div>

      <!-- Tab strip — tabs are draggable to spawn as standalone panels -->
      <div class="ptabs">
        <button
          :class="['ptab', activeTab === 'ops' ? 'on' : '']"
          draggable="true"
          @click="activeTab = 'ops'"
          @dragstart="onTabDragStart($event, 'ops')"
          @dragend="onTabDragEnd"
        >
          Operace
          <span v-if="operations.length" class="n">{{ operations.length }}</span>
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
        <div v-if="ops.loading && !operations.length" class="tab-state">
          <Spinner size="sm" />
        </div>
        <!-- Empty -->
        <div v-else-if="!operations.length" class="tab-state">
          <div class="mod-dot" />
          <span class="mod-label">Žádné operace</span>
        </div>
        <!-- Summary + table -->
        <template v-else>
          <div class="rib rib-sep">
            <div class="rib-r">
              <div class="rib-i">
                <span class="rib-l">Seřízení</span>
                <span class="rib-v m">{{ formatDuration(totalSetup) }}</span>
              </div>
              <div class="rib-i">
                <span class="rib-l">Výroba</span>
                <span class="rib-v m">{{ formatDuration(totalOp) }}</span>
              </div>
            </div>
          </div>
          <table class="ot">
            <thead>
              <tr>
                <th style="width:28px">#</th>
                <th>Název</th>
                <th class="r" style="width:85px">Seřízení</th>
                <th class="r" style="width:85px">Výroba</th>
                <th class="r" style="width:36px">M</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="op in operations" :key="op.id" :data-testid="`op-row-${op.id}`">
                <td class="mono t4">{{ op.seq }}</td>
                <td>{{ op.name || 'Bez názvu' }}</td>
                <td class="r">
                  <span class="tb s"><span class="d" />{{ formatDuration(op.setup_time_min) }}</span>
                </td>
                <td class="r">
                  <span class="tb o"><span class="d" />{{ formatDuration(op.operation_time_min) }}</span>
                </td>
                <td class="r">
                  <span v-if="op.is_coop" class="cm-badge coop">CO</span>
                  <span v-else :class="['cm-badge', `cm-${op.cutting_mode}`]">{{ cuttingLabel(op.cutting_mode) }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </template>
      </div>

      <!-- ── Tab: Kalkulace ── -->
      <div v-else-if="activeTab === 'pricing'" class="tab-body tab-placeholder">
        <div class="mod-dot" />
        <span class="mod-label">KALKULACE</span>
        <span class="mod-hint">Modul se připravuje</span>
      </div>

      <!-- ── Tab: Materiály ── -->
      <div v-else-if="activeTab === 'materials'" class="tab-body tab-placeholder">
        <div class="mod-dot" />
        <span class="mod-label">MATERIÁLY</span>
        <span class="mod-hint">Modul se připravuje</span>
      </div>

      <!-- ── Tab: Výkres ── -->
      <div v-else-if="activeTab === 'drawing'" class="tab-body tab-placeholder">
        <div class="mod-dot" />
        <span class="mod-label">VÝKRES</span>
        <span class="mod-hint">Modul se připravuje</span>
      </div>

    </template>
  </div>
</template>

<style scoped>
.wdet {
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
.mod-hint { font-size: 10px; opacity: 0.6; }

/* ─── Compact info bar — single row replacing det-head ─── */
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
.det-pn {
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--t1);
  flex-shrink: 0;
  letter-spacing: 0.02em;
}
.det-nm {
  font-size: var(--fs);
  color: var(--t3);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}
.det-bgs {
  display: flex;
  gap: 3px;
  flex-shrink: 0;
}

/* ─── Badge — reference .bdg ─── */
.bdg {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 5px;
  font-size: 10px;
  font-weight: 500;
  border-radius: 99px;
  background: var(--b1);
  color: var(--t2);
}
.bdg .dot { width: 4px; height: 4px; border-radius: 50%; flex-shrink: 0; }
.dot.ok { background: var(--ok); }
.dot.w  { background: var(--warn); }
.dot.e  { background: var(--err); }
.dot.o  { background: var(--t4); }

/* ─── Ribbon — reference .rib ─── */
.rib {
  padding: 4px var(--pad);
  background: rgba(255,255,255,0.02);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.rib-sep { border-top: 1px solid var(--b1); }
.rib-r { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.rib-i { display: flex; align-items: baseline; gap: 4px; }
.rib-l { font-size: 10px; color: var(--t4); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 500; }
.rib-v { font-size: var(--fs); color: var(--t1); font-weight: 500; }
.rib-v.m { font-family: var(--mono); }

/* ─── Tab strip — reference .ptabs ─── */
.ptabs {
  display: flex;
  gap: 1px;
  padding: 3px var(--pad);
  border-bottom: 1px solid var(--b2);
  flex-shrink: 0;
  background: rgba(255,255,255,0.015);
}
.ptab {
  padding: 3px 7px;
  font-size: 10.5px;
  font-weight: 500;
  color: var(--t4);
  background: transparent;
  border: none;
  border-radius: var(--rs);
  cursor: pointer;
  font-family: var(--font);
  display: flex;
  align-items: center;
  gap: 3px;
}
.ptab:hover { color: var(--t3); }
.ptab.on { color: var(--t1); background: var(--b1); }
.ptab[draggable="true"] { cursor: grab; }
.ptab[draggable="true"]:active { cursor: grabbing; }
.n {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--t4);
  padding: 1px 4px;
  background: var(--b1);
  border-radius: 2px;
}

/* ─── Tab body ─── */
.tab-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.tab-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
}
.tab-placeholder {
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
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
.tb .d { width: 3px; height: 3px; border-radius: 50%; flex-shrink: 0; }
.tb.s .d { background: var(--red); }
.tb.o .d { background: var(--ok); }

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
