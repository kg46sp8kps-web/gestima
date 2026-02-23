<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { usePartsStore } from '@/stores/parts'
import { useCatalogStore } from '@/stores/catalog'
import { useUiStore } from '@/stores/ui'
import * as materialsApi from '@/api/materials'
import type { ContextGroup } from '@/types/workspace'
import type { Part, PartStatus } from '@/types/part'
import type { MaterialItem } from '@/types/material-item'
import Spinner from '@/components/ui/Spinner.vue'

type TypeFilter = 'all' | 'parts' | 'materials'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()
const catalog = useCatalogStore()
const ui = useUiStore()

const searchVal = ref('')
const typeFilter = ref<TypeFilter>('all')

// ─── Materials state ───
const materialItems = ref<MaterialItem[]>([])
const materialsTotal = ref(0)
const materialsLoading = ref(false)

const SHAPE_LABELS: Record<string, string> = {
  round_bar:     'Kulatina',
  square_bar:    'Čtyřhran',
  flat_bar:      'Plochá ocel',
  hexagonal_bar: 'Šestihran',
  plate:         'Plech',
  tube:          'Trubka',
  casting:       'Odlitek',
  forging:       'Výkovek',
}

let searchTimer: ReturnType<typeof setTimeout>
function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    if (typeFilter.value !== 'materials') {
      parts.search = searchVal.value
      parts.fetchAll()
    }
  }, 300)
}

const filteredParts = computed(() => {
  const q = searchVal.value.toLowerCase().trim()
  if (!q) return parts.items
  return parts.items.filter(
    (p) =>
      p.part_number.toLowerCase().includes(q) ||
      (p.name ?? '').toLowerCase().includes(q) ||
      (p.article_number ?? '').toLowerCase().includes(q) ||
      (p.drawing_number ?? '').toLowerCase().includes(q),
  )
})

const filteredMaterials = computed(() => {
  const q = searchVal.value.toLowerCase().trim()
  if (!q) return materialItems.value
  return materialItems.value.filter(
    (m) =>
      m.material_number.toLowerCase().includes(q) ||
      m.name.toLowerCase().includes(q) ||
      m.code.toLowerCase().includes(q),
  )
})

const focusedItem = computed(() => catalog.getFocusedItem(props.ctx))

function selectPart(p: Part) {
  catalog.focusItem({ type: 'part', number: p.part_number }, props.ctx)
}

function selectMaterial(m: MaterialItem) {
  catalog.focusItem({ type: 'material', number: m.material_number }, props.ctx)
}

/** Returns CSS class for the 5px status dot — reference .pd pattern */
function dotClass(status: string): string {
  if (status === 'active') return 'pd ok'
  if (status === 'draft') return 'pd w'
  if (status === 'archived') return 'pd e'
  return 'pd o'
}

async function fetchMaterials() {
  if (materialsLoading.value) return
  materialsLoading.value = true
  try {
    const result = await materialsApi.getItems({ limit: 500 })
    materialItems.value = result.items
    materialsTotal.value = result.total
  } catch {
    ui.showError('Chyba při načítání polotovarů')
  } finally {
    materialsLoading.value = false
  }
}

onMounted(() => {
  if (!parts.hasParts) parts.fetchAll()
  fetchMaterials()
})

watch(
  () => parts.statusFilter,
  () => parts.fetchAll(),
)
</script>

<template>
  <div class="plist-root">
    <!-- Search + actions -->
    <div class="srch-w">
      <div class="srch-wrap">
        <svg class="srch-ico" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="6.5" cy="6.5" r="4" stroke="currentColor" stroke-width="1.5" />
          <path d="M10 10L13.5 13.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
        </svg>
        <input
          v-model="searchVal"
          class="srch"
          placeholder="Hledat..."
          data-testid="parts-search"
          @input="onSearchInput"
        />
        <button
          v-if="searchVal"
          class="icon-btn srch-clr"
          data-testid="parts-search-clear"
          @click="searchVal = ''; parts.search = ''; parts.fetchAll()"
        >×</button>
      </div>
      <button class="icon-btn icon-btn-sm" title="Obnovit" data-testid="parts-refresh" @click="parts.fetchAll(); fetchMaterials()">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M2.5 8a5.5 5.5 0 1 0 1-3.18M2.5 2v4h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
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
        Polotovary <span class="n">{{ materialsTotal }}</span>
      </button>
    </div>

    <!-- Status filter tabs (only when showing parts) -->
    <div v-if="typeFilter !== 'materials'" class="ptabs ptabs-sub">
      <button :class="['ptab', parts.statusFilter === '' ? 'on' : '']" data-testid="filter-all" @click="parts.statusFilter = ''">
        Vše
      </button>
      <button :class="['ptab', parts.statusFilter === 'active' ? 'on' : '']" data-testid="filter-active" @click="parts.statusFilter = 'active' as PartStatus">Aktivní</button>
      <button :class="['ptab', parts.statusFilter === 'draft' ? 'on' : '']" data-testid="filter-draft" @click="parts.statusFilter = 'draft' as PartStatus">Rozpr.</button>
      <button :class="['ptab', parts.statusFilter === 'archived' ? 'on' : '']" data-testid="filter-archived" @click="parts.statusFilter = 'archived' as PartStatus">Arch.</button>
    </div>

    <!-- Loading -->
    <div v-if="parts.loading || materialsLoading" class="plist-state">
      <Spinner size="sm" />
    </div>

    <!-- Empty -->
    <div v-else-if="typeFilter !== 'materials' && !filteredParts.length && typeFilter !== 'all'" class="plist-state">
      <span class="empty-hint">{{ searchVal ? 'Žádný díl nevyhovuje hledání' : 'Žádné díly' }}</span>
    </div>
    <div v-else-if="typeFilter === 'materials' && !filteredMaterials.length" class="plist-state">
      <span class="empty-hint">{{ searchVal ? 'Žádný polotovar nevyhovuje hledání' : 'Žádné polotovary' }}</span>
    </div>

    <!-- Unified list -->
    <ul v-else class="plist">
      <!-- Parts section -->
      <template v-if="typeFilter !== 'materials'">
        <li
          v-for="p in filteredParts"
          :key="`part-${p.part_number}`"
          :class="['pi', { sel: focusedItem?.type === 'part' && focusedItem.number === p.part_number }]"
          :data-testid="`part-row-${p.part_number}`"
          @click="selectPart(p)"
        >
          <span class="pn">{{ p.part_number }}</span>
          <span class="pm">{{ p.name || p.article_number || '—' }}</span>
          <span :class="dotClass(p.status)" />
        </li>
      </template>

      <!-- Materials section -->
      <template v-if="typeFilter !== 'parts'">
        <li
          v-for="m in filteredMaterials"
          :key="`mat-${m.material_number}`"
          :class="['pi pi-mat', { sel: focusedItem?.type === 'material' && focusedItem.number === m.material_number }]"
          :data-testid="`material-row-${m.material_number}`"
          @click="selectMaterial(m)"
        >
          <span class="pn">{{ m.material_number }}</span>
          <span class="pm">{{ m.name }}</span>
          <span class="mat-shape-badge">{{ SHAPE_LABELS[m.shape] ?? m.shape }}</span>
        </li>
      </template>
    </ul>

  </div>
</template>

<style scoped>
.plist-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* ─── Search row — reference .srch-w ─── */
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
.srch {
  width: 100%;
  height: 26px;
  padding: 0 20px 0 24px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t2);
  font-size: var(--fs);
  font-family: var(--font);
  outline: none;
  transition: border-color 120ms var(--ease), background 120ms var(--ease), color 120ms var(--ease);
}
.srch::placeholder { color: var(--t4); }
.srch:focus { border-color: var(--b3); background: rgba(255,255,255,0.07); color: var(--t1); }
/* search clear — positioned inside search wrap */
.srch-clr {
  position: absolute;
  right: 4px;
  font-size: var(--fsh);
  line-height: 1;
  padding: 0 3px;
}

/* ─── Filter tabs — reference .ptabs / .ptab ─── */
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
  font-size: var(--fsx);
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
/* Count badge inside tab */
.n {
  font-size: var(--fsm);
  color: var(--t4);
  padding: 1px 4px;
  background: var(--b1);
  border-radius: 2px;
}

/* ─── States ─── */
.plist-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.empty-hint { font-size: var(--fs); color: var(--t4); }

/* ─── Parts list — reference .plist / .pi ─── */
.plist {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  list-style: none;
  margin: 0;
  padding: 0;
}

.pi {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px var(--pad);
  cursor: pointer;
  position: relative;
  min-height: 28px;
  border-bottom: 1px solid rgba(255,255,255,0.025);
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

/* Part number — reference .pn */
.pn {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t1);
  min-width: 66px;
  flex-shrink: 0;
}

/* Part name — reference .pm */
.pm {
  font-size: var(--fs);
  color: var(--t3);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Status dot — reference .pd */
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

/* Material row badge */
.mat-shape-badge {
  font-size: var(--fsm);
  padding: 1px 5px;
  border-radius: var(--rs);
  background: var(--b1);
  color: var(--t3);
  white-space: nowrap;
  flex-shrink: 0;
}


</style>
