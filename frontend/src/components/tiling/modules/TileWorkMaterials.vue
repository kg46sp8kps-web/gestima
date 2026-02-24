<script setup lang="ts">
import { ref, computed, watch, reactive } from 'vue'
import { PlusIcon, XIcon, CheckIcon, Link2OffIcon, ChevronDownIcon } from 'lucide-vue-next'
import { usePartsStore } from '@/stores/parts'
import { useUiStore } from '@/stores/ui'
import { useItemTypeGuard } from '@/composables/useItemTypeGuard'
import * as materialInputsApi from '@/api/material-inputs'
import * as operationsApi from '@/api/operations'
import type { MaterialInput, StockShape, MaterialInputCreate, MaterialInputUpdate, ParseResult, SuggestedMaterialItem } from '@/types/material-input'
import type { ContextGroup } from '@/types/workspace'
import { formatCurrency, formatNumber } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'
import Input from '@/components/ui/Input.vue'
import InlineInput from '@/components/ui/InlineInput.vue'
import InlineSelect from '@/components/ui/InlineSelect.vue'
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
const typeGuard = useItemTypeGuard(['part'])

const part = computed(() => parts.getFocusedPart(props.ctx))

const items = ref<MaterialInput[]>([])
const loading = ref(false)
const error = ref(false)
const isRefetching = computed(() => loading.value && items.value.length > 0)

// ─── Inline dimension editing — per-row, auto-save on blur ───
const rowDims = reactive<Record<number, Record<string, number | null>>>({})
const savingRowIds = ref<number[]>([])

// ─── Detail expand (operation links) ───
const expandedId = ref<number | null>(null)

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
  round_bar:     'Kulatina',
  square_bar:    'Čtyřhran',
  flat_bar:      'Plochá ocel',
  hexagonal_bar: 'Šestihran',
  plate:         'Plech',
  tube:          'Trubka',
  casting:       'Odlitek',
  forging:       'Výkovek',
}

// ─── Inline dim slots ───
interface DimSlot {
  kind: 'sep' | 'locked' | 'editable'
  text?: string
  field?: string
}

// dimSlots — data-driven z BE hodnot material_item.diameter/width/thickness/wall_thickness.
// Pokud katalog definuje rozměr (non-null) → locked badge s hodnotou z katalogu.
// Pokud katalog rozměr nemá (null nebo žádný katalog) → editable input.
function dimSlots(m: MaterialInput): DimSlot[] {
  const mi = m.material_item
  const slots: DimSlot[] = []

  switch (m.stock_shape) {
    case 'round_bar':
    case 'hexagonal_bar': {
      const sym = m.stock_shape === 'round_bar' ? '∅' : '⬡'
      if (mi?.diameter != null) {
        slots.push({ kind: 'locked', text: `${sym}${mi.diameter}` })
      } else {
        slots.push({ kind: 'sep', text: sym })
        slots.push({ kind: 'editable', field: 'stock_diameter' })
      }
      slots.push({ kind: 'sep', text: '×' })
      slots.push({ kind: 'editable', field: 'stock_length' })
      slots.push({ kind: 'sep', text: 'mm' })
      break
    }
    case 'square_bar': {
      if (mi?.width != null) {
        slots.push({ kind: 'locked', text: `□${mi.width}` })
      } else {
        slots.push({ kind: 'sep', text: '□' })
        slots.push({ kind: 'editable', field: 'stock_width' })
      }
      slots.push({ kind: 'sep', text: '×' })
      slots.push({ kind: 'editable', field: 'stock_length' })
      slots.push({ kind: 'sep', text: 'mm' })
      break
    }
    case 'flat_bar': {
      // width → stock_width, thickness → stock_height (tloušťka průřezu tyče)
      if (mi?.width != null) {
        slots.push({ kind: 'locked', text: `${mi.width}` })
      } else {
        slots.push({ kind: 'editable', field: 'stock_width' })
      }
      slots.push({ kind: 'sep', text: '×' })
      if (mi?.thickness != null) {
        slots.push({ kind: 'locked', text: `${mi.thickness}` })
      } else {
        slots.push({ kind: 'editable', field: 'stock_height' })
      }
      slots.push({ kind: 'sep', text: '×' })
      slots.push({ kind: 'editable', field: 'stock_length' })
      slots.push({ kind: 'sep', text: 'mm' })
      break
    }
    case 'plate': {
      // Tři scénáře dle katalogové položky:
      // 1. Přířez (3 fixní): mi.width && mi.height → stock_width i stock_height locked
      // 2. Pás (2 fixní): mi.width, mi.height == null → stock_width locked, stock_height = délka řezu
      // 3. Volný výřez: mi.width == null → obě variabilní
      if (mi?.width != null) {
        slots.push({ kind: 'locked', text: `${mi.width}` })
      } else {
        slots.push({ kind: 'editable', field: 'stock_width' })
      }
      slots.push({ kind: 'sep', text: '×' })
      if (mi?.height != null) {
        slots.push({ kind: 'locked', text: `${mi.height}` })
      } else {
        slots.push({ kind: 'editable', field: 'stock_height' })
      }
      if (mi?.thickness != null) {
        slots.push({ kind: 'sep', text: ' t' })
        slots.push({ kind: 'locked', text: `${mi.thickness}mm` })
      } else {
        slots.push({ kind: 'sep', text: 'mm' })
      }
      break
    }
    case 'tube': {
      if (mi?.diameter != null) {
        slots.push({ kind: 'locked', text: `∅${mi.diameter}` })
      } else {
        slots.push({ kind: 'sep', text: '∅' })
        slots.push({ kind: 'editable', field: 'stock_diameter' })
      }
      slots.push({ kind: 'sep', text: ' t' })
      if (mi?.wall_thickness != null) {
        slots.push({ kind: 'locked', text: `${mi.wall_thickness}` })
      } else {
        slots.push({ kind: 'editable', field: 'stock_wall_thickness' })
      }
      slots.push({ kind: 'sep', text: '×' })
      slots.push({ kind: 'editable', field: 'stock_length' })
      slots.push({ kind: 'sep', text: 'mm' })
      break
    }
    case 'casting':
    case 'forging': {
      // Tvary bez jednoznačné geometrie — délka orientační
      slots.push({ kind: 'editable', field: 'stock_length' })
      slots.push({ kind: 'sep', text: 'mm' })
      break
    }
  }
  return slots
}

function initRowDims(m: MaterialInput) {
  rowDims[m.id] = {
    stock_diameter:       m.stock_diameter,
    stock_length:         m.stock_length,
    stock_width:          m.stock_width,
    stock_height:         m.stock_height,
    stock_wall_thickness: m.stock_wall_thickness,
  }
}

async function saveRowDims(m: MaterialInput) {
  const dims = rowDims[m.id]
  if (!dims) return
  const changed = (
    toNum(dims.stock_diameter) !== m.stock_diameter ||
    toNum(dims.stock_length) !== m.stock_length ||
    toNum(dims.stock_width) !== m.stock_width ||
    toNum(dims.stock_height) !== m.stock_height ||
    toNum(dims.stock_wall_thickness) !== m.stock_wall_thickness
  )
  if (!changed) return
  savingRowIds.value = [...savingRowIds.value, m.id]
  try {
    const payload: MaterialInputUpdate = {
      stock_diameter:       toNum(dims.stock_diameter),
      stock_length:         toNum(dims.stock_length),
      stock_width:          toNum(dims.stock_width),
      stock_height:         toNum(dims.stock_height),
      stock_wall_thickness: toNum(dims.stock_wall_thickness),
      version: m.version,
    }
    const updated = await materialInputsApi.update(m.id, payload)
    const idx = items.value.findIndex(x => x.id === m.id)
    if (idx >= 0) {
      items.value[idx] = updated
      _cache.set(part.value!.id, [...items.value])
      initRowDims(updated)
    }
  } catch {
    ui.showError('Chyba při ukládání rozměrů')
    initRowDims(m)
  } finally {
    savingRowIds.value = savingRowIds.value.filter(id => id !== m.id)
  }
}

function toggleExpand(id: number) {
  if (expandedId.value === id) {
    expandedId.value = null
    linkingOpFor.value = null
  } else {
    expandedId.value = id
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
    items.value.forEach(initRowDims)
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
      expandedId.value = null
      partOpsLoaded.value = false
      partOps.value = []
      return
    }
    if (_cache.has(p.id)) {
      items.value = _cache.get(p.id)!
      items.value.forEach(initRowDims)
    }
    if (_fetchedFor.get(props.leafId) === p.id) return
    _fetchedFor.set(props.leafId, p.id)
    loading.value = true
    error.value = false
    expandedId.value = null
    partOpsLoaded.value = false
    partOps.value = []
    try {
      items.value = await materialInputsApi.getByPartId(p.id)
      items.value.forEach(initRowDims)
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
    <!-- Unsupported item type -->
    <div v-if="!typeGuard.isSupported(props.ctx)" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Nedostupné pro {{ typeGuard.focusedTypeName(props.ctx) }}</span>
    </div>

    <!-- No part selected -->
    <div v-else-if="!part" class="mod-placeholder">
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
          <Input
            v-model="parseInput"
            bare
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
            <tr
              :class="['mat-row', { 'row-expanded': expandedId === m.id, saving: savingRowIds.includes(m.id) }]"
              :data-testid="`mat-row-${m.id}`"
            >
              <td class="t4">{{ m.seq + 1 }}</td>
              <td>
                <div class="mat-name">{{ matPrimary(m) }}</div>
                <div v-if="m.material_item?.code" class="mat-code">{{ m.material_item.code }}</div>
                <div v-if="matSub(m)" class="mat-sub t4">{{ matSub(m) }}</div>
              </td>
              <td>
                <div class="mat-shape">{{ SHAPE_LABELS[m.stock_shape] }}</div>
                <div v-if="rowDims[m.id]" class="inline-dims">
                  <template v-for="(slot, si) in dimSlots(m)" :key="si">
                    <span v-if="slot.kind === 'sep'" class="dim-sep">{{ slot.text }}</span>
                    <span v-else-if="slot.kind === 'locked'" class="badge dim-locked">{{ slot.text }}</span>
                    <InlineInput
                      v-else
                      numeric
                      type="number"
                      class="dim-input-inline"
                      :modelValue="rowDims[m.id]?.[slot.field!] ?? null"
                      :data-testid="`inline-dim-${slot.field}-${m.id}`"
                      step="0.1"
                      min="0"
                      @update:modelValue="(v) => { rowDims[m.id]![slot.field!] = v as number | null }"
                      @blur="saveRowDims(m)"
                      @keydown.enter.prevent="saveRowDims(m)"
                      @keydown.esc="initRowDims(m)"
                    />
                  </template>
                </div>
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
                <div class="wt-cell">
                  <span>{{ m.weight_kg != null ? formatNumber(m.weight_kg, 3) + ' kg' : '—' }}</span>
                  <span
                    v-if="m.weight_source"
                    :class="['badge', 'wsrc-badge', m.weight_source === 'catalog' ? 'wsrc-catalog' : 'wsrc-volume']"
                    :title="m.weight_source === 'catalog' ? 'Váha z katalogu (conv_factor)' : 'Váha z objemu (hustota × objem)'"
                  >{{ m.weight_source === 'catalog' ? 'katalog' : 'objem' }}</span>
                </div>
              </td>
              <td class="r">
                <span class="badge price-val">{{ formatCurrency(m.cost_per_piece) }}</span>
              </td>
              <td>
                <button
                  class="icon-btn"
                  :class="{ 'icon-btn-brand': expandedId === m.id }"
                  :data-testid="`expand-mat-${m.id}`"
                  title="Vazby na operace"
                  @click="toggleExpand(m.id)"
                >
                  <ChevronDownIcon :size="ICON_SIZE_SM" :class="['expand-icon', { 'expanded': expandedId === m.id }]" />
                </button>
              </td>
            </tr>

            <!-- Detail row — operation links -->
            <tr v-if="expandedId === m.id" :data-testid="`detail-row-${m.id}`">
              <td colspan="7" class="detail-td">
                <div class="detail-panel">
                  <div class="detail-title">Vazby na operace</div>
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
                    <InlineSelect
                      :modelValue="selectedOpId !== null ? String(selectedOpId) : ''"
                      class="op-select"
                      :data-testid="`op-select-${m.id}`"
                      @update:modelValue="selectedOpId = $event ? Number($event) : null"
                    >
                      <option value="" disabled>Vyberte operaci…</option>
                      <option v-for="op in availableOps" :key="op.id" :value="String(op.id)">
                        {{ op.seq }}. {{ op.name }}
                      </option>
                    </InlineSelect>
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
  transition: opacity 150ms var(--ease);
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
.mod-label { font-size: var(--fsm); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

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
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t2);
  font-size: var(--fs);
 
  outline: none;
  transition: border-color 120ms var(--ease), background 120ms var(--ease), color 120ms var(--ease);
}
.parse-input:focus { border-color: var(--b3); background: rgba(255,255,255,0.07); color: var(--t1); }
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
  font-size: var(--fsm);
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

/* ─── Table rows ─── */
.mat-row:hover td { background: rgba(255,255,255,0.025); }
.mat-row.saving { opacity: 0.6; }
.row-expanded td { background: rgba(255,255,255,0.03); }
.detail-td { padding: 0; }

.t4 { color: var(--t4); }
.fsl { font-size: var(--fsm); }

.mat-name { font-weight: 500; color: var(--t1); }
.mat-code {
  display: inline-block;
  font-size: var(--fsm);
  color: var(--t2);
  background: var(--b1);
  border: 1px solid var(--b2);
  padding: 1px 5px;
  border-radius: var(--rs);
  margin-top: 2px;
}
.mat-sub { font-size: var(--fsm); margin-top: 1px; color: var(--t4); }
.mat-shape { font-size: var(--fsm); color: var(--t3); margin-bottom: 3px; }

/* ─── Inline dims ─── */
.inline-dims {
  display: flex;
  align-items: center;
  gap: 3px;
  flex-wrap: nowrap;
}
.dim-sep {
  font-size: var(--fsm);
  color: var(--t4);
 
  white-space: nowrap;
}
/* dim-locked: catalog-locked dimension display — extends global .badge */
.dim-locked {
 
  color: var(--t3);
  border-color: var(--b2);
  border-radius: var(--rs);
  white-space: nowrap;
}
/* dim-input-inline: size + mono overrides on top of InlineInput .ii base styles */
.dim-input-inline {
  width: 52px;
  height: 20px;
  padding: 0 4px;
  font-size: var(--fsm);
 
  text-align: right;
}
/* Remove number input spinners */
.dim-input-inline::-webkit-inner-spin-button,
.dim-input-inline::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
.dim-input-inline[type=number] { -moz-appearance: textfield; }

/* ─── Expand button icon rotation ─── */
.expand-icon { transition: transform 150ms var(--ease); }
.expand-icon.expanded { transform: rotate(180deg); }

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

/* price-val: pricing value — extends global .badge */
.price-val { color: var(--green); }

/* ─── Weight cell with source badge ─── */
.wt-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}
.wsrc-badge {
  font-size: var(--fss);
  padding: 0px 4px;
}
.wsrc-catalog { color: var(--ok); }
.wsrc-volume  { color: var(--t4); }

/* ─── Detail panel (operation links) ─── */
.detail-panel {
  padding: 8px var(--pad);
  background: var(--raised);
  border-top: 1px solid var(--b2);
  border-bottom: 1px solid var(--b2);
}
.detail-title {
  font-size: var(--fsm);
  font-weight: 600;
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
}

/* ─── Op list in detail panel ─── */
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
.add-op-btn { margin-top: 2px; }
/* op-select: size override on top of InlineSelect .is base styles */
.op-select {
  flex: 1;
  height: 28px;
  padding: 0 6px;
}
</style>
