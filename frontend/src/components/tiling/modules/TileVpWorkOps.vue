<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useCatalogStore } from '@/stores/catalog'
import { useWorkshopStore } from '@/stores/workshop'
import * as workshopApi from '@/api/workshop'
import type { ContextGroup } from '@/types/workspace'
import type { VpListItem } from '@/types/vp'
import type { WorkshopOperation, WorkshopMaterial } from '@/types/workshop'
import Spinner from '@/components/ui/Spinner.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const catalog = useCatalogStore()
const workshop = useWorkshopStore()

// Local state
const operations = ref<WorkshopOperation[]>([])
const loadingOps = ref(false)
const selectedOper = ref<string | null>(null)
const materials = ref<WorkshopMaterial[]>([])
const loadingMats = ref(false)
let opsRequestSeq = 0
let matsRequestSeq = 0

// Focused VP from catalog store
const focusedVp = computed(() => {
  const item = catalog.getFocusedItem(props.ctx)
  return item?.type === 'vp' ? item : null
})

// Find VP detail from store list
const vpDetail = computed<VpListItem | null>(() => {
  if (!focusedVp.value) return null
  return workshop.vpListItems.find(v => v.job === focusedVp.value!.number) ?? null
})

// Watch focused VP -> load operations
watch(focusedVp, async (vp) => {
  operations.value = []
  selectedOper.value = null
  materials.value = []
  if (!vp) return

  const reqId = ++opsRequestSeq
  loadingOps.value = true
  try {
    const detail = workshop.vpListItems.find(v => v.job === vp.number)
    const suffix = detail?.suffix ?? '0'
    const ops = await workshopApi.getJobOperations(vp.number, suffix)
    if (reqId === opsRequestSeq) {
      operations.value = ops
    }
  } catch {
    if (reqId === opsRequestSeq) {
      operations.value = []
    }
  } finally {
    if (reqId === opsRequestSeq) {
      loadingOps.value = false
    }
  }
}, { immediate: true })

// Click on operation -> toggle expand + load materials
async function toggleOper(oper: WorkshopOperation) {
  if (selectedOper.value === oper.OperNum) {
    selectedOper.value = null
    materials.value = []
    return
  }
  selectedOper.value = oper.OperNum
  materials.value = []
  const reqId = ++matsRequestSeq
  loadingMats.value = true
  try {
    const mats = await workshopApi.getOperationMaterials(oper.Job, oper.OperNum, oper.Suffix)
    if (reqId === matsRequestSeq) {
      materials.value = mats
    }
  } catch {
    if (reqId === matsRequestSeq) {
      materials.value = []
    }
  } finally {
    if (reqId === matsRequestSeq) {
      loadingMats.value = false
    }
  }
}

function operStatus(op: WorkshopOperation): 'done' | 'in_progress' | 'idle' {
  const qty = op.QtyComplete ?? 0
  const rel = op.QtyReleased ?? 0
  if (rel > 0 && qty >= rel) return 'done'
  if (qty > 0) return 'in_progress'
  return 'idle'
}

function statusDotClass(s: 'done' | 'in_progress' | 'idle'): string {
  if (s === 'done') return 'sd sd-ok'
  if (s === 'in_progress') return 'sd sd-w'
  return 'sd sd-o'
}

function statLabel(stat: string): string {
  switch (stat?.toUpperCase()) {
    case 'R': return 'Released'
    case 'F': return 'Firm'
    case 'S': return 'Scheduled'
    case 'W': return 'Waiting'
    default: return stat || '\u2014'
  }
}

function statChipClass(stat: string): string {
  switch (stat?.toUpperCase()) {
    case 'R': return 'chip chip-ok'
    case 'F': return 'chip chip-w'
    case 'S': return 'chip chip-blue'
    default: return 'chip chip-o'
  }
}

function fmtNum(v: number | null | undefined): string {
  if (v == null) return '\u2014'
  return String(v)
}

function fmtDate(v: string | null | undefined): string {
  if (!v) return '\u2014'
  return v.length > 10 ? v.substring(0, 10) : v
}
</script>

<template>
  <div class="vwo-root">
    <!-- Empty state -->
    <div v-if="!focusedVp" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Vyberte VP ze seznamu</span>
      <span class="mod-hint">Klikněte na výrobní příkaz vlevo</span>
    </div>

    <!-- VP operations -->
    <template v-else>
      <!-- Header ribbon -->
      <div class="vwo-hdr">
        <span class="vwo-job">{{ vpDetail?.job || focusedVp.number }}</span>
        <span class="vwo-suf">/{{ vpDetail?.suffix || '0' }}</span>
        <span v-if="vpDetail" :class="statChipClass(vpDetail.job_stat)">{{ statLabel(vpDetail.job_stat) }}</span>
        <span class="vwo-item">{{ vpDetail?.item || '' }}</span>
        <span class="vwo-desc">{{ vpDetail?.description || '' }}</span>
      </div>

      <!-- Operations table -->
      <div class="vwo-ops">
        <div v-if="loadingOps" class="vwo-loading">
          <Spinner size="sm" />
        </div>
        <template v-else-if="operations.length > 0">
          <table class="ops-tbl">
            <thead>
              <tr>
                <th class="th-n">#</th>
                <th class="th-wc">Pracoviště</th>
                <th class="th-st">Stav</th>
                <th class="th-num">Rel</th>
                <th class="th-num">Done</th>
                <th class="th-num">Scrap</th>
                <th class="th-num">Setup [h]</th>
                <th class="th-num">Run [ks/h]</th>
                <th class="th-dt">Začátek</th>
                <th class="th-dt">Konec</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="op in operations" :key="op.OperNum">
                <tr
                  :class="['ops-row', { 'ops-sel': selectedOper === op.OperNum }]"
                  @click="toggleOper(op)"
                >
                  <td class="td-n">{{ op.OperNum }}</td>
                  <td class="td-wc">{{ op.Wc }}</td>
                  <td class="td-st"><span :class="statusDotClass(operStatus(op))" /></td>
                  <td class="td-num">{{ fmtNum(op.QtyReleased) }}</td>
                  <td class="td-num">{{ fmtNum(op.QtyComplete) }}</td>
                  <td class="td-num">{{ fmtNum(op.ScrapQty) }}</td>
                  <td class="td-num">{{ fmtNum(op.SetupHrs) }}</td>
                  <td class="td-num">{{ fmtNum(op.RunHrs) }}</td>
                  <td class="td-dt">{{ fmtDate(op.OpDatumSt) }}</td>
                  <td class="td-dt">{{ fmtDate(op.OpDatumSp) }}</td>
                </tr>
                <!-- Materials expand -->
                <tr v-if="selectedOper === op.OperNum" class="mat-expand">
                  <td colspan="10">
                    <div v-if="loadingMats" class="mat-loading">
                      <Spinner size="sm" :inline="true" /> Načítám materiály...
                    </div>
                    <div v-else-if="materials.length === 0" class="mat-empty">
                      Žádné materiály
                    </div>
                    <table v-else class="mat-tbl">
                      <thead>
                        <tr>
                          <th>Materiál</th>
                          <th>Popis</th>
                          <th class="th-num">Spotř./ks</th>
                          <th class="th-num">Celkem</th>
                          <th class="th-num">Vydáno</th>
                          <th class="th-num">Zbývá</th>
                          <th>JM</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="mat in materials" :key="mat.Material" class="mat-row">
                          <td class="mat-code">{{ mat.Material }}</td>
                          <td class="mat-desc">{{ mat.Desc || '' }}</td>
                          <td class="td-num">{{ fmtNum(mat.Qty) }}</td>
                          <td class="td-num">{{ fmtNum(mat.TotCons) }}</td>
                          <td class="td-num">{{ fmtNum(mat.QtyIssued) }}</td>
                          <td class="td-num">{{ fmtNum(mat.RemainingCons) }}</td>
                          <td>{{ mat.UM || '' }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </template>
        <div v-else class="vwo-empty-ops">
          Žádné operace
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.vwo-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow-y: auto;
}

/* Placeholder */
.mod-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
  user-select: none;
  padding: 24px;
}
.mod-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--t4);
}
.mod-label {
  font-size: var(--fsm);
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--t4);
}
.mod-hint {
  font-size: var(--fsm);
  color: var(--t4);
  opacity: 0.6;
}

/* Header ribbon */
.vwo-hdr {
  height: 30px;
  padding: 0 var(--pad);
  border-bottom: 1px solid var(--b1);
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  overflow: hidden;
}
.vwo-job {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
  font-family: var(--mono, monospace);
  flex-shrink: 0;
}
.vwo-suf {
  font-size: var(--fs);
  color: var(--t4);
  font-family: var(--mono, monospace);
  flex-shrink: 0;
}
.vwo-item {
  font-size: var(--fs);
  color: var(--t2);
  font-weight: 500;
  flex-shrink: 0;
  margin-left: 4px;
}
.vwo-desc {
  font-size: var(--fs);
  color: var(--t3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  flex: 1;
}

/* Status chip */
.chip {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--rs);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  flex-shrink: 0;
}
.chip-ok   { background: rgba(76,175,80,0.15); color: var(--ok); }
.chip-w    { background: rgba(255,193,7,0.15);  color: var(--warn); }
.chip-blue { background: rgba(66,165,245,0.15); color: var(--link); }
.chip-o    { background: rgba(158,158,158,0.15); color: var(--t4); }

/* Operations */
.vwo-ops {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0;
}

.vwo-loading,
.vwo-empty-ops {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  color: var(--t4);
  font-size: var(--fs);
}

.ops-tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fsm);
}
.ops-tbl th {
  text-align: left;
  font-weight: 600;
  color: var(--t4);
  padding: 4px 6px;
  border-bottom: 1px solid var(--b1);
  white-space: nowrap;
  position: sticky;
  top: 0;
  background: var(--surface);
  z-index: 1;
}
.th-n  { width: 40px; text-align: center; }
.th-wc { width: 80px; }
.th-st { width: 36px; text-align: center; }
.th-num { width: 60px; text-align: right; }
.th-dt { width: 80px; }

.ops-row {
  cursor: pointer;
  transition: background 80ms var(--ease);
}
.ops-row:hover { background: var(--b1); }
.ops-row.ops-sel { background: rgba(229,57,53,0.04); }

.ops-row td {
  padding: 4px 6px;
  border-bottom: 1px solid rgba(255,255,255,0.025);
  color: var(--t2);
  white-space: nowrap;
}
.td-n { text-align: center; color: var(--t4); font-family: var(--mono, monospace); }
.td-wc { font-weight: 500; }
.td-st { text-align: center; }
.td-num { text-align: right; font-family: var(--mono, monospace); }
.td-dt { font-size: var(--fsm); color: var(--t3); }

/* Status dots */
.sd {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.sd-ok { background: var(--ok); }
.sd-w  { background: var(--warn); }
.sd-o  { background: var(--t4); }

/* Materials expand */
.mat-expand td {
  padding: 0;
  background: rgba(0,0,0,0.1);
}
.mat-loading,
.mat-empty {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: var(--fsm);
  color: var(--t4);
}
.mat-tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}
.mat-tbl th {
  text-align: left;
  font-weight: 500;
  color: var(--t4);
  padding: 3px 6px;
  border-bottom: 1px solid var(--b1);
}
.mat-row td {
  padding: 3px 6px;
  border-bottom: 1px solid rgba(255,255,255,0.02);
  color: var(--t3);
}
.mat-code {
  font-weight: 500;
  color: var(--t2);
  font-family: var(--mono, monospace);
}
.mat-desc {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
