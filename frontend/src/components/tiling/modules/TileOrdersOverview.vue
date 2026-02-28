<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as plannerApi from '@/api/productionPlanner'
import { useCatalogStore } from '@/stores/catalog'
import { useWorkshopStore } from '@/stores/workshop'
import type { PriorityTier } from '@/types/production-planner'
import type { ContextGroup } from '@/types/workspace'
import type { WorkshopOrderOverviewRow, WorkshopOrderVpCandidate } from '@/types/workshop'
import Input from '@/components/ui/Input.vue'
import Spinner from '@/components/ui/Spinner.vue'
import { formatDate, formatNumber } from '@/utils/formatters'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()

// ─── Store + Cross-tile linking (VP focus) ──────────────────────────
const workshopStore = useWorkshopStore()
const catalog = useCatalogStore()

const focusedVp = computed(() => {
  const item = catalog.getFocusedItem(props.ctx)
  if (item?.type === 'vp') return item.number
  return null
})

function onRowClick(row: WorkshopOrderOverviewRow) {
  const vpJob = selectedVpJob(row)
  if (vpJob) {
    catalog.focusItem({ type: 'vp', number: vpJob }, props.ctx)
  }
  // Toggle expand for rows with multiple VP candidates
  if (row.vp_candidates.length > 1) {
    expandedRows.value[row.row_id] = !expandedRows.value[row.row_id]
  }
}

function onVpSubRowClick(row: WorkshopOrderOverviewRow, vp: WorkshopOrderVpCandidate) {
  selectedVpByRow.value[row.row_id] = vp.job
  catalog.focusItem({ type: 'vp', number: vp.job }, props.ctx)
}

function isRowExpanded(row: WorkshopOrderOverviewRow): boolean {
  return !!expandedRows.value[row.row_id] && row.vp_candidates.length > 1
}

// ─── Column configuration ───────────────────────────────────────────
interface OrderColumn {
  id: string
  label: string
  defaultVisible: boolean
  minWidth: number
  defaultWidth: number
  align: 'left' | 'right' | 'center'
  sortable: boolean
  truncate?: boolean
  mono?: boolean
}

const COLUMNS: OrderColumn[] = [
  { id: 'row_num', label: '#', defaultVisible: true, minWidth: 32, defaultWidth: 36, align: 'right', sortable: false },
  { id: 'customer_name', label: 'Zákazník', defaultVisible: true, minWidth: 80, defaultWidth: 140, align: 'left', sortable: true, truncate: true },
  { id: 'delivery_name', label: 'Dodání', defaultVisible: true, minWidth: 80, defaultWidth: 120, align: 'left', sortable: true, truncate: true },
  { id: 'co_num', label: 'NO Zak.', defaultVisible: true, minWidth: 60, defaultWidth: 85, align: 'left', sortable: true, mono: true },
  { id: 'item', label: 'Pol.', defaultVisible: true, minWidth: 50, defaultWidth: 70, align: 'left', sortable: true, mono: true },
  { id: 'description', label: 'Popis', defaultVisible: true, minWidth: 80, defaultWidth: 180, align: 'left', sortable: true, truncate: true },
  { id: 'confirm_date', label: 'Potvrzeno', defaultVisible: true, minWidth: 70, defaultWidth: 88, align: 'left', sortable: true },
  { id: 'due_date', label: 'Plán do', defaultVisible: true, minWidth: 70, defaultWidth: 88, align: 'left', sortable: true },
  { id: 'promise_date', label: 'Slíbené', defaultVisible: false, minWidth: 70, defaultWidth: 88, align: 'left', sortable: true },
  { id: 'qty_ordered', label: 'Obj.', defaultVisible: true, minWidth: 40, defaultWidth: 55, align: 'right', sortable: true },
  { id: 'qty_shipped', label: 'Exp.', defaultVisible: true, minWidth: 40, defaultWidth: 55, align: 'right', sortable: true },
  { id: 'qty_wip', label: 'WIP', defaultVisible: true, minWidth: 40, defaultWidth: 55, align: 'right', sortable: true },
  { id: 'tier', label: 'Tier', defaultVisible: true, minWidth: 36, defaultWidth: 42, align: 'center', sortable: false },
  { id: 'selected_vp_job', label: 'VP', defaultVisible: true, minWidth: 100, defaultWidth: 140, align: 'left', sortable: true },
  { id: 'material_ready', label: 'Přip.', defaultVisible: true, minWidth: 40, defaultWidth: 55, align: 'center', sortable: true },
]

// ─── Reactive state (SWR: rows + loading + error ze storu) ──────────
const rows = computed(() => workshopStore.ordersOverviewRows)
const loading = computed(() => workshopStore.ordersLoading)
const error = computed(() => workshopStore.ordersError)

const customerFilter = ref<string | null>(null)
const searchFilter = ref<string | null>('')
const dueFrom = ref<string | null>(null)
const dueTo = ref<string | null>(null)
const selectedVpByRow = ref<Record<string, string>>({})
const expandedRows = ref<Record<string, boolean>>({})

// ─── Column widths + visibility with localStorage persistence ───────
const LS_WIDTHS_KEY = 'gestima.orders-overview.col-widths'
const LS_VISIBLE_KEY = 'gestima.orders-overview.col-visible'

function loadWidths(): Record<string, number> {
  try {
    const raw = localStorage.getItem(LS_WIDTHS_KEY)
    if (raw) return JSON.parse(raw) as Record<string, number>
  } catch { /* ignore */ }
  const out: Record<string, number> = {}
  for (const col of COLUMNS) out[col.id] = col.defaultWidth
  return out
}

function loadVisible(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(LS_VISIBLE_KEY)
    if (raw) return JSON.parse(raw) as Record<string, boolean>
  } catch { /* ignore */ }
  const out: Record<string, boolean> = {}
  for (const col of COLUMNS) out[col.id] = col.defaultVisible
  return out
}

const columnWidths = ref<Record<string, number>>(loadWidths())
const columnVisible = ref<Record<string, boolean>>(loadVisible())

let saveTimer: ReturnType<typeof setTimeout> | null = null
function debouncedSave() {
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    localStorage.setItem(LS_WIDTHS_KEY, JSON.stringify(columnWidths.value))
    localStorage.setItem(LS_VISIBLE_KEY, JSON.stringify(columnVisible.value))
  }, 300)
}

watch(columnWidths, debouncedSave, { deep: true })
watch(columnVisible, debouncedSave, { deep: true })

const visibleColumns = computed(() => COLUMNS.filter((c) => columnVisible.value[c.id] !== false))

// ─── Column visibility dropdown ─────────────────────────────────────
const showColDropdown = ref(false)
const colDropdownRef = ref<HTMLElement | null>(null)

function toggleColDropdown() {
  showColDropdown.value = !showColDropdown.value
}

function onClickOutsideDropdown(e: MouseEvent) {
  if (colDropdownRef.value && !colDropdownRef.value.contains(e.target as Node)) {
    showColDropdown.value = false
  }
}

// ─── Column resize ──────────────────────────────────────────────────
const resizingCol = ref<string | null>(null)

function startResize(colId: string, e: MouseEvent) {
  e.preventDefault()
  resizingCol.value = colId
  const startX = e.clientX
  const startWidth = columnWidths.value[colId] ?? 80
  const col = COLUMNS.find((c) => c.id === colId)
  const minW = col?.minWidth ?? 30

  function onMove(ev: MouseEvent) {
    const diff = ev.clientX - startX
    columnWidths.value[colId] = Math.max(minW, startWidth + diff)
  }
  function onUp() {
    resizingCol.value = null
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

function resetColWidth(colId: string) {
  const col = COLUMNS.find((c) => c.id === colId)
  if (col) columnWidths.value[colId] = col.defaultWidth
}

// ─── Tier per VP (job key) ──────────────────────────────────────────
const tierByVp = ref<Record<string, PriorityTier>>({})

const TIER_CYCLE: PriorityTier[] = ['normal', 'urgent', 'hot']

function tierIcon(tier: PriorityTier | undefined): string {
  if (tier === 'hot') return '\u{1F525}'
  if (tier === 'urgent') return '\u26A1'
  return '\u2014'
}

function getRowTier(row: WorkshopOrderOverviewRow): PriorityTier {
  const vp = selectedVp(row)
  if (!vp) return 'normal'
  return tierByVp.value[vp.job] ?? 'normal'
}

async function cycleRowTier(row: WorkshopOrderOverviewRow) {
  const vp = selectedVp(row)
  if (!vp) return
  const current = tierByVp.value[vp.job] ?? 'normal'
  const idx = TIER_CYCLE.indexOf(current)
  const next = TIER_CYCLE[(idx + 1) % TIER_CYCLE.length]!
  tierByVp.value[vp.job] = next
  const suffix = vp.suffix ?? '0'
  try {
    await plannerApi.setTier(vp.job, suffix, next)
    catalog.notifyTierChange(vp.job, suffix, next)
  } catch {
    tierByVp.value[vp.job] = current
  }
}

// Watch cross-tile tier changes from other tiles
watch(() => catalog.lastTierChange, (change) => {
  if (!change) return
  tierByVp.value[change.job] = change.tier
})

// ─── Sorting ────────────────────────────────────────────────────────
type SortKey =
  | 'customer_name'
  | 'delivery_name'
  | 'co_num'
  | 'item'
  | 'description'
  | 'confirm_date'
  | 'due_date'
  | 'promise_date'
  | 'qty_ordered'
  | 'qty_shipped'
  | 'qty_wip'
  | 'selected_vp_job'
  | 'material_ready'
type SortDir = 'asc' | 'desc'

const sortKey = ref<SortKey | null>(null)
const sortDir = ref<SortDir>('asc')

function toggleSort(key: SortKey) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
}

function sortMark(key: SortKey): string {
  if (sortKey.value !== key) return ''
  return sortDir.value === 'asc' ? ' \u25B2' : ' \u25BC'
}

// ─── Customer dropdown ──────────────────────────────────────────────
const uniqueCustomers = computed(() => {
  const map = new Map<string, string>()
  for (const row of rows.value) {
    const code = row.customer_code
    if (!code) continue
    const name = row.customer_name ?? code
    if (!map.has(code)) map.set(code, name)
  }
  return Array.from(map.entries())
    .map(([code, name]) => ({ code, name }))
    .sort((a, b) => a.name.localeCompare(b.name, 'cs'))
})

// ─── Sorted rows ────────────────────────────────────────────────────
function parseSortDate(value: string | null | undefined): number {
  const raw = (value ?? '').trim()
  if (!raw) return 0
  const m = raw.match(/^(\d{4})(\d{2})(\d{2})/)
  if (m) return Number(m[1]) * 10000 + Number(m[2]) * 100 + Number(m[3])
  const d = new Date(raw)
  return Number.isNaN(d.getTime()) ? 0 : d.getTime()
}

const sortedRows = computed(() => {
  let filtered = rows.value
  if (customerFilter.value) {
    const code = customerFilter.value
    filtered = filtered.filter((r) => r.customer_code === code)
  }
  if (!sortKey.value) return filtered

  const key = sortKey.value
  const dir = sortDir.value === 'asc' ? 1 : -1

  return [...filtered].sort((a, b) => {
    let va: string | number | null = null
    let vb: string | number | null = null

    if (key === 'qty_ordered' || key === 'qty_shipped' || key === 'qty_wip') {
      va = a[key] ?? 0
      vb = b[key] ?? 0
      return ((va as number) - (vb as number)) * dir
    }
    if (key === 'confirm_date' || key === 'due_date' || key === 'promise_date') {
      va = parseSortDate(a[key])
      vb = parseSortDate(b[key])
      return ((va as number) - (vb as number)) * dir
    }
    va = (a[key] ?? '') as string
    vb = (b[key] ?? '') as string
    return (va as string).localeCompare(vb as string, 'cs') * dir
  })
})

const hasRows = computed(() => rows.value.length > 0)

// ─── Row helpers ────────────────────────────────────────────────────
function selectedVpJob(row: WorkshopOrderOverviewRow): string | null {
  const manual = selectedVpByRow.value[row.row_id]
  if (manual) return manual
  if (row.selected_vp_job) return row.selected_vp_job
  return row.vp_candidates[0]?.job ?? null
}

function selectedVp(row: WorkshopOrderOverviewRow): WorkshopOrderVpCandidate | null {
  const selected = selectedVpJob(row)
  if (!selected) return null
  const hit = row.vp_candidates.find((vp) => vp.job === selected)
  return hit ?? null
}

function rowOperations(row: WorkshopOrderOverviewRow) {
  const selected = selectedVp(row)
  if (selected) return selected.operations
  return row.operations ?? []
}

const operationColumns = computed(() => {
  let maxColumns = 0
  for (const row of sortedRows.value) {
    maxColumns = Math.max(maxColumns, rowOperations(row).length)
    for (const vp of row.vp_candidates) {
      maxColumns = Math.max(maxColumns, vp.operations.length)
    }
  }
  return Array.from({ length: maxColumns }, (_, index) => index + 1)
})

function operationCellClass(row: WorkshopOrderOverviewRow, columnIndex: number): string {
  const op = rowOperations(row)[columnIndex]
  if (!op) return 'op-cell op-cell--empty'
  if (op.status === 'done') return 'op-cell op-cell--done'
  if (op.status === 'in_progress') return 'op-cell op-cell--progress'
  return 'op-cell op-cell--idle'
}

function operationCellText(row: WorkshopOrderOverviewRow, columnIndex: number): string {
  const op = rowOperations(row)[columnIndex]
  if (!op) return ''
  return op.wc || op.oper_num
}

function vpOpCellClass(vp: WorkshopOrderVpCandidate, columnIndex: number): string {
  const op = vp.operations[columnIndex]
  if (!op) return 'op-cell op-cell--empty'
  if (op.status === 'done') return 'op-cell op-cell--done'
  if (op.status === 'in_progress') return 'op-cell op-cell--progress'
  return 'op-cell op-cell--idle'
}

function vpOpCellText(vp: WorkshopOrderVpCandidate, columnIndex: number): string {
  const op = vp.operations[columnIndex]
  if (!op) return ''
  return op.wc || op.oper_num
}

// ─── Material columns (dynamic, like operations) ────────────────────
const materialColumns = computed(() => {
  const maxCols = sortedRows.value.reduce((acc, row) => Math.max(acc, (row.materials ?? []).length), 0)
  return Array.from({ length: maxCols }, (_, i) => i + 1)
})

function materialCellClass(row: WorkshopOrderOverviewRow, columnIndex: number): string {
  const mat = (row.materials ?? [])[columnIndex]
  if (!mat) return 'mat-cell mat-cell--empty'
  if (mat.status === 'done') return 'mat-cell mat-cell--done'
  return 'mat-cell mat-cell--idle'
}

function materialCellText(row: WorkshopOrderOverviewRow, columnIndex: number): string {
  const mat = (row.materials ?? [])[columnIndex]
  if (!mat) return ''
  return mat.material
}

function rowTierClass(row: WorkshopOrderOverviewRow): string {
  const tier = getRowTier(row)
  if (tier === 'hot') return 'row-hot'
  if (tier === 'urgent') return 'row-urgent'
  return ''
}

function isRowFocused(row: WorkshopOrderOverviewRow): boolean {
  const vpJob = selectedVpJob(row)
  return !!vpJob && vpJob === focusedVp.value
}

// ─── Cell value helpers using shared formatters ─────────────────────
function cellValue(row: WorkshopOrderOverviewRow, colId: string): string {
  switch (colId) {
    case 'customer_name': return row.customer_name ?? row.customer_code ?? '\u2014'
    case 'delivery_name': return row.delivery_name ?? row.delivery_code ?? '\u2014'
    case 'co_num': return row.co_num ?? '\u2014'
    case 'item': return row.item ?? '\u2014'
    case 'description': return row.description ?? '\u2014'
    case 'confirm_date': return formatDate(row.confirm_date)
    case 'due_date': return formatDate(row.due_date)
    case 'promise_date': return formatDate(row.promise_date)
    case 'qty_ordered': return formatNumber(row.qty_ordered, 0)
    case 'qty_shipped': return formatNumber(row.qty_shipped, 0)
    case 'qty_wip': return formatNumber(row.qty_wip, 0)
    case 'material_ready': return row.material_ready ? '\u2713' : '\u2717'
    default: return '\u2014'
  }
}

// ─── Fetch (delegováno do storu — SWR) ──────────────────────────────
function fetchOrdersOpts() {
  return {
    due_from: (dueFrom.value ?? '').trim() || undefined,
    due_to: (dueTo.value ?? '').trim() || undefined,
    search: (searchFilter.value ?? '').trim() || undefined,
    limit: 2000,
  }
}

async function fetchOrders(): Promise<void> {
  await workshopStore.fetchOrders(fetchOrdersOpts())
}

let fetchTimer: ReturnType<typeof setTimeout> | null = null
function debouncedFetch() {
  if (fetchTimer) clearTimeout(fetchTimer)
  fetchTimer = setTimeout(() => void fetchOrders(), 400)
}

watch([dueFrom, dueTo], debouncedFetch)

// ─── Auto-scroll to focused row from cross-tile ─────────────────
const tableWrapRef = ref<HTMLElement | null>(null)

watch(focusedVp, (job) => {
  if (!job) return
  void nextTick(() => {
    const wrap = tableWrapRef.value
    if (!wrap) return
    const el = wrap.querySelector(`[data-vp-job="${job}"]`) as HTMLElement | null
    if (el) {
      el.scrollIntoView({ block: 'center', behavior: 'smooth' })
    }
  })
})

onMounted(() => {
  void workshopStore.fetchOrdersIfStale(fetchOrdersOpts(), 60000)
  document.addEventListener('click', onClickOutsideDropdown)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutsideDropdown)
})
</script>

<template>
  <div class="orders-overview" data-testid="tile-orders-overview">
    <div class="orders-overview__toolbar">
      <Input
        v-model="dueFrom"
        type="date"
        bare
        label="Od"
        testid="orders-filter-due-from"
        class="orders-overview__field orders-overview__field--date"
      />
      <Input
        v-model="dueTo"
        type="date"
        bare
        label="Do"
        testid="orders-filter-due-to"
        class="orders-overview__field orders-overview__field--date"
      />

      <div class="orders-overview__field orders-overview__field--customer">
        <label class="filter-label">Zákazník</label>
        <div class="filter-select-wrap">
          <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
          <select
            :value="customerFilter ?? ''"
            class="filter-select"
            data-testid="orders-filter-customer"
            @change="customerFilter = ($event.target as HTMLSelectElement).value || null"
          >
            <option value="">Všichni</option>
            <option
              v-for="c in uniqueCustomers"
              :key="c.code"
              :value="c.code"
            >
              {{ c.name }}
            </option>
          </select>
          <span class="filter-select-arrow">&#x25BE;</span>
        </div>
      </div>

      <Input
        v-model="searchFilter"
        bare
        type="text"
        label="Hledat"
        testid="orders-filter-search"
        class="orders-overview__field orders-overview__field--search"
      />

      <!-- Column visibility dropdown -->
      <div ref="colDropdownRef" class="col-dropdown-wrap">
        <button
          class="btn-secondary orders-overview__col-btn"
          data-testid="orders-col-toggle"
          @click.stop="toggleColDropdown"
        >Sloupce</button>
        <div v-if="showColDropdown" class="col-dropdown" data-testid="orders-col-dropdown">
          <label
            v-for="col in COLUMNS.filter(c => c.id !== 'row_num')"
            :key="col.id"
            class="col-dropdown__item"
          >
            <input
              type="checkbox"
              :checked="columnVisible[col.id] !== false"
              @change="columnVisible[col.id] = ($event.target as HTMLInputElement).checked"
            />
            {{ col.label }}
          </label>
        </div>
      </div>

      <span class="badge" data-testid="orders-count">
        {{ sortedRows.length }} zakázek
        <span v-if="workshopStore.ordersIsRevalidating" class="swr-dot" title="Obnovuji na pozadí…" />
      </span>

      <button class="btn-secondary orders-overview__refresh" data-testid="orders-refresh" @click="fetchOrders">
        Obnovit
      </button>
    </div>

    <div v-if="loading && !hasRows" class="orders-overview__state">
      <Spinner text="Načítám přehled..." />
    </div>
    <div v-else-if="error" class="orders-overview__state orders-overview__state--error">
      {{ error }}
    </div>
    <div v-else-if="!hasRows" class="orders-overview__state">
      Žádné zakázky pro zadaný filtr.
    </div>
    <div v-else ref="tableWrapRef" class="orders-overview__table-wrap">
      <table class="orders-table">
        <thead>
          <tr>
            <!-- Static columns from config -->
            <th
              v-for="col in visibleColumns"
              :key="col.id"
              :class="[
                col.sortable ? 'sortable' : '',
                col.align === 'right' ? 'r' : '',
                col.align === 'center' ? 'c' : '',
                col.id === 'row_num' ? 'row-num' : '',
                col.id === 'tier' ? 'q-tier-col' : '',
              ]"
              :style="{ width: columnWidths[col.id] + 'px', position: 'relative' }"
              @click="col.sortable ? toggleSort(col.id as SortKey) : undefined"
            >
              {{ col.label }}{{ col.sortable ? sortMark(col.id as SortKey) : '' }}
              <div
                v-if="col.id !== 'row_num'"
                class="resize-grip"
                :class="{ 'resize-grip--active': resizingCol === col.id }"
                @mousedown.stop="startResize(col.id, $event)"
                @dblclick.stop="resetColWidth(col.id)"
              />
            </th>
            <!-- Dynamic operation columns -->
            <th
              v-for="column in operationColumns"
              :key="`op-col-${column}`"
              class="op-col"
            >
              {{ column }}
            </th>
            <!-- Dynamic material columns -->
            <th
              v-for="column in materialColumns"
              :key="`mat-col-${column}`"
              class="mat-col"
            >
              Mat{{ column }}
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(row, idx) in sortedRows" :key="row.row_id">
            <tr
              :class="[
                rowTierClass(row),
                { 'row-focused': isRowFocused(row), 'row-expandable': row.vp_candidates.length > 1, 'row-expanded': isRowExpanded(row) },
              ]"
              :data-testid="`orders-row-${row.row_id}`"
              :data-vp-job="selectedVpJob(row) ?? undefined"
              @click="onRowClick(row)"
            >
              <template v-for="col in visibleColumns" :key="`${row.row_id}-${col.id}`">
                <!-- row_num -->
                <td v-if="col.id === 'row_num'" class="row-num">{{ idx + 1 }}</td>
                <!-- tier -->
                <td v-else-if="col.id === 'tier'" class="q-tier-cell">
                  <button
                    v-if="selectedVp(row)"
                    class="q-tier-btn"
                    :title="`Tier: ${getRowTier(row)} — klikni pro změnu`"
                    @click.stop="cycleRowTier(row)"
                  >{{ tierIcon(getRowTier(row)) }}</button>
                  <span v-else class="q-tier-na">&mdash;</span>
                </td>
                <!-- selected_vp_job / Multiple -->
                <td v-else-if="col.id === 'selected_vp_job'" class="vp-cell">
                  <template v-if="row.vp_candidates.length > 1">
                    <span class="vp-multi-label" :class="{ 'vp-multi-label--open': isRowExpanded(row) }">
                      <span class="vp-expand-icon">{{ isRowExpanded(row) ? '\u25BC' : '\u25B6' }}</span>
                      Multiple
                      <span class="vp-count-badge">{{ row.vp_candidates.length }}</span>
                    </span>
                  </template>
                  <span v-else class="mono">{{ selectedVpJob(row) ?? '\u2014' }}</span>
                </td>
                <!-- material_ready -->
                <td v-else-if="col.id === 'material_ready'" class="c" :class="row.material_ready ? 'mat-ready--yes' : 'mat-ready--no'">
                  {{ row.material_ready ? '\u2713' : '\u2717' }}
                </td>
                <!-- generic cell -->
                <td
                  v-else
                  :class="[
                    col.align === 'right' ? 'r' : '',
                    col.align === 'center' ? 'c' : '',
                    col.mono ? 'mono' : '',
                    col.truncate ? 'cell-truncate' : '',
                  ]"
                >{{ cellValue(row, col.id) }}</td>
              </template>
              <!-- Dynamic operation cells -->
              <td
                v-for="column in operationColumns"
                :key="`${row.row_id}-op-${column}`"
                :class="operationCellClass(row, column - 1)"
              >
                {{ operationCellText(row, column - 1) }}
              </td>
              <!-- Dynamic material cells -->
              <td
                v-for="column in materialColumns"
                :key="`${row.row_id}-mat-${column}`"
                :class="materialCellClass(row, column - 1)"
                :title="materialCellText(row, column - 1)"
              >
                {{ materialCellText(row, column - 1) }}
              </td>
            </tr>
            <!-- Expanded VP sub-rows -->
            <tr
              v-for="vp in (isRowExpanded(row) ? row.vp_candidates : [])"
              :key="`${row.row_id}-vp-${vp.job}`"
              class="vp-sub-row"
              :class="{ 'vp-sub-row--selected': selectedVpJob(row) === vp.job }"
              @click.stop="onVpSubRowClick(row, vp)"
            >
              <!-- VP info spanning static columns -->
              <td :colspan="visibleColumns.length">
                <div class="vp-sub-cell">
                  <span class="vp-sub-job mono">{{ vp.job }}<template v-if="vp.suffix && vp.suffix !== '0'">/{{ vp.suffix }}</template></span>
                  <span v-if="vp.job_stat" class="vp-sub-stat">{{ vp.job_stat }}</span>
                  <span v-if="vp.qty_released != null" class="vp-sub-qty">{{ vp.qty_released }} ks</span>
                  <span v-if="vp.due_date" class="vp-sub-date">{{ formatDate(vp.due_date) }}</span>
                </div>
              </td>
              <!-- Operation cells aligned with main row columns -->
              <td
                v-for="column in operationColumns"
                :key="`${row.row_id}-vp-${vp.job}-op-${column}`"
                :class="vpOpCellClass(vp, column - 1)"
              >
                {{ vpOpCellText(vp, column - 1) }}
              </td>
              <!-- Material cells (empty for sub-rows) -->
              <td
                v-for="column in materialColumns"
                :key="`${row.row_id}-vp-${vp.job}-mat-${column}`"
                class="mat-cell mat-cell--empty"
              />
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.orders-overview {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.orders-overview__toolbar {
  display: flex;
  flex-wrap: nowrap;
  align-items: end;
  gap: 6px;
  padding: 4px var(--pad);
  border-bottom: 1px solid var(--b2);
}

.orders-overview__field {
  min-width: 0;
}

.orders-overview__field--date {
  width: 110px;
  flex-shrink: 0;
}

.orders-overview__field--customer {
  min-width: 120px;
  max-width: 200px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.orders-overview__field--search {
  min-width: 100px;
  max-width: 180px;
  flex: 1;
}

.filter-label {
  font-size: var(--fsm);
  font-weight: 500;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  user-select: none;
}

.filter-select-wrap {
  position: relative;
}

.filter-select {
  width: 100%;
  height: 28px;
  padding: 0 24px 0 8px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  font-family: var(--font);
  outline: none;
  appearance: none;
  cursor: pointer;
  transition: border-color 120ms var(--ease);
}
.filter-select:focus {
  border-color: var(--b3);
}
.filter-select option {
  background: var(--ground);
  color: var(--t1);
}

.filter-select-arrow {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--t4);
  font-size: 10px;
  pointer-events: none;
}

.orders-overview__refresh {
  min-height: 26px;
  padding: 4px 10px;
  font-size: var(--fss);
  flex-shrink: 0;
}

.orders-overview__col-btn {
  min-height: 26px;
  padding: 4px 10px;
  font-size: var(--fss);
  flex-shrink: 0;
}

.orders-overview__state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--t3);
}

.orders-overview__state--error {
  color: var(--err);
}

.orders-overview__table-wrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

/* ─── Table ─────────────────────────────────────────────────────── */
.orders-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  min-width: 100%;
}

.orders-table th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: var(--ground);
  color: var(--t3);
  font-size: var(--fss);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  border-bottom: 1px solid var(--b2);
  padding: 6px 8px;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
}

.orders-table th.sortable {
  cursor: pointer;
  user-select: none;
}
.orders-table th.sortable:hover {
  color: var(--t1);
}

.orders-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--b1);
  font-size: var(--fs);
  color: var(--t2);
  white-space: nowrap;
}

.orders-table tbody tr {
  cursor: pointer;
}
.orders-table tbody tr:hover {
  background: var(--surface);
}

.r {
  text-align: right;
}

.c {
  text-align: center;
}

.mono {
  font-family: var(--mono);
}

/* ─── Truncation ────────────────────────────────────────────────── */
.cell-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 0;
}

/* ─── VP cell + expand ──────────────────────────────────────────── */
.vp-cell {
  min-width: 100px;
}

.vp-multi-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
  color: var(--link-group-blue);
  cursor: pointer;
}
.vp-multi-label--open {
  color: var(--t1);
}

.vp-expand-icon {
  font-size: 9px;
  color: var(--t4);
  width: 10px;
  text-align: center;
  flex-shrink: 0;
}

.vp-count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 3px;
  font-size: 10px;
  font-weight: 700;
  border-radius: 8px;
  background: rgba(59,130,246,0.2);
  color: var(--link-group-blue);
}

.row-expandable {
  cursor: pointer;
}
.row-expanded td {
  border-bottom-color: transparent;
}

/* ─── VP sub-rows ──────────────────────────────────────────────── */
.vp-sub-row {
  cursor: pointer;
  background: rgba(255,255,255,0.02);
}
.vp-sub-row:hover {
  background: rgba(59,130,246,0.06);
}
.vp-sub-row--selected {
  background: rgba(59,130,246,0.1);
}
.vp-sub-row--selected:hover {
  background: rgba(59,130,246,0.14);
}

.vp-sub-cell {
  padding: 3px 8px 3px 32px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: var(--fsm);
}

.vp-sub-job {
  font-weight: 600;
  color: var(--t1);
}
.vp-sub-stat {
  font-size: 10px;
  font-weight: 700;
  color: var(--t3);
  padding: 0 3px;
  border-radius: 2px;
  background: rgba(255,255,255,0.06);
}
.vp-sub-qty {
  color: var(--t2);
  font-variant-numeric: tabular-nums;
}
.vp-sub-date {
  color: var(--t3);
  font-variant-numeric: tabular-nums;
}

/* ─── Operation columns ─────────────────────────────────────────── */
.op-col {
  width: 56px;
  text-align: center;
}

.op-cell {
  text-align: center;
  font-size: var(--fss);
  border-radius: 3px;
}

.op-cell--done {
  background: rgba(52,211,153,0.15);
  color: var(--ok);
}

.op-cell--progress {
  background: rgba(59,130,246,0.15);
  color: var(--link-group-blue);
}

.op-cell--idle {
  background: transparent;
}

.op-cell--empty {
  color: var(--t4);
}

/* ─── Material columns ─────────────────────────────────────────── */
.mat-col {
  width: 72px;
  text-align: center;
}

.mat-cell {
  text-align: center;
  font-size: var(--fss);
  border-radius: 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 72px;
}

.mat-cell--done {
  background: rgba(52,211,153,0.15);
  color: var(--ok);
}

.mat-cell--idle {
  background: transparent;
}

.mat-cell--empty {
  color: var(--t4);
}

/* ─── Material ready column ────────────────────────────────────── */
.orders-table td.mat-ready--yes {
  color: var(--ok, #34d399);
}
.orders-table td.mat-ready--no {
  color: var(--err, #f87171);
}

/* ─── Row number ────────────────────────────────────────────────── */
.row-num {
  text-align: right;
  color: var(--t4);
  font-size: var(--fss);
}

/* ─── Tier column ───────────────────────────────────────────────── */
.q-tier-col {
  text-align: center;
}
.q-tier-cell {
  text-align: center;
}
.q-tier-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  padding: 0 2px;
  line-height: 1;
}
.q-tier-na {
  color: var(--t4);
}

/* ─── Focused row (cross-tile link) ─────────────────────────────── */
.row-focused td {
  background: rgba(59,130,246,0.12);
}
.orders-table tbody tr.row-focused:hover td {
  background: rgba(59,130,246,0.18);
}

/* ─── Hot / urgent rows ─────────────────────────────────────────── */
.row-hot td {
  background: rgba(229,57,53,0.07);
}
.row-hot.row-focused td {
  background: rgba(229,57,53,0.15);
}
.row-urgent td {
  background: rgba(255,193,7,0.07);
}
.row-urgent.row-focused td {
  background: rgba(255,193,7,0.15);
}
/* ─── Resize grip ───────────────────────────────────────────────── */
.resize-grip {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  cursor: col-resize;
  background: transparent;
  transition: background 120ms var(--ease);
  z-index: 3;
}
.resize-grip:hover {
  background: var(--b2);
}
.resize-grip--active {
  background: var(--red, #e53935);
}

/* ─── Column visibility dropdown ────────────────────────────────── */
.col-dropdown-wrap {
  position: relative;
  flex-shrink: 0;
}

.col-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 20;
  margin-top: 4px;
  padding: 6px 0;
  min-width: 150px;
  max-height: 320px;
  overflow-y: auto;
  background: var(--ground);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  box-shadow: 0 4px 12px rgba(0,0,0,0.25);
}

.col-dropdown__item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  font-size: var(--fs);
  color: var(--t2);
  cursor: pointer;
  white-space: nowrap;
  user-select: none;
}
.col-dropdown__item:hover {
  background: var(--surface);
}
.col-dropdown__item input[type="checkbox"] {
  accent-color: var(--link-group-blue);
}

/* ─── Badge ─────────────────────────────────────────────────────── */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  font-size: var(--fss);
  color: var(--t3);
  background: rgba(255,255,255,0.06);
  border-radius: 10px;
  white-space: nowrap;
  flex-shrink: 0;
  align-self: center;
}

/* ─── SWR revalidating indicator ───────────────────────────────── */
.swr-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--link-group-blue, #3b82f6);
  margin-left: 4px;
  vertical-align: middle;
  animation: swr-pulse 1.2s ease-in-out infinite;
}
@keyframes swr-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
