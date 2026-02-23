<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { PlusIcon, PencilIcon, XIcon, CheckIcon, Link2OffIcon } from 'lucide-vue-next'
import { usePartsStore } from '@/stores/parts'
import { useUiStore } from '@/stores/ui'
import * as materialInputsApi from '@/api/material-inputs'
import * as operationsApi from '@/api/operations'
import type { MaterialInput, StockShape, MaterialInputCreate, MaterialInputUpdate, ParseResult, SuggestedMaterialItem } from '@/types/material-input'
import type { ContextGroup } from '@/types/workspace'
import { formatCurrency, formatNumber } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'
import { ICON_SIZE_SM } from '@/config/design'

// Module-level cache: partId → items. Survives component unmount/remount (panel moves).
const _cache = new Map<number, MaterialInput[]>()
// Tracks which leafId has already fetched data for which partId — skips refetch on remount.
const _fetchedFor = new Map<string, number>()

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()
const ui = useUiStore()

const part = computed(() => parts.getFocusedPart(props.ctx))

const items = ref<MaterialInput[]>([])
const loading = ref(false)
const error = ref(false)
const isRefetching = computed(() => loading.value && items.value.length > 0)

// ─── Edit dimensions ───
const editingId = ref<number | null>(null)
const editDims = ref<Record<string, number | null>>({})
const saving = ref(false)

// ─── Operation linking ───
const partOps = ref<Array<{ id: number; seq: number; name: string; type: string }>>([])
const partOpsLoaded = ref(false)
const linkingOpFor = ref<number | null>(null)
const selectedOpId = ref<number | null>(null)
const linkingSaving = ref(false)

// ─── Add material ───
const showAdd = ref(false)
const parseInput = ref('')
const parsing = ref(false)
const parseResult = ref<ParseResult | null>(null)
const selectedItem = ref<SuggestedMaterialItem | null>(null)
const creating = ref(false)

const totalWeight = computed(() => items.value.reduce((s, m) => s + (m.weight_kg ?? 0), 0))
const totalCost = computed(() => items.value.reduce((s, m) => s + (m.cost_per_piece ?? 0), 0))

const SHAPE_LABELS: Record<StockShape, string> = {
  round_bar:     'Tyč kulatá',
  square_bar:    'Tyč čtvercová',
  flat_bar:      'Tyč plochá',
  hexagonal_bar: 'Tyč šestihranná',
  plate:         'Plech',
  tube:          'Trubka',
  casting:       'Odlitek',
  forging:       'Výkovek',
}

// All editable fields when no catalog item is linked (generic material)
const DIM_FIELDS_FULL: Record<StockShape, string[]> = {
  round_bar:     ['stock_diameter', 'stock_length'],
  hexagonal_bar: ['stock_diameter', 'stock_length'],
  square_bar:    ['stock_width', 'stock_length'],
  flat_bar:      ['stock_width', 'stock_height', 'stock_length'],
  plate:         ['stock_width', 'stock_height'],
  tube:          ['stock_diameter', 'stock_wall_thickness', 'stock_length'],
  casting:       ['stock_length'],
  forging:       ['stock_length'],
}

// Only variable fields when catalog item is linked (cross-section is fixed by catalog)
// For bars: only length. For plates: width + height (sheet piece dimensions). Castings: nothing.
const DIM_FIELDS_LOCKED: Record<StockShape, string[]> = {
  round_bar:     ['stock_length'],
  hexagonal_bar: ['stock_length'],
  square_bar:    ['stock_length'],
  flat_bar:      ['stock_length'],
  plate:         ['stock_width', 'stock_height'],
  tube:          ['stock_length'],
  casting:       [],
  forging:       [],
}

function editFields(m: MaterialInput): string[] {
  return m.material_item ? DIM_FIELDS_LOCKED[m.stock_shape] : DIM_FIELDS_FULL[m.stock_shape]
}

const DIM_LABELS: Record<string, string> = {
  stock_diameter:       'Průměr (mm)',
  stock_length:         'Délka (mm)',
  stock_width:          'Šířka (mm)',
  stock_height:         'Výška (mm)',
  stock_wall_thickness: 'Tl. stěny (mm)',
}

function dimLabel(m: MaterialInput): string {
  const d = (v: number | null) => v != null ? String(v) : '?'
  switch (m.stock_shape) {
    case 'round_bar':
    case 'hexagonal_bar':
      return `\u00D8${d(m.stock_diameter)} \u00D7 ${d(m.stock_length)} mm`
    case 'square_bar':
      return `${d(m.stock_width)} \u00D7 ${d(m.stock_length)} mm`
    case 'flat_bar':
      return `${d(m.stock_width)} \u00D7 ${d(m.stock_height)} \u00D7 ${d(m.stock_length)} mm`
    case 'plate':
      return `${d(m.stock_width)} \u00D7 ${d(m.stock_height)} mm`
    case 'tube':
      return `\u00D8${d(m.stock_diameter)} \u00D7 ${d(m.stock_length)}, t=${d(m.stock_wall_thickness)} mm`
    default:
      return m.stock_length != null ? `${d(m.stock_length)} mm` : '—'
  }
}

function matPrimary(m: MaterialInput): string {
  return m.material_item?.name ?? m.price_category?.name ?? '—'
}

function matSub(m: MaterialInput): string {
  if (m.material_item) {
    return m.material_item.material_number + (m.price_category ? ' · ' + m.price_category.name : '')
  }
  return m.price_category?.code ?? ''
}

const availableOps = computed(() => {
  if (!linkingOpFor.value) return partOps.value
  const m = items.value.find(x => x.id === linkingOpFor.value)
  if (!m) return partOps.value
  const linkedIds = new Set(m.operations.map(o => o.id))
  return partOps.value.filter(o => !linkedIds.has(o.id))
})

function toNum(v: unknown): number | null {
  if (v === null || v === undefined || v === '') return null
  const n = Number(v)
  return isNaN(n) ? null : n
}

function startEdit(m: MaterialInput) {
  editingId.value = m.id
  editDims.value = {
    stock_diameter:       m.stock_diameter,
    stock_length:         m.stock_length,
    stock_width:          m.stock_width,
    stock_height:         m.stock_height,
    stock_wall_thickness: m.stock_wall_thickness,
  }
  linkingOpFor.value = null
}

function cancelEdit() {
  editingId.value = null
  linkingOpFor.value = null
}

async function saveEdit(m: MaterialInput) {
  saving.value = true
  try {
    const payload: MaterialInputUpdate = {
      stock_diameter:       toNum(editDims.value.stock_diameter),
      stock_length:         toNum(editDims.value.stock_length),
      stock_width:          toNum(editDims.value.stock_width),
      stock_height:         toNum(editDims.value.stock_height),
      stock_wall_thickness: toNum(editDims.value.stock_wall_thickness),
      version: m.version,
    }
    const updated = await materialInputsApi.update(m.id, payload)
    const idx = items.value.findIndex(x => x.id === m.id)
    if (idx >= 0) {
      items.value[idx] = updated
      _cache.set(part.value!.id, [...items.value])
    }
    editingId.value = null
    ui.showSuccess('Rozměry uloženy')
  } catch {
    ui.showError('Chyba při ukládání rozměrů')
  } finally {
    saving.value = false
  }
}

async function loadPartOps() {
  if (partOpsLoaded.value || !part.value) return
  try {
    const ops = await operationsApi.getByPartId(part.value.id)
    partOps.value = ops.map(o => ({ id: o.id, seq: o.seq, name: o.name, type: o.type }))
    partOpsLoaded.value = true
  } catch { /* silent */ }
}

async function startLinkOp(materialId: number) {
  await loadPartOps()
  linkingOpFor.value = materialId
  selectedOpId.value = null
}

async function confirmLinkOp(m: MaterialInput) {
  if (!selectedOpId.value) return
  linkingSaving.value = true
  try {
    await materialInputsApi.linkOperation(m.id, selectedOpId.value)
    const op = partOps.value.find(o => o.id === selectedOpId.value)
    if (op) {
      const mat = items.value.find(x => x.id === m.id)
      if (mat) {
        mat.operations.push({ id: op.id, seq: op.seq, name: op.name, type: op.type })
        _cache.set(part.value!.id, [...items.value])
      }
    }
    linkingOpFor.value = null
    selectedOpId.value = null
    ui.showSuccess('Vazba přidána')
  } catch {
    ui.showError('Chyba při přidávání vazby')
  } finally {
    linkingSaving.value = false
  }
}

async function removeOpLink(m: MaterialInput, opId: number) {
  try {
    await materialInputsApi.unlinkOperation(m.id, opId)
    const mat = items.value.find(x => x.id === m.id)
    if (mat) {
      mat.operations = mat.operations.filter(o => o.id !== opId)
      _cache.set(part.value!.id, [...items.value])
    }
    ui.showSuccess('Vazba odebrána')
  } catch {
    ui.showError('Chyba při odebírání vazby')
  }
}

function toggleAdd() {
  showAdd.value = !showAdd.value
  if (!showAdd.value) {
    parseInput.value = ''
    parseResult.value = null
  }
}

async function doParse() {
  if (!parseInput.value.trim()) return
  parsing.value = true
  parseResult.value = null
  selectedItem.value = null
  try {
    const pr = await materialInputsApi.parse(parseInput.value.trim())
    parseResult.value = pr
    // Předvyber první kandidát (primární)
    selectedItem.value = pr.suggested_material_items[0] ?? null
  } catch {
    ui.showError('Chyba při parsování')
  } finally {
    parsing.value = false
  }
}

async function confirmCreate() {
  if (!parseResult.value || !part.value) return
  const pr = parseResult.value
  if (!pr.suggested_price_category_id || !pr.shape) {
    ui.showError('Nelze vytvořit: nerozpoznaná cenová kategorie nebo tvar')
    return
  }
  // Použij vybraného kandidáta (pokud uživatel vybral), jinak primární
  const itemId = selectedItem.value?.id ?? pr.suggested_material_item_id ?? null
  creating.value = true
  try {
    const payload: MaterialInputCreate = {
      part_id: part.value.id,
      price_category_id: pr.suggested_price_category_id,
      material_item_id: itemId,
      stock_shape: pr.shape,
      stock_diameter:       pr.diameter ?? null,
      stock_length:         pr.length ?? null,
      stock_width:          pr.width ?? null,
      stock_height:         pr.height ?? null,
      stock_wall_thickness: pr.wall_thickness ?? null,
      quantity: 1,
      seq: items.value.length,
    }
    await materialInputsApi.create(payload)
    _fetchedFor.delete(props.leafId)
    loading.value = true
    items.value = await materialInputsApi.getByPartId(part.value.id)
    _cache.set(part.value.id, [...items.value])
    showAdd.value = false
    parseInput.value = ''
    parseResult.value = null
    ui.showSuccess('Materiál přidán')
  } catch {
    ui.showError('Chyba při vytváření materiálu')
  } finally {
    creating.value = false
    loading.value = false
  }
}

watch(
  part,
  async (p) => {
    if (!p) {
      items.value = []
      editingId.value = null
      partOpsLoaded.value = false
      partOps.value = []
      return
    }
    if (_cache.has(p.id)) items.value = _cache.get(p.id)!
    if (_fetchedFor.get(props.leafId) === p.id) return
    _fetchedFor.set(props.leafId, p.id)
    loading.value = true
    error.value = false
    editingId.value = null
    partOpsLoaded.value = false
    partOps.value = []
    try {
      items.value = await materialInputsApi.getByPartId(p.id)
      _cache.set(p.id, [...items.value])
    } catch {
      error.value = true
      _fetchedFor.delete(props.leafId)
      if (!items.value.length) items.value = []
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
</script>

<template>
  <div :class="['wmat', { refetching: isRefetching }]">
    <!-- No part selected -->
    <div v-if="!part" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Vyberte díl ze seznamu</span>
    </div>

    <!-- Loading -->
    <div v-else-if="loading && !items.length" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>

    <template v-else>
      <!-- Ribbon -->
      <div class="rib">
        <div class="rib-r">
          <div class="rib-i">
            <span class="rib-l">Materiálů</span>
            <span class="rib-v m">{{ items.length }}</span>
          </div>
          <div class="rib-i">
            <span class="rib-l">Hmotnost / ks</span>
            <span class="rib-v m">{{ formatNumber(totalWeight, 3) }} kg</span>
          </div>
          <div class="rib-i">
            <span class="rib-l">Náklady / ks</span>
            <span class="rib-v m green">{{ formatCurrency(totalCost) }}</span>
          </div>
        </div>
        <button
          :class="['icon-btn', 'icon-btn-brand', { 'add-active': showAdd }]"
          data-testid="add-material-btn"
          title="Přidat materiál"
          @click="toggleAdd"
        >
          <PlusIcon :size="ICON_SIZE_SM" />
        </button>
      </div>

      <!-- Add form -->
      <div v-if="showAdd" class="add-form">
        <div class="add-row">
          <input
            v-model="parseInput"
            class="parse-input"
            placeholder="Např. D20 1.4301 100mm"
            data-testid="parse-input"
            @keydown.enter="doParse"
          />
          <button
            class="btn-secondary"
            :disabled="parsing || !parseInput.trim()"
            data-testid="parse-btn"
            @click="doParse"
          >
            <Spinner v-if="parsing" size="sm" :inline="true" />
            <span v-else>Parsovat</span>
          </button>
        </div>
        <div v-if="parseResult" class="parse-result">
          <div class="pr-grid">
            <span class="pr-lbl">Tvar</span>
            <span class="pr-val">{{ parseResult.shape ? SHAPE_LABELS[parseResult.shape] : '—' }}</span>
            <template v-if="parseResult.suggested_price_category_name">
              <span class="pr-lbl">Cenová kategorie</span>
              <span class="pr-val">{{ parseResult.suggested_price_category_name }}</span>
            </template>
            <template v-if="parseResult.suggested_material_items.length > 0">
              <span class="pr-lbl">{{ parseResult.suggested_material_items.length > 1 ? 'Vyberte položku' : 'Položka katalogu' }}</span>
              <div class="pr-items-list">
                <button
                  v-for="it in parseResult.suggested_material_items"
                  :key="it.id"
                  :class="['pr-item-opt', { 'pr-item-selected': selectedItem?.id === it.id }]"
                  :data-testid="`item-opt-${it.id}`"
                  @click="selectedItem = it"
                >
                  <span class="pr-item-opt-name">{{ it.name }}</span>
                  <span class="pr-item-opt-code">{{ it.code }}</span>
                </button>
              </div>
            </template>
            <span class="pr-lbl">Shoda</span>
            <span :class="['pr-val', parseResult.confidence > 0.7 ? 'pr-ok' : 'pr-warn']">
              {{ Math.round(parseResult.confidence * 100) }}%
            </span>
          </div>
          <div v-for="w in parseResult.warnings" :key="w" class="pr-warning">{{ w }}</div>
          <div class="pr-actions">
            <button
              class="btn-primary"
              :disabled="!parseResult.suggested_price_category_id || !parseResult.shape || creating"
              data-testid="confirm-create-btn"
              @click="confirmCreate"
            >
              <Spinner v-if="creating" size="sm" :inline="true" />
              <span v-else>Vytvořit materiál</span>
            </button>
            <button class="btn-secondary" data-testid="cancel-add-btn" @click="toggleAdd">Zrušit</button>
          </div>
        </div>
      </div>

      <!-- Empty -->
      <div v-if="!items.length" class="mod-placeholder">
        <div class="mod-dot" />
        <span class="mod-label">Díl nemá žádné materiály</span>
      </div>

      <!-- Table -->
      <div v-else class="ot-wrap">
        <table class="ot">
          <thead>
            <tr>
              <th style="width:24px">#</th>
              <th>Materiál</th>
              <th>Tvar / rozměry</th>
              <th>Operace</th>
              <th class="r" style="width:80px">Hmotnost</th>
              <th class="r" style="width:100px">Cena / ks</th>
              <th style="width:28px"></th>
            </tr>
          </thead>
          <tbody v-for="m in items" :key="m.id">
            <!-- Main row -->
            <tr :class="{ 'row-editing': editingId === m.id }" :data-testid="`mat-row-${m.id}`">
              <td class="t4">{{ m.seq + 1 }}</td>
              <td>
                <div class="mat-name">{{ matPrimary(m) }}</div>
                <div v-if="m.material_item?.code" class="mat-code">{{ m.material_item.code }}</div>
                <div v-if="matSub(m)" class="mat-sub t4">{{ matSub(m) }}</div>
              </td>
              <td>
                <div>{{ SHAPE_LABELS[m.stock_shape] }}</div>
                <div class="mat-sub t4">{{ dimLabel(m) }}</div>
              </td>
              <td>
                <div class="op-chips">
                  <span v-for="op in m.operations" :key="op.id" class="op-chip">
                    {{ op.seq }}. {{ op.name }}
                  </span>
                  <span v-if="!m.operations.length" class="t4 fsl">—</span>
                </div>
              </td>
              <td class="r">
                {{ m.weight_kg != null ? formatNumber(m.weight_kg, 3) + ' kg' : '—' }}
              </td>
              <td class="r">
                <span class="price-badge">{{ formatCurrency(m.cost_per_piece) }}</span>
              </td>
              <td>
                <button
                  v-if="editingId !== m.id"
                  class="icon-btn"
                  :data-testid="`edit-mat-${m.id}`"
                  title="Upravit rozměry"
                  @click="startEdit(m)"
                >
                  <PencilIcon :size="ICON_SIZE_SM" />
                </button>
                <button
                  v-else
                  class="icon-btn"
                  :data-testid="`cancel-edit-mat-${m.id}`"
                  title="Zrušit"
                  @click="cancelEdit"
                >
                  <XIcon :size="ICON_SIZE_SM" />
                </button>
              </td>
            </tr>

            <!-- Edit row -->
            <tr v-if="editingId === m.id" :data-testid="`edit-row-${m.id}`">
              <td colspan="7" class="edit-td">
                <div class="edit-panel">
                  <!-- Dimension inputs -->
                  <div class="edit-section">
                    <div class="edit-sec-title">
                      Rozměry
                      <span v-if="m.material_item" class="locked-hint">průřez fixní dle katalogu</span>
                    </div>
                    <div v-if="editFields(m).length === 0" class="t4 fsl">Rozměry definuje katalogová položka</div>
                    <div v-else class="dim-grid">
                      <template v-for="field in editFields(m)" :key="field">
                        <label class="dim-lbl">{{ DIM_LABELS[field] }}</label>
                        <input
                          v-model.number="editDims[field]"
                          type="number"
                          class="dim-input"
                          :data-testid="`dim-${field}-${m.id}`"
                          step="0.1"
                          min="0"
                        />
                      </template>
                    </div>
                    <div v-if="editFields(m).length > 0" class="edit-actions">
                      <button
                        class="icon-btn icon-btn-brand icon-btn-sm"
                        :disabled="saving"
                        :data-testid="`save-dims-${m.id}`"
                        @click="saveEdit(m)"
                      >
                        <Spinner v-if="saving" size="sm" :inline="true" />
                        <CheckIcon v-else :size="ICON_SIZE_SM" />
                      </button>
                      <button class="btn-secondary" :data-testid="`cancel-dims-${m.id}`" @click="cancelEdit">
                        Zrušit
                      </button>
                    </div>
                  </div>

                  <!-- Operation links -->
                  <div class="edit-section">
                    <div class="edit-sec-title">Vazby na operace</div>
                    <div class="op-list">
                      <div v-if="!m.operations.length" class="t4 fsl">Žádné vazby</div>
                      <div v-for="op in m.operations" :key="op.id" class="op-item">
                        <span class="op-item-name">{{ op.seq }}. {{ op.name }}</span>
                        <button
                          class="icon-btn icon-btn-danger icon-btn-sm"
                          :data-testid="`unlink-op-${m.id}-${op.id}`"
                          title="Odebrat vazbu"
                          @click="removeOpLink(m, op.id)"
                        >
                          <Link2OffIcon :size="ICON_SIZE_SM" />
                        </button>
                      </div>
                    </div>
                    <div v-if="linkingOpFor === m.id" class="link-op-row">
                      <select
                        v-model.number="selectedOpId"
                        class="op-select"
                        :data-testid="`op-select-${m.id}`"
                      >
                        <option :value="null" disabled>Vyberte operaci…</option>
                        <option v-for="op in availableOps" :key="op.id" :value="op.id">
                          {{ op.seq }}. {{ op.name }}
                        </option>
                      </select>
                      <button
                        class="icon-btn icon-btn-brand"
                        :disabled="!selectedOpId || linkingSaving"
                        :data-testid="`confirm-link-op-${m.id}`"
                        @click="confirmLinkOp(m)"
                      >
                        <CheckIcon :size="ICON_SIZE_SM" />
                      </button>
                      <button
                        class="icon-btn"
                        :data-testid="`cancel-link-op-${m.id}`"
                        @click="linkingOpFor = null"
                      >
                        <XIcon :size="ICON_SIZE_SM" />
                      </button>
                    </div>
                    <button
                      v-else
                      class="btn-secondary add-op-btn"
                      :data-testid="`add-op-link-${m.id}`"
                      @click="startLinkOp(m.id)"
                    >Přidat operaci</button>
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wmat {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  transition: opacity 0.15s;
}
.wmat.refetching { opacity: 0.4; }

/* ─── Placeholder ─── */
.mod-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
}
.mod-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--b2);
}
.mod-dot.err { background: var(--err); }
.mod-label { font-size: var(--fsl); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

/* ─── Ribbon ─── */
.rib {
  padding: 6px var(--pad);
  background: rgba(255,255,255,0.02);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.rib-r { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.rib-i { display: flex; align-items: baseline; gap: 4px; }
.rib-l { font-size: var(--fsm); color: var(--t4); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 500; }
.rib-v { font-size: var(--fs); color: var(--t1); font-weight: 500; }
.rib-v.m { }
.rib-v.green { color: var(--green); }

.add-active { background: var(--red-10); }

/* ─── Add form ─── */
.add-form {
  padding: 8px var(--pad);
  border-bottom: 1px solid var(--b2);
  flex-shrink: 0;
  background: rgba(255,255,255,0.015);
}
.add-row {
  display: flex;
  gap: 6px;
  align-items: center;
}
.parse-input {
  flex: 1;
  height: 28px;
  padding: 0 8px;
  background: var(--raised);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  font-family: var(--mono);
  outline: none;
}
.parse-input:focus { border-color: var(--b3); }
.parse-input::placeholder { color: var(--t4); }

.parse-result {
  margin-top: 8px;
}
.pr-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 10px;
  align-items: start;
}
.pr-lbl { font-size: var(--fsm); color: var(--t4); text-transform: uppercase; letter-spacing: 0.04em; white-space: nowrap; padding-top: 2px; }
.pr-val { font-size: var(--fs); color: var(--t1); }

.pr-ok { color: var(--ok); }
.pr-warn { color: var(--warn); }

/* Kandidáti — výběrový seznam */
.pr-items-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.pr-item-opt {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 5px 7px;
  background: var(--raised);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  cursor: pointer;
  text-align: left;
  transition: border-color 100ms var(--ease);
}
.pr-item-opt:hover { border-color: var(--b3); }
.pr-item-opt.pr-item-selected { border-color: var(--t3); background: var(--b1); }
.pr-item-opt-name { font-size: var(--fs); color: var(--t1); }
.pr-item-opt-code {
  font-size: var(--fsx);
  color: var(--t3);
}
.pr-warning {
  margin-top: 4px;
  font-size: var(--fsm);
  color: var(--warn);
}
.pr-actions {
  margin-top: 8px;
  display: flex;
  gap: 6px;
}

/* ─── Table wrapper ─── */
.ot-wrap {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

/* ─── Table ─── */
.row-editing td { background: rgba(255,255,255,0.03); }
.edit-td { padding: 0; }


.t4 { color: var(--t4); }
.fsl { font-size: var(--fsl); }

.mat-name { font-weight: 500; color: var(--t1); }
/* Catalog code badge in the table — monospace, distinct from name */
.mat-code {
  display: inline-block;
  font-size: var(--fsx);
  color: var(--t2);
  background: var(--b1);
  border: 1px solid var(--b2);
  padding: 1px 5px;
  border-radius: var(--rs);
  margin-top: 2px;
}
.mat-sub { font-size: var(--fsm); margin-top: 1px; color: var(--t4); }

/* ─── Op chips (summary column) ─── */
.op-chips { display: flex; flex-wrap: wrap; gap: 3px; }
.op-chip {
  font-size: var(--fsm);
  padding: 1px 5px;
  border-radius: 99px;
  background: var(--b1);
  color: var(--t3);
  white-space: nowrap;
}

/* ─── Price badge ─── */
.price-badge {
  display: inline-block;
  font-size: var(--fsm);
  padding: 1px 5px;
  border-radius: 99px;
  background: var(--b1);
  color: var(--green);
  white-space: nowrap;
}

/* ─── Edit panel ─── */
.edit-panel {
  display: flex;
  gap: 0;
  background: var(--raised);
  border-top: 1px solid var(--b2);
  border-bottom: 1px solid var(--b2);
}
.edit-section {
  flex: 1;
  padding: 10px var(--pad);
  border-right: 1px solid var(--b2);
}
.edit-section:last-child { border-right: none; }
.edit-sec-title {
  font-size: var(--fsm);
  font-weight: 600;
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.locked-hint {
  font-size: var(--fss);
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
  color: var(--t4);
  background: var(--b1);
  padding: 1px 5px;
  border-radius: 99px;
}
.dim-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 5px 10px;
  align-items: center;
  margin-bottom: 8px;
}
.dim-lbl {
  font-size: var(--fsm);
  color: var(--t4);
  white-space: nowrap;
}
.dim-input {
  height: 24px;
  padding: 0 6px;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  font-family: var(--mono);
  outline: none;
  width: 100%;
}
.dim-input:focus { border-color: var(--b3); }

.edit-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

/* ─── Op list in edit panel ─── */
.op-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 6px;
  min-height: 20px;
}
.op-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.op-item-name {
  flex: 1;
  font-size: var(--fs);
  color: var(--t2);
}
.link-op-row {
  display: flex;
  gap: 4px;
  align-items: center;
  margin-top: 6px;
}
.add-op-btn { margin-top: 6px; }
.op-select {
  flex: 1;
  height: 24px;
  padding: 0 6px;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  outline: none;
}
.op-select:focus { border-color: var(--b3); }
</style>
