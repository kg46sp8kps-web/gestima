<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import { Search, RefreshCw } from 'lucide-vue-next'
import { usePartsStore } from '@/stores/parts'
import { useMaterialItemsStore } from '@/stores/materialItems'
import { useCatalogStore } from '@/stores/catalog'
import type { ContextGroup } from '@/types/workspace'
import type { Part, PartStatus } from '@/types/part'
import type { MaterialItem } from '@/types/material-item'
import Spinner from '@/components/ui/Spinner.vue'
import Input from '@/components/ui/Input.vue'

type ListItem =
  | { kind: 'part';     data: Part }
  | { kind: 'material'; data: MaterialItem }

type TypeFilter = 'all' | 'parts' | 'materials'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()
const matItems = useMaterialItemsStore()
const catalog = useCatalogStore()

const searchVal = ref('')
const typeFilter = ref<TypeFilter>('all')
const scrollContainerRef = ref<HTMLElement | null>(null)

const ROW_HEIGHT = 30

const SHAPE_LABELS: Record<string, string> = {
  round_bar:     'Kulatina',
  square_bar:    'Čtyřhran',
  flat_bar:      'Plochá ocel',
  hexagonal_bar: 'Šestihran',
  plate:         'Deska',
  tube:          'Trubka',
  casting:       'Odlitek',
  forging:       'Výkovek',
}

// ─── Material filters ───
const matShapeFilter = ref('')
const matNormQuery = ref('')

// Rozměrové filtry — per-dimension refs
const dimDiaMin = ref(''); const dimDiaMax = ref('')
const dimWidthMin = ref(''); const dimWidthMax = ref('')
const dimThkMin = ref(''); const dimThkMax = ref('')
const dimWallMin = ref(''); const dimWallMax = ref('')

// Které rozměry zobrazit per shape
interface DimField { key: string; label: string; minRef: ReturnType<typeof ref<string>>; maxRef: ReturnType<typeof ref<string>> }
const shapeDims = computed<DimField[]>(() => {
  const sh = matShapeFilter.value
  if (sh === 'round_bar')     return [{ key: 'dia', label: 'Průměr', minRef: dimDiaMin, maxRef: dimDiaMax }]
  if (sh === 'hexagonal_bar') return [{ key: 'width', label: 'Šířka SW', minRef: dimWidthMin, maxRef: dimWidthMax }]
  if (sh === 'square_bar')    return [{ key: 'width', label: 'Strana', minRef: dimWidthMin, maxRef: dimWidthMax }, { key: 'thk', label: 'Tloušťka', minRef: dimThkMin, maxRef: dimThkMax }]
  if (sh === 'flat_bar')      return [{ key: 'width', label: 'Šířka', minRef: dimWidthMin, maxRef: dimWidthMax }, { key: 'thk', label: 'Tloušťka', minRef: dimThkMin, maxRef: dimThkMax }]
  if (sh === 'plate')         return [{ key: 'width', label: 'Šířka', minRef: dimWidthMin, maxRef: dimWidthMax }, { key: 'thk', label: 'Tloušťka', minRef: dimThkMin, maxRef: dimThkMax }]
  if (sh === 'tube')          return [{ key: 'dia', label: 'Průměr', minRef: dimDiaMin, maxRef: dimDiaMax }, { key: 'wall', label: 'Stěna', minRef: dimWallMin, maxRef: dimWallMax }]
  return []
})

// ─── Search — server-side pro parts, pro materials přes matItems.search ───
let searchTimer: ReturnType<typeof setTimeout>
watch(searchVal, (val) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    parts.search = val
    void parts.fetchParts(true)
    matItems.search = val
    void matItems.fetchItems(true)
  }, 300)
})

// ─── Status filter watcher ───
watch(() => parts.statusFilter, () => void parts.fetchParts(true))

// ─── Material filter watchers — sjednocený debounce ───
let matFilterTimer: ReturnType<typeof setTimeout>

function parseNum(v: string): number | undefined {
  const n = parseFloat(v)
  return Number.isFinite(n) ? n : undefined
}

function syncMatFiltersAndFetch() {
  clearTimeout(matFilterTimer)
  matFilterTimer = setTimeout(() => {
    matItems.shapeFilter = matShapeFilter.value
    matItems.normQuery = matNormQuery.value
    matItems.diameterMin = parseNum(dimDiaMin.value)
    matItems.diameterMax = parseNum(dimDiaMax.value)
    matItems.widthMin = parseNum(dimWidthMin.value)
    matItems.widthMax = parseNum(dimWidthMax.value)
    matItems.thicknessMin = parseNum(dimThkMin.value)
    matItems.thicknessMax = parseNum(dimThkMax.value)
    matItems.wallThicknessMin = parseNum(dimWallMin.value)
    matItems.wallThicknessMax = parseNum(dimWallMax.value)
    void matItems.fetchItems(true)
  }, 250)
}

// Při změně tvaru vyčistit rozměry
watch(matShapeFilter, () => {
  dimDiaMin.value = ''; dimDiaMax.value = ''
  dimWidthMin.value = ''; dimWidthMax.value = ''
  dimThkMin.value = ''; dimThkMax.value = ''
  dimWallMin.value = ''; dimWallMax.value = ''
  syncMatFiltersAndFetch()
})
watch(matNormQuery, syncMatFiltersAndFetch)
watch([dimDiaMin, dimDiaMax, dimWidthMin, dimWidthMax, dimThkMin, dimThkMax, dimWallMin, dimWallMax], syncMatFiltersAndFetch)

// ─── Unified display list ───
const displayItems = computed<ListItem[]>(() => {
  if (typeFilter.value === 'parts')
    return parts.items.map((p) => ({ kind: 'part' as const, data: p }))
  if (typeFilter.value === 'materials')
    return matItems.items.map((m) => ({ kind: 'material' as const, data: m }))
  return [
    ...parts.items.map((p) => ({ kind: 'part' as const, data: p })),
    ...matItems.items.map((m) => ({ kind: 'material' as const, data: m })),
  ]
})

// ─── TanStack Virtual ───
const virtualizer = useVirtualizer({
  get count() { return displayItems.value.length },
  getScrollElement: () => scrollContainerRef.value,
  estimateSize: () => ROW_HEIGHT,
  overscan: 10,
})

const virtualRows = computed(() => virtualizer.value.getVirtualItems())
const totalSize = computed(() => virtualizer.value.getTotalSize())

// ─── Infinite scroll ───
function onScroll() {
  if (!scrollContainerRef.value) return
  const el = scrollContainerRef.value
  if (el.scrollHeight - el.scrollTop - el.clientHeight > 300) return

  if (typeFilter.value !== 'materials' && parts.hasMore && !parts.loadingMore)
    void parts.loadMoreParts()
  else if (typeFilter.value !== 'parts' && matItems.hasMore && !matItems.loadingMore)
    void matItems.loadMoreItems()
}

// ─── Loading state — jen při prvním načítání ───
const isLoading = computed(() =>
  (typeFilter.value !== 'materials' && parts.initialLoading) ||
  (typeFilter.value !== 'parts' && matItems.initialLoading),
)

// ─── Selected item ───
const focusedItem = computed(() => catalog.getFocusedItem(props.ctx))

function selectPart(p: Part) {
  catalog.focusItem({ type: 'part', number: p.part_number }, props.ctx)
}

function selectMaterial(m: MaterialItem) {
  catalog.focusItem({ type: 'material', number: m.material_number }, props.ctx)
}

function dotClass(status: string): string {
  if (status === 'active') return 'pd ok'
  if (status === 'draft') return 'pd w'
  if (status === 'archived') return 'pd e'
  return 'pd o'
}

function onRefresh() {
  void parts.fetchParts(true)
  void matItems.fetchItems(true)
}

// ─── Lifecycle ───
onMounted(async () => {
  if (!parts.loaded) await parts.fetchParts()
  if (!matItems.loaded) await matItems.fetchItems()
  // Auto-select first part if nothing is focused in this context yet
  if (!catalog.getFocusedItem(props.ctx) && parts.items[0]) {
    catalog.focusItem({ type: 'part', number: parts.items[0].part_number }, props.ctx)
  }
})

onUnmounted(() => {
  searchVal.value = ''
  parts.search = ''
  matItems.search = ''
  matItems.shapeFilter = ''
  matItems.normQuery = ''
  typeFilter.value = 'all'
})
</script>

<template>
  <div class="plist-root">
    <!-- Search + actions -->
    <div class="srch-w">
      <div class="srch-wrap">
        <Search class="srch-ico" :size="11" aria-hidden="true" />
        <Input
          v-model="searchVal"
          bare
          class="srch"
          placeholder="Hledat..."
          testid="parts-search"
        />
        <button
          v-if="searchVal"
          class="icon-btn srch-clr"
          data-testid="parts-search-clear"
          @click="searchVal = ''; parts.search = ''; matItems.search = ''; void parts.fetchParts(true); void matItems.fetchItems(true)"
        >×</button>
      </div>
      <button class="icon-btn icon-btn-sm" title="Obnovit" data-testid="parts-refresh" @click="onRefresh">
        <RefreshCw :size="16" />
      </button>
    </div>

    <!-- Type filter tabs — Vše / Díly / Polotovary -->
    <div class="ptabs">
      <button :class="['ptab', typeFilter === 'all' ? 'on' : '']" data-testid="type-filter-all" @click="typeFilter = 'all'">
        Vše
      </button>
      <button :class="['ptab', typeFilter === 'parts' ? 'on' : '']" data-testid="type-filter-parts" @click="typeFilter = 'parts'">
        Díly <span class="n">{{ parts.total }}</span>
      </button>
      <button :class="['ptab', typeFilter === 'materials' ? 'on' : '']" data-testid="type-filter-materials" @click="typeFilter = 'materials'">
        Polotovary <span class="n">{{ matItems.total }}</span>
      </button>
    </div>

    <!-- Status filter tabs (pouze při zobrazení dílů) -->
    <div v-if="typeFilter !== 'materials'" class="ptabs ptabs-sub">
      <button :class="['ptab', parts.statusFilter === '' ? 'on' : '']" data-testid="filter-all" @click="parts.statusFilter = ''">
        Vše
      </button>
      <button :class="['ptab', parts.statusFilter === 'active' ? 'on' : '']" data-testid="filter-active" @click="parts.statusFilter = 'active' as PartStatus">Aktivní</button>
      <button :class="['ptab', parts.statusFilter === 'draft' ? 'on' : '']" data-testid="filter-draft" @click="parts.statusFilter = 'draft' as PartStatus">Rozpr.</button>
      <button :class="['ptab', parts.statusFilter === 'archived' ? 'on' : '']" data-testid="filter-archived" @click="parts.statusFilter = 'archived' as PartStatus">Arch.</button>
    </div>

    <!-- Material filters (pouze při zobrazení polotovarů) -->
    <div v-if="typeFilter === 'materials'" class="mat-filters">
      <select v-model="matShapeFilter" class="mat-sel" data-testid="mat-shape-filter">
        <option value="">Tvar: Vše</option>
        <option v-for="(label, key) in SHAPE_LABELS" :key="key" :value="key">{{ label }}</option>
      </select>
      <input
        v-model="matNormQuery"
        class="mat-inp"
        placeholder="Norma (W.Nr/EN/ČSN)"
        data-testid="mat-norm-input"
      />
      <template v-for="dim in shapeDims" :key="dim.key">
        <div class="dim-range">
          <span class="dim-lbl">{{ dim.label }}:</span>
          <input v-model="dim.minRef.value" class="dim-inp" type="number" placeholder="od" :data-testid="`mat-${dim.key}-min`" />
          <span class="dim-sep">–</span>
          <input v-model="dim.maxRef.value" class="dim-inp" type="number" placeholder="do" :data-testid="`mat-${dim.key}-max`" />
        </div>
      </template>
    </div>

    <!-- První načítání — spinner blokující -->
    <div v-if="isLoading" class="plist-state">
      <Spinner size="sm" />
    </div>

    <!-- Prázdný stav -->
    <div v-else-if="displayItems.length === 0" class="plist-state">
      <span class="empty-hint">{{ searchVal ? 'Žádná položka nevyhovuje hledání' : 'Žádné položky' }}</span>
    </div>

    <!-- Virtuální seznam -->
    <div v-else ref="scrollContainerRef" class="item-scroll" @scroll="onScroll">
      <div :style="{ height: `${totalSize}px`, position: 'relative' }">
        <div
          v-for="vrow in virtualRows"
          :key="String(vrow.key)"
          :style="{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            transform: `translateY(${vrow.start}px)`,
            height: `${ROW_HEIGHT}px`,
          }"
        >
          <!-- Part řádek -->
          <template v-if="displayItems[vrow.index]?.kind === 'part'">
            <div
              :class="['pi', { sel: focusedItem?.type === 'part' && focusedItem.number === (displayItems[vrow.index]?.data as Part).part_number }]"
              :data-testid="`part-row-${(displayItems[vrow.index]?.data as Part).part_number}`"
              @click="selectPart(displayItems[vrow.index]?.data as Part)"
            >
              <span class="pn">{{ (displayItems[vrow.index]?.data as Part).article_number || '—' }}</span>
              <span class="pm">{{ (displayItems[vrow.index]?.data as Part).name || '—' }}</span>
              <span :class="dotClass((displayItems[vrow.index]?.data as Part).status)" />
            </div>
          </template>

          <!-- Material řádek -->
          <template v-else-if="displayItems[vrow.index]?.kind === 'material'">
            <div
              :class="['pi pi-mat', { sel: focusedItem?.type === 'material' && focusedItem.number === (displayItems[vrow.index]?.data as MaterialItem).material_number }]"
              :data-testid="`material-row-${(displayItems[vrow.index]?.data as MaterialItem).material_number}`"
              @click="selectMaterial(displayItems[vrow.index]?.data as MaterialItem)"
            >
              <span class="pn">{{ (displayItems[vrow.index]?.data as MaterialItem).material_number }}</span>
              <span class="pm">{{ (displayItems[vrow.index]?.data as MaterialItem).name }}</span>
              <span class="badge">{{ SHAPE_LABELS[(displayItems[vrow.index]?.data as MaterialItem).shape] ?? (displayItems[vrow.index]?.data as MaterialItem).shape }}</span>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- Load-more bar — informační, neblokující -->
    <div v-if="parts.loadingMore || matItems.loadingMore" class="load-more-bar">
      <Spinner size="sm" :inline="true" /> Načítám další...
    </div>
  </div>
</template>

<style scoped>
.plist-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* ─── Search row ─── */
.srch-w {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.srch-wrap {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}
.srch-ico {
  position: absolute;
  left: 7px;
  width: 11px;
  height: 11px;
  color: var(--t4);
  pointer-events: none;
}
.srch { width: 100%; padding-left: 24px; }
.srch-clr {
  position: absolute;
  right: 4px;
  font-size: var(--fsh);
  line-height: 1;
  padding: 0 3px;
}

/* ─── Filter tabs ─── */
.ptabs {
  display: flex;
  gap: 1px;
  padding: 3px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.ptabs-sub {
  padding: 2px var(--pad);
  background: rgba(255,255,255,0.01);
}
.ptab {
  padding: 3px 7px;
  font-size: var(--fsm);
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
.n {
  font-size: var(--fsm);
  color: var(--t4);
  padding: 1px 4px;
  background: var(--b1);
  border-radius: var(--rs);
}

/* ─── Material filters ─── */
.mat-filters {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
  flex-wrap: wrap;
}
.mat-sel {
  font-size: var(--fsm);
  font-family: var(--font);
  padding: 2px 4px;
  border: 1px solid var(--b1);
  border-radius: var(--rs);
  background: var(--bg);
  color: var(--t2);
  max-width: 120px;
}
.mat-inp {
  font-size: var(--fsm);
  font-family: var(--font);
  padding: 2px 6px;
  border: 1px solid var(--b1);
  border-radius: var(--rs);
  background: var(--bg);
  color: var(--t2);
  flex: 1;
  min-width: 80px;
  max-width: 140px;
}
.dim-range {
  display: flex;
  align-items: center;
  gap: 2px;
}
.dim-lbl {
  font-size: var(--fsm);
  color: var(--t4);
  white-space: nowrap;
}
.dim-inp {
  font-size: var(--fsm);
  font-family: var(--font);
  padding: 2px 4px;
  border: 1px solid var(--b1);
  border-radius: var(--rs);
  background: var(--bg);
  color: var(--t2);
  width: 48px;
}
.dim-sep {
  font-size: var(--fsm);
  color: var(--t4);
}
/* Remove number input spinners */
.dim-inp::-webkit-inner-spin-button,
.dim-inp::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.dim-inp[type="number"] { -moz-appearance: textfield; }

/* ─── States ─── */
.plist-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.empty-hint { font-size: var(--fs); color: var(--t4); }

/* ─── Virtuální scroll container ─── */
.item-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

/* ─── Řádek položky ─── */
.pi {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 var(--pad);
  cursor: pointer;
  position: relative;
  height: 30px;
  border-bottom: 1px solid rgba(255,255,255,0.025);
  transition: background 80ms var(--ease);
  box-sizing: border-box;
}
.pi:hover { background: var(--b1); }
.pi.sel { background: rgba(229,57,53,0.06); }
.pi.sel::after {
  content: '';
  position: absolute;
  left: 0;
  top: 2px;
  bottom: 2px;
  width: 2px;
  background: var(--red);
  border-radius: 0 1px 1px 0;
}

/* Číslo položky — fixní šířka */
.pn {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t1);
  width: 110px;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Název */
.pm {
  font-size: var(--fs);
  color: var(--t3);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Status dot */
.pd {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}
.pd.ok { background: var(--ok); }
.pd.w  { background: var(--warn); }
.pd.e  { background: var(--err); }
.pd.o  { background: var(--t4); }

/* ─── Load-more bar ─── */
.load-more-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px var(--pad);
  font-size: var(--fsm);
  color: var(--t4);
  border-top: 1px solid var(--b1);
}
</style>
