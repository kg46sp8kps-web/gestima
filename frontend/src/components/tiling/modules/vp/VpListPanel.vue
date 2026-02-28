<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import { Search, RefreshCw } from 'lucide-vue-next'
import { useWorkshopStore } from '@/stores/workshop'
import { useCatalogStore } from '@/stores/catalog'
import type { ContextGroup } from '@/types/workspace'
import type { VpListItem } from '@/types/vp'
import Spinner from '@/components/ui/Spinner.vue'
import Input from '@/components/ui/Input.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const workshop = useWorkshopStore()
const catalog = useCatalogStore()

const searchVal = ref('')
const scrollContainerRef = ref<HTMLElement | null>(null)
const ROW_HEIGHT = 30

// Status filter — multi-select toggle
const activeStats = ref<Set<string>>(new Set(['R', 'F']))

const STAT_TABS = [
  { key: 'R', label: 'Released', color: 'ok' },
  { key: 'F', label: 'Firm', color: 'w' },
  { key: 'S', label: 'Sched.', color: 'blue' },
  { key: 'W', label: 'Waiting', color: 'o' },
] as const

function toggleStat(key: string) {
  const s = new Set(activeStats.value)
  if (s.has(key)) {
    if (s.size > 1) s.delete(key) // keep at least 1
  } else {
    s.add(key)
  }
  activeStats.value = s
  doFetch()
}

// Stat counts from loaded data
const statCounts = computed(() => {
  const counts: Record<string, number> = { R: 0, F: 0, S: 0, W: 0 }
  for (const vp of workshop.vpListItems) {
    const s = (vp.job_stat || 'R').toUpperCase()
    if (s in counts) counts[s] = (counts[s] ?? 0) + 1
  }
  return counts
})

// Focused item
const focusedItem = computed(() => catalog.getFocusedItem(props.ctx))

// Search debounce
let searchTimer: ReturnType<typeof setTimeout>
watch(searchVal, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => doFetch(), 300)
})

function doFetch() {
  const stat = Array.from(activeStats.value).join(',')
  void workshop.fetchVpList({
    stat,
    search: searchVal.value || undefined,
  })
}

function onRefresh() {
  workshop.vpListLastFetched = null
  doFetch()
}

// Items to display (already filtered server-side)
const displayItems = computed(() => workshop.vpListItems)

// Virtual scroll
const virtualizer = useVirtualizer(computed(() => ({
  count: displayItems.value.length,
  getScrollElement: () => scrollContainerRef.value,
  estimateSize: () => ROW_HEIGHT,
  overscan: 10,
})))

const totalSize = computed(() => virtualizer.value.getTotalSize())
const virtualRows = computed(() => virtualizer.value.getVirtualItems())

const isLoading = computed(() => workshop.vpListLoading && workshop.vpListItems.length === 0)

function selectVp(vp: VpListItem) {
  catalog.focusItem({ type: 'vp', number: vp.job }, props.ctx)
}

function statDotClass(stat: string): string {
  switch (stat.toUpperCase()) {
    case 'R': return 'pd ok'
    case 'F': return 'pd w'
    case 'S': return 'pd blue'
    default: return 'pd o'
  }
}

function fmtProgress(vp: VpListItem): string {
  const done = vp.qty_complete ?? 0
  const rel = vp.qty_released ?? 0
  return `${done}/${rel}`
}

// On mount — fetch if stale + auto-select first
onMounted(async () => {
  const stat = Array.from(activeStats.value).join(',')
  await workshop.fetchVpListIfStale({ stat }, 60000)
  // Auto-select first VP if nothing focused
  if (!focusedItem.value && displayItems.value.length > 0) {
    selectVp(displayItems.value[0]!)
  }
})
</script>

<template>
  <div class="plist-root">
    <!-- Search + refresh -->
    <div class="srch-w">
      <div class="srch-wrap">
        <Search class="srch-ico" :size="11" aria-hidden="true" />
        <Input
          v-model="searchVal"
          bare
          class="srch"
          placeholder="Hledat VP..."
        />
        <button
          v-if="searchVal"
          class="icon-btn srch-clr"
          @click="searchVal = ''; doFetch()"
        >&times;</button>
      </div>
      <button class="icon-btn icon-btn-sm" title="Obnovit" @click="onRefresh">
        <RefreshCw :size="16" />
      </button>
    </div>

    <!-- Status filter tabs (multi-select) -->
    <div class="ptabs">
      <button
        v-for="st in STAT_TABS"
        :key="st.key"
        :class="['ptab', activeStats.has(st.key) ? 'on' : '']"
        @click="toggleStat(st.key)"
      >
        {{ st.label }}
        <span class="n">{{ statCounts[st.key] }}</span>
      </button>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="plist-state">
      <Spinner size="sm" />
    </div>

    <!-- Empty -->
    <div v-else-if="displayItems.length === 0" class="plist-state">
      <span class="empty-hint">{{ searchVal ? 'Žádný VP nevyhovuje hledání' : 'Žádné výrobní příkazy' }}</span>
    </div>

    <!-- Virtual list -->
    <div v-else ref="scrollContainerRef" class="item-scroll">
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
          <div
            :class="['pi', { sel: focusedItem?.type === 'vp' && focusedItem.number === displayItems[vrow.index]?.job }]"
            @click="selectVp(displayItems[vrow.index]!)"
          >
            <span class="pn">{{ displayItems[vrow.index]?.job }}</span>
            <span class="pi-item">{{ displayItems[vrow.index]?.item || '' }}</span>
            <span class="pm">{{ displayItems[vrow.index]?.description || '' }}</span>
            <span :class="statDotClass(displayItems[vrow.index]?.job_stat || 'R')" />
            <span class="pi-prog">{{ fmtProgress(displayItems[vrow.index]!) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Revalidating indicator -->
    <div v-if="workshop.vpListIsRevalidating" class="load-more-bar">
      <Spinner size="sm" :inline="true" /> Aktualizuji...
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

/* Search row */
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

/* Filter tabs */
.ptabs {
  display: flex;
  gap: 1px;
  padding: 3px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
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

/* States */
.plist-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.empty-hint { font-size: var(--fs); color: var(--t4); }

/* Virtual scroll */
.item-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

/* Row */
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

/* Job number */
.pn {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t1);
  width: 120px;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--mono, monospace);
}

/* Item/article */
.pi-item {
  font-size: var(--fs);
  color: var(--t3);
  width: 90px;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Description */
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
.pd.ok   { background: var(--ok); }
.pd.w    { background: var(--warn); }
.pd.blue { background: var(--link); }
.pd.o    { background: var(--t4); }

/* Progress text */
.pi-prog {
  font-size: var(--fsm);
  color: var(--t4);
  font-family: var(--mono, monospace);
  white-space: nowrap;
  flex-shrink: 0;
  min-width: 50px;
  text-align: right;
}

/* Revalidating bar */
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
