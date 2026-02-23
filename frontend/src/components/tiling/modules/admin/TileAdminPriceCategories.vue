<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { CheckIcon, XIcon } from 'lucide-vue-next'
import * as materialsApi from '@/api/materials'
import type { MaterialPriceCategory } from '@/types/admin-user'
import { formatNumber } from '@/utils/formatters'
import { useUiStore } from '@/stores/ui'
import Spinner from '@/components/ui/Spinner.vue'
import { ICON_SIZE_SM } from '@/config/design'

const cats = ref<MaterialPriceCategory[]>([])
const loading = ref(false)
const error = ref(false)
const search = ref('')
const ui = useUiStore()

interface CatDraft {
  name: string
  iso_group: string | null
  shape: string | null
  cutting_speed_turning: number | null
  cutting_speed_milling: number | null
  version: number
}

const editingId = ref<number | null>(null)
const editDraft = ref<CatDraft | null>(null)

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return cats.value
  return cats.value.filter(c =>
    c.code.toLowerCase().includes(q) ||
    c.name.toLowerCase().includes(q) ||
    (c.iso_group ?? '').toLowerCase().includes(q) ||
    (c.material_group?.name ?? '').toLowerCase().includes(q),
  )
})

async function load() {
  loading.value = true
  error.value = false
  try {
    cats.value = await materialsApi.getPriceCategories()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

function startEdit(c: MaterialPriceCategory) {
  editingId.value = c.id
  editDraft.value = {
    name: c.name,
    iso_group: c.iso_group,
    shape: c.shape,
    cutting_speed_turning: c.cutting_speed_turning,
    cutting_speed_milling: c.cutting_speed_milling,
    version: c.version,
  }
}

async function saveEdit() {
  const id = editingId.value
  const draft = editDraft.value
  if (!id || !draft) return
  editingId.value = null
  editDraft.value = null
  try {
    const updated = await materialsApi.updatePriceCategory(id, draft)
    const idx = cats.value.findIndex(c => c.id === id)
    if (idx !== -1) cats.value[idx] = updated
    ui.showSuccess('Kategorie uložena')
  } catch {
    ui.showError('Chyba při ukládání kategorie')
  }
}

function cancelEdit() {
  editingId.value = null
  editDraft.value = null
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') { e.preventDefault(); saveEdit() }
  if (e.key === 'Escape') { e.preventDefault(); cancelEdit() }
}

onMounted(load)
</script>

<template>
  <div class="tab-content">
    <div class="srch-bar">
      <input
        v-model="search"
        class="srch-inp"
        type="text"
        placeholder="Hledat kód, název, ISO skupinu…"
        data-testid="price-cats-search-input"
      />
      <span class="srch-count">{{ filtered.length }} / {{ cats.length }}</span>
    </div>

    <div v-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>
    <div v-else-if="!filtered.length" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">{{ search ? 'Žádné výsledky' : 'Žádné kategorie' }}</span>
    </div>
    <div v-else class="ot-wrap">
      <table class="ot">
        <thead>
          <tr>
            <th style="width:82px">Kód</th>
            <th>Název</th>
            <th style="width:55px">ISO sk.</th>
            <th style="width:65px">Tvar</th>
            <th>Skupina</th>
            <th class="r" style="width:78px">Vc soustr.</th>
            <th class="r" style="width:78px">Vc fréz.</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="c in filtered"
            :key="c.id"
            :data-testid="`price-cat-row-${c.id}`"
            :class="['row-clickable', { 'row-editing': editingId === c.id }]"
            @click="editingId !== c.id ? startEdit(c) : undefined"
            @keydown.capture="editingId === c.id ? onKeydown($event) : undefined"
          >
            <td class="t3">{{ c.code }}</td>
            <td>
              <template v-if="editingId === c.id && editDraft">
                <input
                  v-model="editDraft.name"
                  type="text"
                  class="ei ei-wide"
                  :data-testid="`price-cat-edit-name-${c.id}`"
                />
              </template>
              <template v-else>{{ c.name }}</template>
            </td>
            <td class="t4">
              <template v-if="editingId === c.id && editDraft">
                <input
                  v-model="editDraft.iso_group"
                  type="text"
                  class="ei ei-xs"
                  :data-testid="`price-cat-edit-iso-${c.id}`"
                />
              </template>
              <template v-else>{{ c.iso_group ?? '—' }}</template>
            </td>
            <td class="t4">
              <template v-if="editingId === c.id && editDraft">
                <input
                  v-model="editDraft.shape"
                  type="text"
                  class="ei ei-sm-text"
                  :data-testid="`price-cat-edit-shape-${c.id}`"
                />
              </template>
              <template v-else>{{ c.shape ?? '—' }}</template>
            </td>
            <td class="t4">{{ c.material_group?.name ?? '—' }}</td>
            <td class="r t4">
              <template v-if="editingId === c.id && editDraft">
                <input
                  v-model.number="editDraft.cutting_speed_turning"
                  type="number"
                  class="ei ei-num"
                  step="1"
                  :data-testid="`price-cat-edit-vc-turn-${c.id}`"
                />
              </template>
              <template v-else>
                {{ c.cutting_speed_turning != null ? formatNumber(c.cutting_speed_turning, 0) : '—' }}
              </template>
            </td>
            <td class="r t4">
              <template v-if="editingId === c.id && editDraft">
                <input
                  v-model.number="editDraft.cutting_speed_milling"
                  type="number"
                  class="ei ei-num"
                  step="1"
                  :data-testid="`price-cat-edit-vc-mill-${c.id}`"
                />
              </template>
              <template v-else>
                {{ c.cutting_speed_milling != null ? formatNumber(c.cutting_speed_milling, 0) : '—' }}
              </template>
            </td>
            <template v-if="editingId === c.id && editDraft">
              <td class="act-cell">
                <button
                  class="icon-btn icon-btn-brand icon-btn-sm"
                  data-testid="pc-save-btn"
                  title="Uložit (Enter)"
                  @click.stop="saveEdit"
                >
                  <CheckIcon :size="ICON_SIZE_SM" />
                </button>
                <button
                  class="icon-btn icon-btn-sm"
                  data-testid="pc-cancel-btn"
                  title="Zrušit (Esc)"
                  @click.stop="cancelEdit"
                >
                  <XIcon :size="ICON_SIZE_SM" />
                </button>
              </td>
            </template>
            <template v-else>
              <td />
            </template>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.tab-content { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.srch-bar {
  display: flex; align-items: center; gap: 6px;
  padding: 5px var(--pad); border-bottom: 1px solid var(--b1); flex-shrink: 0;
}
.srch-inp {
  flex: 1; background: var(--b1); border: 1px solid var(--b2);
  border-radius: var(--rs); color: var(--t1); font-size: var(--fs);
  padding: 3px 6px; outline: none;
}
.srch-inp::placeholder { color: var(--t4); }
.srch-inp:focus { border-color: var(--b3); }
.srch-count { font-size: var(--fsm); color: var(--t4); white-space: nowrap; }
.mod-placeholder {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 8px; color: var(--t4);
}
.mod-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--b2); }
.mod-dot.err { background: var(--err); }
.mod-label { font-size: var(--fsl); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
.ot-wrap { flex: 1; overflow-y: auto; overflow-x: hidden; min-height: 0; }

.t3 { color: var(--t3); }
.t4 { color: var(--t4); }
.r { text-align: right; }

/* Inline editing */
.row-editing td { background: var(--raised); border-bottom-color: var(--b3); }
.row-editing:hover td { background: var(--raised); }
.row-clickable { cursor: pointer; }
.ei {
  background: var(--surface); border: 1px solid var(--b3);
  border-radius: var(--rs); color: var(--t1); font-size: var(--fs);
  padding: 2px 4px; outline: none;
}
.ei:focus { border-color: rgba(255,255,255,0.3); }
.ei-num { font-family: var(--mono); width: 64px; text-align: right; }
.ei-xs { width: 44px; }
.ei-sm-text { width: 56px; }
.ei-wide { width: 100%; }
</style>
