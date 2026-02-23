<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { CheckIcon, XIcon } from 'lucide-vue-next'
import * as materialsApi from '@/api/materials'
import type { MaterialGroup } from '@/types/admin-user'
import { formatNumber } from '@/utils/formatters'
import { useUiStore } from '@/stores/ui'
import Spinner from '@/components/ui/Spinner.vue'
import { ICON_SIZE_SM } from '@/config/design'

interface GroupDraft {
  code: string
  name: string
  iso_group: string | null
  density: number | null
  hardness_hb: number | null
  cutting_speed_turning: number | null
  cutting_speed_milling: number | null
  version: number
}

const ui = useUiStore()

const groups = ref<MaterialGroup[]>([])
const loading = ref(false)
const error = ref(false)
const search = ref('')

const editingId = ref<number | null>(null)
const editDraft = ref<GroupDraft | null>(null)

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return groups.value
  return groups.value.filter(g =>
    g.code.toLowerCase().includes(q) ||
    g.name.toLowerCase().includes(q) ||
    (g.iso_group ?? '').toLowerCase().includes(q),
  )
})

async function load() {
  loading.value = true
  error.value = false
  try {
    groups.value = await materialsApi.getGroups()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

function startEdit(g: MaterialGroup) {
  editingId.value = g.id
  editDraft.value = {
    code: g.code,
    name: g.name,
    iso_group: g.iso_group ?? null,
    density: g.density,
    hardness_hb: g.hardness_hb ?? null,
    cutting_speed_turning: g.cutting_speed_turning ?? null,
    cutting_speed_milling: g.cutting_speed_milling ?? null,
    version: g.version,
  }
}

async function saveEdit() {
  const id = editingId.value
  const draft = editDraft.value
  if (!id || !draft) return
  editingId.value = null
  editDraft.value = null
  try {
    const updated = await materialsApi.updateGroup(id, draft)
    const idx = groups.value.findIndex(g => g.id === id)
    if (idx !== -1) groups.value[idx] = updated
    ui.showSuccess('Skupina uložena')
  } catch {
    ui.showError('Chyba při ukládání skupiny')
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
        data-testid="mat-groups-search-input"
      />
      <span class="srch-count">{{ filtered.length }} / {{ groups.length }}</span>
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
      <span class="mod-label">{{ search ? 'Žádné výsledky' : 'Žádné skupiny' }}</span>
    </div>
    <div v-else class="ot-wrap">
      <table class="ot">
        <thead>
          <tr>
            <th style="width:60px">Kód</th>
            <th>Název</th>
            <th style="width:55px">ISO sk.</th>
            <th class="r" style="width:72px">Hustota</th>
            <th class="r" style="width:72px">Tvrdost</th>
            <th class="r" style="width:78px">Vc soustr.</th>
            <th class="r" style="width:78px">Vc fréz.</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="g in filtered"
            :key="g.id"
            :data-testid="`mat-group-row-${g.id}`"
            :class="['row-clickable', { 'row-editing': editingId === g.id }]"
            @click="editingId !== g.id ? startEdit(g) : undefined"
            @keydown.capture="editingId === g.id ? onKeydown($event) : undefined"
          >
            <!-- EDIT MODE -->
            <template v-if="editingId === g.id && editDraft">
              <td>
                <input
                  v-model="editDraft.code"
                  type="text"
                  class="ei ei-sm-text"
                  :data-testid="`mat-group-edit-code-${g.id}`"
                />
              </td>
              <td>
                <input
                  v-model="editDraft.name"
                  type="text"
                  class="ei ei-wide"
                  :data-testid="`mat-group-edit-name-${g.id}`"
                />
              </td>
              <td>
                <input
                  v-model="editDraft.iso_group"
                  type="text"
                  class="ei ei-xs"
                  :data-testid="`mat-group-edit-iso-${g.id}`"
                />
              </td>
              <td class="r">
                <input
                  v-model.number="editDraft.density"
                  type="number"
                  class="ei ei-num"
                  step="0.01"
                  :data-testid="`mat-group-edit-density-${g.id}`"
                />
              </td>
              <td class="r">
                <input
                  v-model.number="editDraft.hardness_hb"
                  type="number"
                  class="ei ei-num"
                  step="1"
                  :data-testid="`mat-group-edit-hardness-${g.id}`"
                />
              </td>
              <td class="r">
                <input
                  v-model.number="editDraft.cutting_speed_turning"
                  type="number"
                  class="ei ei-num"
                  step="1"
                  :data-testid="`mat-group-edit-vc-turn-${g.id}`"
                />
              </td>
              <td class="r">
                <input
                  v-model.number="editDraft.cutting_speed_milling"
                  type="number"
                  class="ei ei-num"
                  step="1"
                  :data-testid="`mat-group-edit-vc-mill-${g.id}`"
                />
              </td>
              <td class="act-cell">
                <button
                  class="icon-btn icon-btn-brand icon-btn-sm"
                  data-testid="mg-save-btn"
                  title="Uložit (Enter)"
                  @click.stop="saveEdit"
                >
                  <CheckIcon :size="ICON_SIZE_SM" />
                </button>
                <button
                  class="icon-btn icon-btn-sm"
                  data-testid="mg-cancel-btn"
                  title="Zrušit (Esc)"
                  @click.stop="cancelEdit"
                >
                  <XIcon :size="ICON_SIZE_SM" />
                </button>
              </td>
            </template>

            <!-- VIEW MODE -->
            <template v-else>
              <td class="t3">{{ g.code }}</td>
              <td>{{ g.name }}</td>
              <td class="t4">{{ g.iso_group ?? '—' }}</td>
              <td class="r t4">
                {{ g.density != null ? formatNumber(g.density, 2) : '—' }}
              </td>
              <td class="r t4">
                {{ g.hardness_hb != null ? formatNumber(g.hardness_hb, 0) : '—' }}
              </td>
              <td class="r t4">
                {{ g.cutting_speed_turning != null ? formatNumber(g.cutting_speed_turning, 0) : '—' }}
              </td>
              <td class="r t4">
                {{ g.cutting_speed_milling != null ? formatNumber(g.cutting_speed_milling, 0) : '—' }}
              </td>
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
  flex: 1; height: 28px; background: rgba(255,255,255,0.04); border: 1px solid var(--b2);
  border-radius: var(--rs); color: var(--t2); font-size: var(--fs);
  padding: 3px 6px; outline: none;
  transition: border-color 120ms var(--ease), background 120ms var(--ease), color 120ms var(--ease);
}
.srch-inp::placeholder { color: var(--t4); }
.srch-inp:focus { border-color: var(--b3); background: rgba(255,255,255,0.07); color: var(--t1); }
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
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t2);
  font-size: var(--fs);
  padding: 2px 4px;
  outline: none;
  transition: border-color 120ms var(--ease), background 120ms var(--ease), color 120ms var(--ease);
}
.ei:focus { border-color: var(--b3); background: rgba(255,255,255,0.07); color: var(--t1); }
.ei-num { font-family: var(--mono); width: 64px; text-align: right; }
.ei-xs { width: 44px; }
.ei-sm-text { width: 56px; }
.ei-wide { width: 100%; }
</style>
