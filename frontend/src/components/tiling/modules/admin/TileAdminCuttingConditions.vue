<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { CheckIcon, XIcon } from 'lucide-vue-next'
import * as ccApi from '@/api/cutting-conditions'
import type { CuttingConditionPivotResponse } from '@/types/cutting-condition'
import { formatNumber } from '@/utils/formatters'
import { useUiStore } from '@/stores/ui'
import Spinner from '@/components/ui/Spinner.vue'
import { ICON_SIZE_SM } from '@/config/design'

type Mode = 'low' | 'mid' | 'high'

const ui = useUiStore()
const mode = ref<Mode>('mid')
const pivot = ref<CuttingConditionPivotResponse | null>(null)
const loading = ref(false)
const error = ref(false)
const search = ref('')

interface FlatRow {
  id: number
  matCode: string
  opKey: string
  material: string
  operation: string
  operationType: string
  Vc: number | null
  f: number | null
  Ap: number | null
  version: number
}

interface CcDraft {
  id: number
  matCode: string
  opKey: string
  Vc: number | null
  f: number | null
  Ap: number | null
  version: number
}

const editingId = ref<number | null>(null)
const editDraft = ref<CcDraft | null>(null)

const flatRows = computed<FlatRow[]>(() => {
  if (!pivot.value) return []
  const { materials, material_names, operations, cells } = pivot.value
  const rows: FlatRow[] = []
  for (const matCode of materials) {
    const matCells = cells[matCode] ?? {}
    for (const op of operations) {
      const key = `${op.operation_type}/${op.operation}`
      const cell = matCells[key]
      if (!cell) continue
      rows.push({
        id: cell.id,
        matCode,
        opKey: key,
        material: material_names[matCode] ?? matCode,
        operation: op.label,
        operationType: op.operation_type,
        Vc: cell.Vc,
        f: cell.f,
        Ap: cell.Ap,
        version: cell.version,
      })
    }
  }
  return rows
})

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return flatRows.value
  return flatRows.value.filter(r =>
    r.material.toLowerCase().includes(q) ||
    r.operation.toLowerCase().includes(q) ||
    r.operationType.toLowerCase().includes(q),
  )
})

function startEdit(row: FlatRow) {
  editingId.value = row.id
  editDraft.value = {
    id: row.id,
    matCode: row.matCode,
    opKey: row.opKey,
    Vc: row.Vc,
    f: row.f,
    Ap: row.Ap,
    version: row.version,
  }
}

async function saveEdit() {
  const draft = editDraft.value
  if (!draft) return
  const id = draft.id
  const matCode = draft.matCode
  const opKey = draft.opKey
  editingId.value = null
  editDraft.value = null
  try {
    const updated = await ccApi.update(id, { Vc: draft.Vc, f: draft.f, Ap: draft.Ap, version: draft.version })
    if (pivot.value?.cells[matCode]?.[opKey]) {
      pivot.value.cells[matCode][opKey] = updated
    }
    ui.showSuccess('Podmínka uložena')
  } catch {
    ui.showError('Chyba při ukládání podmínky')
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

async function load() {
  loading.value = true
  error.value = false
  try {
    pivot.value = await ccApi.getPivot(mode.value)
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

watch(mode, load)
onMounted(load)
</script>

<template>
  <div class="tab-content">
    <div class="toolbar">
      <div class="mode-tabs">
        <button
          v-for="m in (['low', 'mid', 'high'] as Mode[])"
          :key="m"
          :class="['ptab', mode === m ? 'on' : '']"
          :data-testid="`cc-mode-${m}`"
          @click="mode = m"
        >
          {{ m === 'low' ? 'Nízká' : m === 'mid' ? 'Střední' : 'Vysoká' }}
        </button>
      </div>
      <input
        v-model="search"
        class="srch-inp"
        type="text"
        placeholder="Hledat materiál, operaci…"
        data-testid="cc-search-input"
      />
      <span class="srch-count">{{ filtered.length }}</span>
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
      <span class="mod-label">{{ search ? 'Žádné výsledky' : 'Žádná data' }}</span>
    </div>
    <div v-else class="ot-wrap">
      <table class="ot">
        <thead>
          <tr>
            <th>Materiál</th>
            <th>Operace</th>
            <th class="r" style="width:72px">Vc (m/min)</th>
            <th class="r" style="width:72px">f (mm/ot)</th>
            <th class="r" style="width:72px">Ap (mm)</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, i) in filtered"
            :key="i"
            :class="['row-clickable', { 'row-editing': editingId === row.id }]"
            :data-testid="`cc-row-${i}`"
            @click="editingId !== row.id ? startEdit(row) : undefined"
            @keydown.capture="editingId === row.id ? onKeydown($event) : undefined"
          >
            <td>{{ row.material }}</td>
            <td class="t4">{{ row.operation }}</td>
            <td class="r">
              <template v-if="editingId === row.id && editDraft">
                <input
                  v-model.number="editDraft.Vc"
                  type="number"
                  class="ei ei-num"
                  step="1"
                  :data-testid="`cc-edit-vc-${row.id}`"
                />
              </template>
              <template v-else>
                <span class="">{{ row.Vc != null ? formatNumber(row.Vc, 0) : '—' }}</span>
              </template>
            </td>
            <td class="r">
              <template v-if="editingId === row.id && editDraft">
                <input
                  v-model.number="editDraft.f"
                  type="number"
                  class="ei ei-num"
                  step="0.001"
                  :data-testid="`cc-edit-f-${row.id}`"
                />
              </template>
              <template v-else>
                <span class="t4">{{ row.f != null ? formatNumber(row.f, 4) : '—' }}</span>
              </template>
            </td>
            <td class="r">
              <template v-if="editingId === row.id && editDraft">
                <input
                  v-model.number="editDraft.Ap"
                  type="number"
                  class="ei ei-num"
                  step="0.1"
                  :data-testid="`cc-edit-ap-${row.id}`"
                />
              </template>
              <template v-else>
                <span class="t4">{{ row.Ap != null ? formatNumber(row.Ap, 2) : '—' }}</span>
              </template>
            </td>
            <template v-if="editingId === row.id && editDraft">
              <td class="act-cell">
                <button
                  class="icon-btn icon-btn-brand icon-btn-sm"
                  data-testid="cc-save-btn"
                  title="Uložit (Enter)"
                  @click.stop="saveEdit"
                >
                  <CheckIcon :size="ICON_SIZE_SM" />
                </button>
                <button
                  class="icon-btn icon-btn-sm"
                  data-testid="cc-cancel-btn"
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
.toolbar {
  display: flex; align-items: center; gap: 8px;
  padding: 5px var(--pad); border-bottom: 1px solid var(--b1); flex-shrink: 0;
}
.mode-tabs { display: flex; gap: 2px; }
.ptab { padding: 3px 7px; font-size: var(--fsx); font-weight: 500; color: var(--t4); background: transparent; border: none; border-radius: var(--rs); cursor: pointer; font-family: var(--font); }
.ptab:hover { color: var(--t3); }
.ptab.on { color: var(--t1); background: var(--b1); }
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

.t4 { color: var(--t4); }
.r { text-align: right; }
.row-clickable { cursor: pointer; }
.row-editing td { background: var(--raised); border-bottom-color: var(--b3); }
.row-editing:hover td { background: var(--raised); }
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
</style>
