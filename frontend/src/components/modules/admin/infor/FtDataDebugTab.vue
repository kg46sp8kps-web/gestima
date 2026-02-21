<script setup lang="ts">
/**
 * FT Data Debug Tab - Browse and inspect FT v2 training data
 * Features: virtual scroll, CV filter, select/export, expandable rows
 */

import { ref, computed } from 'vue'
import { getFtDebugParts, exportFtDebug } from '@/api/ft-debug'
import { useUiStore } from '@/stores/ui'
import { useWindowsStore } from '@/stores/windows'
import { Download, Search, Check, X, Brain, ExternalLink } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import FtPartDetail from './FtPartDetail.vue'

interface FtPartOperation {
  category: string; machine: string; operation_time_min: number
  setup_time_min: number; manning_pct: number; num_operations: number
  n_vp: number; planned_time_min: number | null; norm_ratio: number | null
  cv: number | null; manning_cv: number | null
}
interface FtPartSummary {
  part_id: number; article_number: string; name: string | null
  file_id: number | null; vp_count: number; material_norm: string | null
  stock_shape: string | null; operations: FtPartOperation[]
  max_cv: number | null; total_production_time: number
  total_planned_time: number | null; norm_ratio: number | null
  skip_reason: string | null; is_eligible: boolean
}

const uiStore = useUiStore()
const windowsStore = useWindowsStore()
const parts = ref<FtPartSummary[]>([])
const loading = ref(false)
const minVp = ref(3)
// CV filter: metric × category
const cvMetric = ref<'off' | 'time' | 'manning' | 'combined'>('off')
const cvCategory = ref<'lathe' | 'mill' | 'overall'>('lathe')
const cvFilterMax = ref(0.5)
// Norm ratio filter: actual/planned, per category like CV
const normFilterMode = ref<'off' | 'range'>('off')
const normCategory = ref<'lathe' | 'mill' | 'overall'>('overall')
const normMin = ref(0.5)
const normMax = ref(2.0)
// Preciz Cut: manning ≤100%, LATHE manning ≥50%, MILL manning ≥70%, ratio ≤5.0
const precizCut = ref(false)
const selectedIds = ref<Set<number>>(new Set())
const expandedId = ref<number | null>(null)

const ROW_HEIGHT = 36
const VISIBLE_ROWS = 60
const scrollTop = ref(0)
const tableContainer = ref<HTMLElement | null>(null)

function getCategoryCv(part: FtPartSummary, category: string, field: 'cv' | 'manning_cv'): number | null {
  const op = part.operations.find(o => o.category === category)
  return op ? op[field] : null
}

/** Check if a part passes CV filter for given field and category */
function passesFilter(part: FtPartSummary, max: number, field: 'cv' | 'manning_cv'): boolean {
  if (cvCategory.value === 'lathe') {
    const v = getCategoryCv(part, 'LATHE', field)
    return v == null || v <= max
  }
  if (cvCategory.value === 'mill') {
    const v = getCategoryCv(part, 'MILL', field)
    return v == null || v <= max
  }
  // overall = both LATHE and MILL must pass
  const vL = getCategoryCv(part, 'LATHE', field)
  const vM = getCategoryCv(part, 'MILL', field)
  return (vL == null || vL <= max) && (vM == null || vM <= max)
}

function getCategoryNormRatio(part: FtPartSummary, category: string): number | null {
  const op = part.operations.find(o => o.category === category)
  return op ? op.norm_ratio : null
}

/** Preciz Cut filter: per-category manning + ratio bounds */
function passesPrecizCut(part: FtPartSummary): boolean {
  for (const op of part.operations) {
    if (op.category === 'LATHE') {
      if (op.manning_pct > 100 || op.manning_pct < 50) return false
      if (op.norm_ratio != null && op.norm_ratio > 5.0) return false
    }
    if (op.category === 'MILL') {
      if (op.manning_pct > 100 || op.manning_pct < 70) return false
      if (op.norm_ratio != null && op.norm_ratio > 5.0) return false
    }
  }
  return true
}

/** Check if a part passes norm ratio filter for selected category */
function passesNormFilter(part: FtPartSummary, min: number, max: number): boolean {
  if (normCategory.value === 'lathe') {
    const r = getCategoryNormRatio(part, 'LATHE')
    return r == null || (r >= min && r <= max)
  }
  if (normCategory.value === 'mill') {
    const r = getCategoryNormRatio(part, 'MILL')
    return r == null || (r >= min && r <= max)
  }
  // overall = both LATHE and MILL must pass
  const rL = getCategoryNormRatio(part, 'LATHE')
  const rM = getCategoryNormRatio(part, 'MILL')
  const latheOk = rL == null || (rL >= min && rL <= max)
  const millOk = rM == null || (rM >= min && rM <= max)
  return latheOk && millOk
}

const filteredParts = computed(() => {
  let result = parts.value

  // Preciz Cut filter (manning bounds + ratio ≤5)
  if (precizCut.value) {
    result = result.filter(p => passesPrecizCut(p))
  }

  // CV filter
  if (cvMetric.value !== 'off') {
    const max = cvFilterMax.value
    result = result.filter(p => {
      if (cvMetric.value === 'time') return passesFilter(p, max, 'cv')
      if (cvMetric.value === 'manning') return passesFilter(p, max, 'manning_cv')
      return passesFilter(p, max, 'cv') && passesFilter(p, max, 'manning_cv')
    })
  }

  // Norm ratio filter (per category, like CV)
  if (normFilterMode.value === 'range') {
    const nMin = normMin.value
    const nMax = normMax.value
    result = result.filter(p => {
      return passesNormFilter(p, nMin, nMax)
    })
  }

  return result
})
const eligibleCount = computed(() => parts.value.filter(p => p.is_eligible).length)
const skippedCount = computed(() => parts.value.filter(p => !p.is_eligible).length)
const selectedCount = computed(() => selectedIds.value.size)
const totalHeight = computed(() => filteredParts.value.length * ROW_HEIGHT)
const startIndex = computed(() => Math.max(0, Math.floor(scrollTop.value / ROW_HEIGHT) - 10))
const endIndex = computed(() => Math.min(filteredParts.value.length, startIndex.value + VISIBLE_ROWS))
const visibleRows = computed(() => filteredParts.value.slice(startIndex.value, endIndex.value))
const offsetY = computed(() => startIndex.value * ROW_HEIGHT)

function onTableScroll(e: Event) { scrollTop.value = (e.target as HTMLElement).scrollTop }

async function loadParts() {
  loading.value = true
  try {
    const data = await getFtDebugParts(minVp.value)
    parts.value = data.parts
    selectedIds.value = new Set(data.parts.filter((p: FtPartSummary) => p.is_eligible).map((p: FtPartSummary) => p.part_id))
    uiStore.showSuccess(`Nacten ${data.total} dilu (${data.eligible} eligible, ${data.skipped} skipped)`)
  } catch (err: unknown) {
    uiStore.showError((err as Error).message || 'Chyba nacteni FT dat')
  } finally { loading.value = false }
}

function toggleSelect(partId: number) {
  if (selectedIds.value.has(partId)) selectedIds.value.delete(partId)
  else selectedIds.value.add(partId)
  selectedIds.value = new Set(selectedIds.value)
}
function selectAllFiltered() {
  selectedIds.value = new Set()
  for (const p of filteredParts.value) { if (p.is_eligible) selectedIds.value.add(p.part_id) }
  selectedIds.value = new Set(selectedIds.value)
}
function deselectAll() { selectedIds.value = new Set() }
function toggleExpand(partId: number) { expandedId.value = expandedId.value === partId ? null : partId }
function openDrawing(articleNumber: string) {
  windowsStore.openWindow('part-drawing', `Drawing - ${articleNumber}`)
}

async function exportJsonl() {
  const ids = [...selectedIds.value]
  if (ids.length === 0) { uiStore.showError('Zadne vybrane dily'); return }
  loading.value = true
  try {
    const data = await exportFtDebug(ids)
    const url = URL.createObjectURL(data)
    const a = document.createElement('a'); a.href = url; a.download = `ft_v2_debug_${ids.length}samples.jsonl`; a.click()
    URL.revokeObjectURL(url)
    uiStore.showSuccess(`Exported ${ids.length} samples`)
  } catch (err: unknown) {
    uiStore.showError((err as Error).message || 'Chyba exportu')
  } finally { loading.value = false }
}

function normRatioClass(ratio: number | null): string {
  if (ratio == null) return ''
  if (ratio < 0.5 || ratio > 3.0) return 'norm-extreme'
  if (ratio < 0.8 || ratio > 1.5) return 'norm-warn'
  return 'norm-ok'
}
function fmtCv(cv: number | null): string { return cv != null ? cv.toFixed(2) : '-' }
function fmtTime(t: number): string { return t.toFixed(2) }
function opsSummary(ops: FtPartOperation[]): string {
  return ops.map(o => `${o.category} ${fmtTime(o.operation_time_min)}`).join(' | ')
}
</script>

<template>
  <div class="ft-debug-tab">
    <div class="toolbar">
      <div class="form-group">
        <label>Min VP</label>
        <input v-model.number="minVp" type="number" min="1" max="20" class="input input-sm" />
      </div>
      <button @click="loadParts" :disabled="loading" class="btn-ghost">
        <Search :size="ICON_SIZE.STANDARD" /> {{ loading ? 'Nacitam...' : 'Nacist data' }}
      </button>
      <button @click="precizCut = !precizCut"
              :class="['btn-ghost', precizCut ? 'btn-preciz-active' : 'btn-secondary']"
              title="Manning ≤100%, LATHE ≥50%, MILL ≥70%, ratio ≤5×">
        {{ precizCut ? '✂ Preciz Cut ON' : '✂ Preciz Cut' }}
      </button>
      <div class="filter-sep">|</div>
      <div class="form-group">
        <label>CV metrika</label>
        <select v-model="cvMetric" class="input input-md">
          <option value="off">Vypnuto</option>
          <option value="time">Strojní čas</option>
          <option value="manning">Manning</option>
          <option value="combined">Čas + Manning</option>
        </select>
      </div>
      <div v-if="cvMetric !== 'off'" class="form-group">
        <label>Kategorie</label>
        <select v-model="cvCategory" class="input input-md">
          <option value="lathe">LATHE</option>
          <option value="mill">MILL</option>
          <option value="overall">LATHE+MILL</option>
        </select>
      </div>
      <div v-if="cvMetric !== 'off'" class="form-group">
        <label>Max CV</label>
        <select v-model.number="cvFilterMax" class="input input-sm">
          <option :value="0.3">0.3</option>
          <option :value="0.5">0.5</option>
          <option :value="0.7">0.7</option>
          <option :value="1.0">1.0</option>
          <option :value="1.5">1.5</option>
        </select>
      </div>
      <div class="filter-sep">|</div>
      <div class="form-group">
        <label>Plnění normy</label>
        <select v-model="normFilterMode" class="input input-md">
          <option value="off">Vypnuto</option>
          <option value="range">Rozsah</option>
        </select>
      </div>
      <div v-if="normFilterMode === 'range'" class="form-group">
        <label>Kategorie</label>
        <select v-model="normCategory" class="input input-md">
          <option value="lathe">LATHE</option>
          <option value="mill">MILL</option>
          <option value="overall">LATHE+MILL</option>
        </select>
      </div>
      <div v-if="normFilterMode === 'range'" class="form-group">
        <label>Min</label>
        <select v-model.number="normMin" class="input input-sm">
          <option :value="0.3">0.3x</option>
          <option :value="0.5">0.5x</option>
          <option :value="0.8">0.8x</option>
          <option :value="1.0">1.0x</option>
        </select>
      </div>
      <div v-if="normFilterMode === 'range'" class="form-group">
        <label>Max</label>
        <select v-model.number="normMax" class="input input-sm">
          <option :value="1.2">1.2x</option>
          <option :value="1.5">1.5x</option>
          <option :value="2.0">2.0x</option>
          <option :value="3.0">3.0x</option>
          <option :value="5.0">5.0x</option>
        </select>
      </div>
      <div class="spacer"></div>
      <button @click="selectAllFiltered" class="btn-ghost btn-secondary">
        <Check :size="ICON_SIZE.STANDARD" /> Vybrat filtr.
      </button>
      <button @click="deselectAll" class="btn-ghost btn-secondary">
        <X :size="ICON_SIZE.STANDARD" /> Zrusit vyber
      </button>
      <button @click="exportJsonl" :disabled="selectedCount === 0 || loading" class="btn-ghost btn-primary">
        <Download :size="ICON_SIZE.STANDARD" /> Export JSONL ({{ selectedCount }})
      </button>
    </div>

    <div v-if="parts.length > 0" class="stats-bar">
      <span>Celkem: {{ parts.length }}</span>
      <span class="stat-eligible">Eligible: {{ eligibleCount }}</span>
      <span class="stat-skipped">Skipped: {{ skippedCount }}</span>
      <span>Filtrovano: {{ filteredParts.length }}</span>
      <span class="stat-selected">Vybrano: {{ selectedCount }}</span>
    </div>

    <div v-if="parts.length > 0" class="table-scroll" ref="tableContainer" @scroll="onTableScroll">
      <table class="ft-table">
        <thead>
          <tr>
            <th class="col-check">&#9745;</th>
            <th>Artikl</th><th>Nazev</th><th>VP</th><th>Material</th>
            <th>Operace (GT)</th><th>Cas</th><th>Norma</th><th>Max CV</th><th>Vykres</th><th>Status</th>
          </tr>
        </thead>
        <tbody :style="{ height: totalHeight + 'px', position: 'relative' }">
          <tr v-if="offsetY > 0" :style="{ height: offsetY + 'px' }"><td colspan="11"></td></tr>
          <template v-for="part in visibleRows" :key="part.part_id">
            <tr :class="['part-row', { 'row-skipped': !part.is_eligible, 'row-expanded': expandedId === part.part_id }]"
                :style="{ height: ROW_HEIGHT + 'px' }">
              <td class="col-check" @click.stop="toggleSelect(part.part_id)">
                <input type="checkbox" :checked="selectedIds.has(part.part_id)" />
              </td>
              <td class="clickable" @click="toggleExpand(part.part_id)">{{ part.article_number }}</td>
              <td :title="part.name || ''">{{ (part.name || '').slice(0, 25) }}</td>
              <td class="mono">{{ part.vp_count }}</td>
              <td>{{ part.material_norm || '-' }}</td>
              <td class="mono col-ops">{{ opsSummary(part.operations) }}</td>
              <td class="mono">{{ fmtTime(part.total_production_time) }}</td>
              <td class="mono" :class="normRatioClass(part.norm_ratio)">
                {{ part.norm_ratio != null ? part.norm_ratio.toFixed(2) + 'x' : '-' }}
              </td>
              <td class="mono" :class="{ 'cv-high': part.max_cv != null && part.max_cv > 0.5 }">{{ fmtCv(part.max_cv) }}</td>
              <td>
                <button v-if="part.file_id" @click.stop="openDrawing(part.article_number)" class="btn-icon">
                  <ExternalLink :size="ICON_SIZE.SMALL" />
                </button>
                <span v-else class="text-tertiary">-</span>
              </td>
              <td>
                <span v-if="part.skip_reason" class="badge-skip" :title="part.skip_reason">{{ part.skip_reason }}</span>
                <span v-else class="badge-ok">OK</span>
              </td>
            </tr>
            <tr v-if="expandedId === part.part_id" class="detail-row">
              <td colspan="11"><FtPartDetail :part="part" /></td>
            </tr>
          </template>
          <tr v-if="endIndex < filteredParts.length" :style="{ height: (filteredParts.length - endIndex) * ROW_HEIGHT + 'px' }"><td colspan="11"></td></tr>
        </tbody>
      </table>
    </div>

    <div v-else-if="!loading" class="empty-state">
      <Brain :size="ICON_SIZE.HERO" />
      <p>Kliknete "Nacist data" pro zobrazeni FT eligible dilu</p>
    </div>
  </div>
</template>

<style scoped>
.ft-debug-tab { padding: var(--space-4); overflow: auto; display: flex; flex-direction: column; gap: var(--space-3); height: 100%; }
.toolbar { display: flex; gap: var(--space-2); align-items: flex-end; flex-wrap: wrap; }
.spacer { flex: 1; }
.input-sm { width: 80px; }
.input-md { width: 130px; }
.stats-bar { display: flex; gap: var(--space-4); font-size: var(--text-sm); color: var(--text-secondary); padding: var(--space-2) var(--space-3); background: var(--bg-surface); border-radius: var(--radius-md); border: 1px solid var(--border-default); }
.stat-eligible { color: rgb(34, 197, 94); font-weight: 600; }
.stat-skipped { color: var(--text-tertiary); }
.stat-selected { color: var(--color-brand); font-weight: 600; }
.table-scroll { overflow: auto; border: 1px solid var(--border-default); border-radius: var(--radius-md); flex: 1; min-height: 0; max-height: 520px; }
.ft-table { width: 100%; border-collapse: collapse; font-size: var(--text-xs); }
.ft-table th { background: var(--bg-surface); padding: var(--space-1) var(--space-2); text-align: left; font-weight: 600; color: var(--text-secondary); border-bottom: 1px solid var(--border-default); position: sticky; top: 0; z-index: 1; white-space: nowrap; }
.ft-table td { padding: var(--space-1) var(--space-2); border-bottom: 1px solid var(--border-subtle); white-space: nowrap; }
.ft-table tbody tr.part-row:hover { background: var(--state-hover); }
.col-check { width: 28px; text-align: center; }
.col-ops { max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
.mono { font-variant-numeric: tabular-nums; font-family: var(--font-mono, monospace); }
.cv-high { color: var(--color-danger); font-weight: 600; }
.norm-ok { color: rgb(34, 197, 94); }
.norm-warn { color: rgb(234, 179, 8); font-weight: 600; }
.norm-extreme { color: var(--color-danger); font-weight: 600; }
.btn-preciz-active { color: rgb(34, 197, 94) !important; border-color: rgb(34, 197, 94) !important; background: rgba(34, 197, 94, 0.08) !important; font-weight: 600; }
.filter-sep { color: var(--text-tertiary); align-self: center; padding: 0 var(--space-1); }
.row-skipped { opacity: 0.5; }
.row-expanded { background: var(--bg-raised); }
.clickable { cursor: pointer; color: var(--color-brand); }
.btn-icon { background: transparent; border: none; cursor: pointer; color: var(--text-secondary); padding: var(--space-1); border-radius: var(--radius-sm); display: inline-flex; align-items: center; }
.btn-icon:hover { color: var(--text-primary); }
.text-tertiary { color: var(--text-tertiary); }
.badge-ok { display: inline-block; padding: 1px var(--space-2); background: rgba(34, 197, 94, 0.12); color: rgb(34, 197, 94); border-radius: var(--radius-sm); font-size: var(--text-2xs, 10px); font-weight: 600; }
.badge-skip { display: inline-block; padding: 1px var(--space-2); background: rgba(239, 68, 68, 0.12); color: rgb(239, 68, 68); border-radius: var(--radius-sm); font-size: var(--text-2xs, 10px); font-weight: 600; max-width: 120px; overflow: hidden; text-overflow: ellipsis; }
.detail-row td { padding: 0; background: var(--bg-raised); }
</style>
