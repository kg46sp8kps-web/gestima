<script setup lang="ts">
import { ref, computed } from 'vue'
import { getPurchasePrices, applyPurchasePrices, refreshPurchasePriceCache } from '@/api/purchase-prices'
import type { PurchasePriceAnalysisResponse, PriceCategoryAnalysis, ApplyPriceRequest } from '@/types/purchase-prices'
import { useUiStore } from '@/stores/ui'
import { RefreshCw, Download, AlertTriangle, ChevronDown, ChevronRight } from 'lucide-vue-next'
import InforPriceDistribution from './InforPriceDistribution.vue'
import { ICON_SIZE } from '@/config/design'

const props = defineProps<{ isConnected: boolean }>()
const uiStore = useUiStore()
const yearFrom = ref(2024)
const yearTo = ref(2025)
const loading = ref(false)
const analysis = ref<PurchasePriceAnalysisResponse | null>(null)
const showUnmatched = ref(false)
const selected = ref<Set<number>>(new Set())
const expandedRow = ref<number | null>(null)

function toggleExpand(catId: number) {
  expandedRow.value = expandedRow.value === catId ? null : catId
}

const fmtPrice = (n: number | null) => n == null ? '-' : n.toLocaleString('cs-CZ', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const fmtKg = (n: number) => n.toLocaleString('cs-CZ', { maximumFractionDigits: 0 })
const fmtTime = (s: number) => s < 60 ? `${s.toFixed(1)}s` : `${(s / 60).toFixed(1)}m`

function toggleSelect(catId: number) {
  const s = new Set(selected.value)
  s.has(catId) ? s.delete(catId) : s.add(catId)
  selected.value = s
}
function toggleAll() {
  if (!analysis.value) return
  const eligible = analysis.value.categories.filter(c => c.tiers.every(t => t.sufficient_data))
  selected.value = selected.value.size === eligible.length ? new Set() : new Set(eligible.map(c => c.price_category_id))
}

async function analyze() {
  if (!props.isConnected) return uiStore.showError('Nejste pripojeni k Infor ION API')
  loading.value = true
  selected.value = new Set()
  try {
    analysis.value = await getPurchasePrices(yearFrom.value, yearTo.value)
    uiStore.showSuccess(`Analyzovano ${analysis.value.total_po_lines_matched} objednavek za ${analysis.value.date_range}`)
  } catch (error: unknown) {
    uiStore.showError((error as Error).message || 'Chyba analyzy')
  } finally { loading.value = false }
}

async function applySelected() {
  if (!analysis.value || selected.value.size === 0) return
  const cats = analysis.value.categories.filter(c => selected.value.has(c.price_category_id))
  const updates: ApplyPriceRequest[] = cats.map(c => ({
    category_id: c.price_category_id,
    tier_updates: c.tiers.map(t => ({ tier_id: t.tier_id, new_price: t.avg_price_per_kg, version: t.current_tier_version }))
  }))
  try {
    await applyPurchasePrices(updates)
    uiStore.showSuccess(`Aplikovano ${updates.length} kategorii`)
    selected.value = new Set()
    await analyze()
  } catch (error: unknown) { uiStore.showError((error as Error).message || 'Chyba aplikace') }
}

async function refreshCache() {
  loading.value = true
  try {
    await refreshPurchasePriceCache(yearFrom.value)
    uiStore.showSuccess('Cache obnoven')
    await analyze()
  } catch (error: unknown) { uiStore.showError((error as Error).message || 'Chyba refresh') }
  finally { loading.value = false }
}

type SortKey = 'name' | 'po' | 'kg' | 'avg' | 'tier0' | 'tier1' | 'tier2'
const sortKey = ref<SortKey | null>(null)
const sortAsc = ref(true)

function toggleSort(key: SortKey) {
  if (sortKey.value === key) { sortAsc.value = !sortAsc.value }
  else { sortKey.value = key; sortAsc.value = true }
}
function sortIcon(key: SortKey) {
  if (sortKey.value !== key) return ''
  return sortAsc.value ? ' ▲' : ' ▼'
}

function getSortValue(cat: PriceCategoryAnalysis, key: SortKey): number | string {
  if (key === 'name') return cat.price_category_name
  if (key === 'po') return cat.total_po_lines
  if (key === 'kg') return cat.total_qty_received_kg
  if (key === 'avg') return cat.weighted_avg_price_per_kg
  const idx = key === 'tier0' ? 0 : key === 'tier1' ? 1 : 2
  return cat.tiers[idx]?.avg_price_per_kg ?? 0
}

const sortedCategories = computed(() => {
  if (!analysis.value) return []
  const cats = [...analysis.value.categories]
  if (!sortKey.value) return cats
  const k = sortKey.value
  const dir = sortAsc.value ? 1 : -1
  return cats.sort((a, b) => {
    const va = getSortValue(a, k), vb = getSortValue(b, k)
    if (typeof va === 'string') return dir * va.localeCompare(vb as string)
    return dir * ((va as number) - (vb as number))
  })
})

const eligibleCount = computed(() => analysis.value?.categories.filter(c => c.tiers.every(t => t.sufficient_data)).length || 0)
const allSelected = computed(() => selected.value.size > 0 && selected.value.size === eligibleCount.value)
const isEligible = (cat: PriceCategoryAnalysis) => cat.tiers.every(t => t.sufficient_data)
</script>

<template>
  <div class="root">
    <div class="toolbar">
      <label class="filter-label">Od:</label>
      <select v-model="yearFrom" class="year-select">
        <option :value="2024">2024</option><option :value="2025">2025</option><option :value="2026">2026</option>
      </select>
      <label class="filter-label">Do:</label>
      <select v-model="yearTo" class="year-select">
        <option :value="2024">2024</option><option :value="2025">2025</option><option :value="2026">2026</option>
      </select>
      <button class="btn-ghost" @click="analyze" :disabled="loading || !isConnected">Analyzovat</button>
      <button class="btn-ghost" @click="applySelected" :disabled="selected.size === 0">
        Aplikovat vybranych ({{ selected.size }})
      </button>
      <button class="btn-ghost" @click="refreshCache" :disabled="loading || !isConnected"><RefreshCw :size="ICON_SIZE.STANDARD" /></button>
      <span v-if="analysis?.cached" class="cached-badge">Cached</span>
      <span v-if="analysis" class="date-range">{{ analysis.date_range }}</span>
    </div>

    <div class="legend">
      <span><b>Tucne</b> = nakupni cena z Infor PO (vazeny prumer Kc/kg)</span>
      <span class="arrow">-></span>
      <span class="text-secondary">sede = aktualni cena v Gestima</span>
      <span class="diff-badge cheaper">-5%</span><span>= levnejsi nez Gestima</span>
      <span class="diff-badge expensive">+10%</span><span>= drazsi nez Gestima</span>
      <AlertTriangle :size="ICON_SIZE.SMALL" class="warning-icon" /><span>= malo dat (&lt;3 PO)</span>
    </div>

    <div v-if="loading" class="loading-state">Nacitani dat z Infor API...</div>
    <div v-else-if="analysis" class="results">
      <div class="summary-cards">
        <div class="card"><div class="card-label">PO radku</div><div class="card-value">{{ analysis.total_po_lines_fetched }}</div></div>
        <div class="card"><div class="card-label">Prirazeno</div><div class="card-value">{{ analysis.total_po_lines_matched }}</div></div>
        <div class="card"><div class="card-label">Neprirazeno</div><div class="card-value">{{ analysis.total_po_lines_unmatched }}</div></div>
        <div class="card"><div class="card-label">Materialu</div><div class="card-value">{{ analysis.unique_materials }}</div></div>
        <div class="card"><div class="card-label">Cas</div><div class="card-value">{{ fmtTime(analysis.fetch_time_seconds) }}</div></div>
      </div>

      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th class="col-check"><input type="checkbox" :checked="allSelected" @change="toggleAll" /></th>
              <th class="sortable" @click="toggleSort('name')">Kategorie{{ sortIcon('name') }}</th>
              <th>Tvar</th>
              <th class="sortable" @click="toggleSort('po')">PO{{ sortIcon('po') }}</th>
              <th class="sortable" @click="toggleSort('kg')">Nakoupeno kg{{ sortIcon('kg') }}</th>
              <th class="sortable" @click="toggleSort('avg')">Ø Kc/kg{{ sortIcon('avg') }}</th>
              <th v-for="i in Math.min(analysis.categories[0]?.tiers.length || 3, 3)" :key="i"
                  class="sortable" @click="toggleSort(('tier' + (i-1)) as SortKey)">
                Tier {{ i }}{{ sortIcon(('tier' + (i-1)) as SortKey) }}
                <span class="th-sub">Nakup -> Gestima Kc/kg</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <template v-for="cat in sortedCategories" :key="cat.price_category_id">
              <tr :class="{ 'row-selected': selected.has(cat.price_category_id) }">
                <td class="col-check">
                  <input type="checkbox" :checked="selected.has(cat.price_category_id)"
                         :disabled="!isEligible(cat)" @change="toggleSelect(cat.price_category_id)" />
                </td>
                <td class="clickable" @click="toggleExpand(cat.price_category_id)">
                  <div class="cat-name">{{ cat.price_category_name }}</div>
                  <div class="cat-group">{{ cat.material_group_name || '-' }}</div>
                </td>
                <td class="text-secondary">{{ cat.shape || '-' }}</td>
                <td class="text-right">{{ cat.total_po_lines }}</td>
                <td class="text-right font-mono">{{ fmtKg(cat.total_qty_received_kg) }} kg</td>
                <td class="text-right font-mono">{{ fmtPrice(cat.weighted_avg_price_per_kg) }} Kc</td>
                <td v-for="tier in cat.tiers.slice(0, 3)" :key="tier.tier_id" class="tier-cell">
                  <div class="tier-label-row">{{ tier.tier_label }}</div>
                  <div class="tier-content">
                    <span class="real-price" :title="'Nakupni cena z ' + tier.po_line_count + ' PO radku'">{{ fmtPrice(tier.avg_price_per_kg) }}</span>
                    <span class="arrow">-></span>
                    <span class="current-price" title="Aktualni cena v Gestima">{{ fmtPrice(tier.current_price) }}</span>
                    <span class="unit">Kc</span>
                    <span v-if="tier.diff_pct !== null" :class="['diff-badge', tier.diff_pct < 0 ? 'cheaper' : 'expensive']">
                      {{ tier.diff_pct > 0 ? '+' : '' }}{{ tier.diff_pct.toFixed(1) }}%
                    </span>
                    <AlertTriangle v-if="!tier.sufficient_data" :size="ICON_SIZE.SMALL" class="warning-icon" title="Malo dat (<3 PO radku)" />
                  </div>
                  <div class="tier-meta">{{ tier.po_line_count }} PO / {{ fmtKg(tier.total_qty_kg) }} kg</div>
                </td>
              </tr>
              <tr v-if="expandedRow === cat.price_category_id" class="expand-row">
                <td :colspan="6 + Math.min(cat.tiers.length, 3)">
                  <InforPriceDistribution :distribution="cat.weight_distribution" :tiers="cat.tiers"
                    :category-id="cat.price_category_id" @boundaries-applied="analyze" />
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <div v-if="analysis.unmatched.length > 0" class="unmatched-section">
        <button class="unmatched-toggle" @click="showUnmatched = !showUnmatched">
          <component :is="showUnmatched ? ChevronDown : ChevronRight" :size="ICON_SIZE.STANDARD" />
          Neprirazene ({{ analysis.unmatched.length }})
        </button>
        <div v-if="showUnmatched" class="unmatched-list">
          <div v-for="item in analysis.unmatched" :key="item.item" class="unmatched-item">
            <div class="ui-code">{{ item.item }}</div>
            <div class="ui-desc">{{ item.description }}</div>
            <div class="ui-reason">{{ item.reason }}</div>
            <div class="ui-cost">{{ fmtPrice(item.total_cost) }} Kc ({{ item.count }}x)</div>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="empty-state">
      <Download :size="ICON_SIZE.HERO" class="empty-icon" />
      <p>Zvolte obdobi a spuste analyzu nakupnich cen z Infor PO</p>
    </div>
  </div>
</template>

<style scoped>
.root { display: flex; flex-direction: column; height: 100%; gap: var(--space-4); padding: var(--space-4); background: var(--bg-base); }
.toolbar { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.filter-label { font-size: var(--text-xs); color: var(--text-secondary); }
.year-select { padding: var(--space-1) var(--space-2); font-size: var(--text-sm); background: var(--bg-input); border: 1px solid var(--border-default); border-radius: var(--radius-md); color: var(--text-primary); }
.cached-badge, .date-range { font-size: var(--text-xs); color: var(--text-tertiary); }
.cached-badge { padding: var(--space-1) var(--space-2); background: rgba(255,255,255,0.1); border-radius: var(--radius-sm); }
.date-range { margin-left: auto; }
.legend { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-xs); color: var(--text-secondary); padding: var(--space-2) var(--space-3); background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); flex-wrap: wrap; }
.results { display: flex; flex-direction: column; gap: var(--space-4); flex: 1; overflow: auto; }
.summary-cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--space-3); }
.card { padding: var(--space-3); background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: var(--radius-md); }
.card-label { font-size: var(--text-xs); color: var(--text-secondary); margin-bottom: var(--space-1); }
.card-value { font-size: var(--text-lg); font-family: var(--font-mono); color: var(--text-primary); }
.data-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.data-table th { padding: var(--space-2); text-align: left; font-weight: var(--font-medium); color: var(--text-secondary); border-bottom: 1px solid var(--border-default); background: var(--bg-surface); position: sticky; top: 0; white-space: nowrap; }
.data-table td { padding: var(--space-2); border-bottom: 1px solid var(--border-subtle); color: var(--text-body); }
.table-wrapper { overflow: auto; }
.sortable { cursor: pointer; user-select: none; }
.sortable:hover { color: var(--text-primary); }
.col-check { width: 32px; text-align: center; }
.cat-name { font-weight: var(--font-medium); color: var(--text-primary); }
.cat-group { font-size: var(--text-xs); color: var(--text-tertiary); }
.clickable { cursor: pointer; }
.clickable:hover .cat-name { text-decoration: underline; }
.row-selected { background: rgba(59,130,246,0.08); }
.tier-cell { min-width: 150px; }
.tier-label-row { font-size: var(--text-2xs); color: var(--text-tertiary); font-family: var(--font-mono); margin-bottom: var(--space-px); }
.tier-content { display: flex; align-items: center; gap: var(--space-1); font-size: var(--text-xs); font-family: var(--font-mono); }
.real-price { color: var(--text-primary); font-weight: var(--font-medium); }
.arrow, .unit, .tier-meta, .th-sub { color: var(--text-tertiary); }
.current-price { color: var(--text-secondary); }
.unit, .tier-meta, .th-sub { font-size: var(--text-2xs); }
.th-sub { display: block; font-weight: normal; }
.tier-meta { margin-top: var(--space-0\.5); }
.diff-badge { padding: var(--space-px) var(--space-1); border-radius: var(--radius-sm); font-size: var(--text-2xs); font-weight: var(--font-medium); }
.diff-badge.cheaper { background: rgba(34,197,94,0.15); color: rgb(34,197,94); }
.diff-badge.expensive { background: rgba(239,68,68,0.15); color: rgb(239,68,68); }
.warning-icon { color: var(--color-warning); }
.expand-row td { background: var(--bg-surface); padding: var(--space-3) !important; }
/* Unmatched & misc */
.unmatched-section { padding-top: var(--space-4); border-top: 1px solid var(--border-default); }
.unmatched-toggle { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-2); background: transparent; border: none; color: var(--text-primary); font-size: var(--text-sm); cursor: pointer; }
.unmatched-toggle:hover { color: var(--text-secondary); }
.unmatched-list { display: flex; flex-direction: column; gap: var(--space-2); margin-top: var(--space-3); }
.unmatched-item { display: grid; grid-template-columns: 140px 1fr 220px 120px; gap: var(--space-3); padding: var(--space-2); background: var(--bg-surface); border-radius: var(--radius-sm); font-size: var(--text-xs); }
.ui-code { font-family: var(--font-mono); color: var(--text-primary); }
.ui-desc, .text-secondary { color: var(--text-secondary); }
.ui-reason { color: var(--color-warning); }
.ui-cost { font-family: var(--font-mono); color: var(--text-primary); text-align: right; }
.empty-icon { color: var(--text-tertiary); }
.text-right { text-align: right; }
.font-mono { font-family: var(--font-mono); }
</style>
