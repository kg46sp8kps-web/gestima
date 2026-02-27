<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue'
import { PlusIcon, Trash2Icon } from 'lucide-vue-next'
import { usePartsStore } from '@/stores/parts'
import { useOperationsStore } from '@/stores/operations'
import { useUiStore } from '@/stores/ui'
import { useItemTypeGuard } from '@/composables/useItemTypeGuard'
import { useDialog } from '@/composables/useDialog'
import { useWorkCentersStore } from '@/stores/workCenters'
import * as materialInputsApi from '@/api/material-inputs'
import * as materialsApi from '@/api/materials'
import type { ContextGroup } from '@/types/workspace'
import type { Operation } from '@/types/operation'
import type { WorkCenter } from '@/types/work-center'
import type {
  MaterialInput,
  MaterialInputCreate,
  MaterialInputUpdate,
  ParseResult,
  StockShape,
  SuggestedMaterialItem,
} from '@/types/material-input'
import { formatCurrency, formatNumber } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'
import WcCombobox from '@/components/ui/WcCombobox.vue'
import Input from '@/components/ui/Input.vue'
import InlineInput from '@/components/ui/InlineInput.vue'
import InlineSelect from '@/components/ui/InlineSelect.vue'
import OperationCombobox from '@/components/ui/OperationCombobox.vue'
import { ICON_SIZE_SM } from '@/config/design'

const _materialCache = new Map<number, MaterialInput[]>()
const _materialFetchedFor = new Map<string, number>()

interface Props {
  leafId: string
  ctx: ContextGroup
}

interface OpDraft {
  setup_time_min: number | null
  operation_time_min: number | null
  work_center_id: number | null
  ke: number
  ko: number
}

interface DimSlot {
  kind: 'sep' | 'locked' | 'editable'
  text?: string
  field?: string
}

type PriceCat = { id: number; code: string; name: string; shape: string | null }

const props = defineProps<Props>()
const parts = usePartsStore()
const ops = useOperationsStore()
const ui = useUiStore()
const typeGuard = useItemTypeGuard(['part'])
const dialog = useDialog()
const wcStore = useWorkCentersStore()

const part = computed(() => parts.getFocusedPart(props.ctx))

const operations = computed(() => {
  if (!part.value) return []
  return ops.forPart(part.value.id)
})

const drafts = reactive<Record<number, OpDraft>>({})
const activeOpId = ref<number | null>(null)
const openDetails = ref(new Set<number>())

const wcComboRefs = ref<Record<number, { focus: () => void }>>({})
const optimeRefs = ref<Record<number, HTMLInputElement>>({})
const keRefs = ref<Record<number, HTMLInputElement>>({})
const koRefs = ref<Record<number, HTMLInputElement>>({})
const materialsOpen = ref(true)
const opsOpen = ref(true)

const materialItems = ref<MaterialInput[]>([])
const materialsLoading = ref(false)
const materialsError = ref(false)
const materialsRefetching = computed(() => materialsLoading.value && materialItems.value.length > 0)
const rowDims = reactive<Record<number, Record<string, number | null>>>({})
const savingRowIds = ref<number[]>([])
const showAdd = ref(false)
const parseInput = ref('')
const parsing = ref(false)
const parseResult = ref<ParseResult | null>(null)
const selectedItem = ref<SuggestedMaterialItem | null>(null)
const creating = ref(false)
const manualMode = ref(false)
const manualShape = ref<StockShape | null>(null)
const manualDims = reactive<Record<string, number | null>>({
  stock_diameter: null,
  stock_length: null,
  stock_width: null,
  stock_height: null,
  stock_wall_thickness: null,
})
const manualPriceCategoryId = ref<number | null>(null)
const manualPriceCategoryName = ref<string | null>(null)
const priceCategories = ref<PriceCat[]>([])
const linkingMaterialIds = ref<number[]>([])

const filteredCategories = computed(() => {
  if (!manualShape.value) return priceCategories.value
  return priceCategories.value.filter((c) => !c.shape || c.shape === manualShape.value)
})

const totalWeight = computed(() => materialItems.value.reduce((s, m) => s + (m.weight_kg ?? 0), 0))
const totalCost = computed(() => materialItems.value.reduce((s, m) => s + (m.cost_per_piece ?? 0), 0))

const SHAPE_LABELS: Record<StockShape, string> = {
  round_bar: 'Kulatina',
  square_bar: 'Čtyřhran',
  flat_bar: 'Plochá ocel',
  hexagonal_bar: 'Šestihran',
  plate: 'Plech',
  tube: 'Trubka',
  casting: 'Odlitek',
  forging: 'Výkovek',
}

function d(opId: number): OpDraft {
  return (
    drafts[opId] ?? {
      setup_time_min: 0,
      operation_time_min: 0,
      work_center_id: null,
      ke: 100,
      ko: 100,
    }
  )
}

function initDraft(op: Operation) {
  if (!drafts[op.id]) {
    drafts[op.id] = {
      setup_time_min: op.setup_time_min,
      operation_time_min: op.operation_time_min,
      work_center_id: op.work_center_id,
      ke: op.machine_utilization_coefficient,
      ko: op.manning_coefficient,
    }
  }
}

function resetDraft(op: Operation) {
  drafts[op.id] = {
    setup_time_min: op.setup_time_min,
    operation_time_min: op.operation_time_min,
    work_center_id: op.work_center_id,
    ke: op.machine_utilization_coefficient,
    ko: op.manning_coefficient,
  }
}

async function saveOp(op: Operation) {
  const draft = drafts[op.id]
  if (!draft || !part.value) return
  const setup = draft.setup_time_min == null || isNaN(draft.setup_time_min) ? 0 : draft.setup_time_min
  const optime =
    draft.operation_time_min == null || isNaN(draft.operation_time_min) ? 0 : draft.operation_time_min
  const changed =
    setup !== op.setup_time_min ||
    optime !== op.operation_time_min ||
    draft.work_center_id !== op.work_center_id ||
    draft.ke !== op.machine_utilization_coefficient ||
    draft.ko !== op.manning_coefficient
  if (!changed) return
  draft.setup_time_min = setup
  draft.operation_time_min = optime
  await ops.updateOp(op.id, part.value.id, {
    setup_time_min: setup,
    operation_time_min: optime,
    work_center_id: draft.work_center_id ?? undefined,
    machine_utilization_coefficient: draft.ke,
    manning_coefficient: draft.ko,
    version: op.version,
  })
}

async function onWcSelect(op: Operation, id: number | null) {
  const dr = drafts[op.id]
  if (dr) dr.work_center_id = id
  await saveOp(op)
}

function onEscape(e: KeyboardEvent, op: Operation) {
  e.preventDefault()
  resetDraft(op)
  ;(e.target as HTMLElement).blur()
}

function onTimeInput(e: Event, opId: number, field: 'setup_time_min' | 'operation_time_min') {
  const val = (e.target as HTMLInputElement).value
  const n = parseFloat(val)
  const dr = drafts[opId]
  if (dr) dr[field] = isNaN(n) ? null : n
}

function onCoefInput(e: Event, opId: number, field: 'ke' | 'ko') {
  const val = (e.target as HTMLInputElement).value
  const n = parseFloat(val)
  const dr = drafts[opId]
  if (dr) dr[field] = isNaN(n) ? 100 : n
}

function keTime(draft: OpDraft): number {
  const strojni = draft.operation_time_min ?? 0
  return draft.ke > 0 ? strojni / (draft.ke / 100) : 0
}

function koTime(draft: OpDraft): number {
  return keTime(draft) * (draft.ko / 100)
}

function fmtMmSs(minutes: number): string {
  const totalSeconds = Math.round(minutes * 60)
  const mm = Math.floor(totalSeconds / 60)
  const ss = totalSeconds % 60
  return `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`
}

const PRODUCTION_TYPES = new Set(['CNC_LATHE', 'CNC_MILL_3AX', 'CNC_MILL_4AX', 'CNC_MILL_5AX'])

const wcMap = computed(() => {
  const m: Record<number, WorkCenter> = {}
  for (const wc of wcStore.items) m[wc.id] = wc
  return m
})

function isProductionWc(wcId: number | null): boolean {
  if (wcId == null) return false
  const wc = wcMap.value[wcId]
  return wc != null && PRODUCTION_TYPES.has(wc.work_center_type)
}

const totalSetup = computed(() =>
  operations.value.reduce((s, o) => {
    const wcId = drafts[o.id]?.work_center_id ?? o.work_center_id
    return isProductionWc(wcId) ? s + (drafts[o.id]?.setup_time_min ?? o.setup_time_min) : s
  }, 0),
)

const totalStrojni = computed(() =>
  operations.value.reduce((s, o) => {
    const wcId = drafts[o.id]?.work_center_id ?? o.work_center_id
    return isProductionWc(wcId) ? s + (drafts[o.id]?.operation_time_min ?? o.operation_time_min) : s
  }, 0),
)

const totalKe = computed(() =>
  operations.value.reduce((s, o) => {
    const dr = drafts[o.id]
    const wcId = dr?.work_center_id ?? o.work_center_id
    return dr && isProductionWc(wcId) ? s + keTime(dr) : s
  }, 0),
)

const totalKo = computed(() =>
  operations.value.reduce((s, o) => {
    const dr = drafts[o.id]
    const wcId = dr?.work_center_id ?? o.work_center_id
    return dr && isProductionWc(wcId) ? s + koTime(dr) : s
  }, 0),
)

function toggleDetail(opId: number) {
  const s = new Set(openDetails.value)
  if (s.has(opId)) s.delete(opId)
  else s.add(opId)
  openDetails.value = s
}

function onFocusRow(opId: number) {
  activeOpId.value = opId
}

async function deleteOp(opId: number) {
  const op = operations.value.find((o) => o.id === opId)
  if (!op || !part.value) return
  const confirmed = await dialog.confirm({
    title: 'Smazat operaci',
    message: `Opravdu smazat operaci č. ${op.seq}?`,
    confirmLabel: 'Smazat',
    dangerous: true,
  })
  if (confirmed) {
    await ops.removeOp(op.id, part.value.id)
    if (activeOpId.value === opId) activeOpId.value = null
    const s = new Set(openDetails.value)
    s.delete(opId)
    openDetails.value = s
    delete drafts[opId]
  }
}

async function addOp() {
  if (!part.value) return
  const maxSeq = operations.value.length > 0 ? Math.max(...operations.value.map((o) => o.seq)) : 0
  const newOp = await ops.createOp({
    part_id: part.value.id,
    seq: maxSeq + 10,
    manning_coefficient: 100,
    machine_utilization_coefficient: 100,
  })
  if (newOp) {
    await nextTick()
    wcComboRefs.value[newOp.id]?.focus()
  }
}

async function onEnterLastField(op: Operation) {
  await saveOp(op)
  await addOp()
}

function handleCtrlD() {
  if (activeOpId.value != null) deleteOp(activeOpId.value)
}

function focusOptime(opId: number) {
  optimeRefs.value[opId]?.focus()
}

function focusKe(opId: number) {
  keRefs.value[opId]?.focus()
}

function focusKo(opId: number) {
  koRefs.value[opId]?.focus()
}

function toggleMaterials() {
  materialsOpen.value = !materialsOpen.value
}

function toggleOps() {
  opsOpen.value = !opsOpen.value
}

function toNum(v: unknown): number | null {
  if (v === null || v === undefined || v === '') return null
  const n = Number(v)
  return isNaN(n) ? null : n
}

function initRowDims(m: MaterialInput) {
  rowDims[m.id] = {
    stock_diameter: m.stock_diameter,
    stock_length: m.stock_length,
    stock_width: m.stock_width,
    stock_height: m.stock_height,
    stock_wall_thickness: m.stock_wall_thickness,
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

function materialShortRef(m: MaterialInput): string {
  return m.material_item?.code ?? m.material_item?.material_number ?? `M${m.seq + 1}`
}

function operationCrossMetaMap(currentMaterialId: number): Record<number, string> {
  const map: Record<number, string> = {}
  for (const m of materialItems.value) {
    if (m.id === currentMaterialId) continue
    const ref = materialShortRef(m)
    for (const op of m.operations) {
      if (!map[op.id]) map[op.id] = `M: ${ref}`
    }
  }
  return map
}

const materialsByOperation = computed(() => {
  const map: Record<number, MaterialInput[]> = {}
  for (const m of materialItems.value) {
    for (const op of m.operations) {
      const bucket = map[op.id] ?? (map[op.id] = [])
      bucket.push(m)
    }
  }
  return map
})

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
      if (mi?.width != null) slots.push({ kind: 'locked', text: `${mi.width}` })
      else slots.push({ kind: 'editable', field: 'stock_width' })
      slots.push({ kind: 'sep', text: '×' })
      if (mi?.thickness != null) slots.push({ kind: 'locked', text: `${mi.thickness}` })
      else slots.push({ kind: 'editable', field: 'stock_height' })
      slots.push({ kind: 'sep', text: '×' })
      slots.push({ kind: 'editable', field: 'stock_length' })
      slots.push({ kind: 'sep', text: 'mm' })
      break
    }
    case 'plate': {
      if (mi?.width != null) slots.push({ kind: 'locked', text: `${mi.width}` })
      else slots.push({ kind: 'editable', field: 'stock_width' })
      slots.push({ kind: 'sep', text: '×' })
      if (mi?.height != null) slots.push({ kind: 'locked', text: `${mi.height}` })
      else slots.push({ kind: 'editable', field: 'stock_height' })
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
      slots.push({ kind: 'editable', field: 'stock_length' })
      slots.push({ kind: 'sep', text: 'mm' })
      break
    }
  }
  return slots
}

function manualDimSlots(shape: StockShape): DimSlot[] {
  const slots: DimSlot[] = []
  switch (shape) {
    case 'round_bar':
    case 'hexagonal_bar': {
      const sym = shape === 'round_bar' ? '∅' : '⬡'
      slots.push({ kind: 'sep', text: sym })
      slots.push({ kind: 'editable', field: 'stock_diameter' })
      slots.push({ kind: 'sep', text: '×' })
      slots.push({ kind: 'editable', field: 'stock_length' })
      slots.push({ kind: 'sep', text: 'mm' })
      break
    }
    case 'square_bar': {
      slots.push({ kind: 'sep', text: '□' })
      slots.push({ kind: 'editable', field: 'stock_width' })
      slots.push({ kind: 'sep', text: '×' })
      slots.push({ kind: 'editable', field: 'stock_length' })
      slots.push({ kind: 'sep', text: 'mm' })
      break
    }
    case 'flat_bar': {
      slots.push({ kind: 'editable', field: 'stock_width' })
      slots.push({ kind: 'sep', text: '×' })
      slots.push({ kind: 'editable', field: 'stock_height' })
      slots.push({ kind: 'sep', text: '×' })
      slots.push({ kind: 'editable', field: 'stock_length' })
      slots.push({ kind: 'sep', text: 'mm' })
      break
    }
    case 'plate': {
      slots.push({ kind: 'editable', field: 'stock_wall_thickness' })
      slots.push({ kind: 'sep', text: 'mm tl. ×' })
      slots.push({ kind: 'editable', field: 'stock_width' })
      slots.push({ kind: 'sep', text: '×' })
      slots.push({ kind: 'editable', field: 'stock_height' })
      slots.push({ kind: 'sep', text: 'mm' })
      break
    }
    case 'tube': {
      slots.push({ kind: 'sep', text: '∅' })
      slots.push({ kind: 'editable', field: 'stock_diameter' })
      slots.push({ kind: 'sep', text: ' t' })
      slots.push({ kind: 'editable', field: 'stock_wall_thickness' })
      slots.push({ kind: 'sep', text: '×' })
      slots.push({ kind: 'editable', field: 'stock_length' })
      slots.push({ kind: 'sep', text: 'mm' })
      break
    }
    case 'casting':
    case 'forging': {
      slots.push({ kind: 'editable', field: 'stock_length' })
      slots.push({ kind: 'sep', text: 'mm' })
      break
    }
  }
  return slots
}

async function saveRowDims(m: MaterialInput) {
  const dims = rowDims[m.id]
  if (!dims) return
  const changed =
    toNum(dims.stock_diameter) !== m.stock_diameter ||
    toNum(dims.stock_length) !== m.stock_length ||
    toNum(dims.stock_width) !== m.stock_width ||
    toNum(dims.stock_height) !== m.stock_height ||
    toNum(dims.stock_wall_thickness) !== m.stock_wall_thickness
  if (!changed) return
  savingRowIds.value = [...savingRowIds.value, m.id]
  try {
    const payload: MaterialInputUpdate = {
      stock_diameter: toNum(dims.stock_diameter),
      stock_length: toNum(dims.stock_length),
      stock_width: toNum(dims.stock_width),
      stock_height: toNum(dims.stock_height),
      stock_wall_thickness: toNum(dims.stock_wall_thickness),
      version: m.version,
    }
    const updated = await materialInputsApi.update(m.id, payload)
    const idx = materialItems.value.findIndex((x) => x.id === m.id)
    if (idx >= 0) {
      materialItems.value[idx] = updated
      _materialCache.set(part.value!.id, [...materialItems.value])
      initRowDims(updated)
    }
  } catch {
    ui.showError('Chyba při ukládání rozměrů')
    initRowDims(m)
  } finally {
    savingRowIds.value = savingRowIds.value.filter((id) => id !== m.id)
  }
}

async function enterManualMode() {
  manualMode.value = true
  const pr = parseResult.value
  if (pr) {
    manualShape.value = pr.shape
    manualDims.stock_diameter = pr.diameter
    manualDims.stock_length = pr.length
    manualDims.stock_width = pr.width
    manualDims.stock_height = pr.height
    manualDims.stock_wall_thickness = pr.wall_thickness ?? pr.thickness ?? null
    manualPriceCategoryId.value = pr.suggested_price_category_id
    manualPriceCategoryName.value = pr.suggested_price_category_name
  }
  if (!priceCategories.value.length) {
    try {
      const cats = await materialsApi.getPriceCategories()
      priceCategories.value = cats
    } catch {}
  }
}

function exitManualMode() {
  manualMode.value = false
  manualShape.value = null
  Object.keys(manualDims).forEach((k) => {
    manualDims[k] = null
  })
  manualPriceCategoryId.value = null
  manualPriceCategoryName.value = null
}

function onManualCatChange(v: string) {
  const found = priceCategories.value.find((c) => c.id === Number(v))
  manualPriceCategoryId.value = found?.id ?? null
  manualPriceCategoryName.value = found?.name ?? null
}

async function confirmManualCreate() {
  if (!manualShape.value || !manualPriceCategoryId.value || !part.value) return
  creating.value = true
  try {
    const payload: MaterialInputCreate = {
      part_id: part.value.id,
      price_category_id: manualPriceCategoryId.value,
      material_item_id: null,
      stock_shape: manualShape.value,
      stock_diameter: manualDims.stock_diameter,
      stock_length: manualDims.stock_length,
      stock_width: manualDims.stock_width,
      stock_height: manualDims.stock_height,
      stock_wall_thickness: manualDims.stock_wall_thickness,
      quantity: 1,
      seq: materialItems.value.length,
    }
    await materialInputsApi.create(payload)
    _materialFetchedFor.delete(props.leafId)
    materialsLoading.value = true
    materialItems.value = await materialInputsApi.getByPartId(part.value.id)
    materialItems.value.forEach(initRowDims)
    _materialCache.set(part.value.id, [...materialItems.value])
    showAdd.value = false
    parseInput.value = ''
    parseResult.value = null
    exitManualMode()
    ui.showSuccess('Materiál přidán')
  } catch {
    ui.showError('Chyba při vytváření materiálu')
  } finally {
    creating.value = false
    materialsLoading.value = false
  }
}

function toggleAdd() {
  showAdd.value = !showAdd.value
  if (!showAdd.value) {
    parseInput.value = ''
    parseResult.value = null
    exitManualMode()
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
      stock_diameter: pr.diameter ?? null,
      stock_length: pr.length ?? null,
      stock_width: pr.width ?? null,
      stock_height: pr.height ?? null,
      stock_wall_thickness: pr.wall_thickness ?? null,
      quantity: 1,
      seq: materialItems.value.length,
    }
    await materialInputsApi.create(payload)
    _materialFetchedFor.delete(props.leafId)
    materialsLoading.value = true
    materialItems.value = await materialInputsApi.getByPartId(part.value.id)
    materialItems.value.forEach(initRowDims)
    _materialCache.set(part.value.id, [...materialItems.value])
    showAdd.value = false
    parseInput.value = ''
    parseResult.value = null
    ui.showSuccess('Materiál přidán')
  } catch {
    ui.showError('Chyba při vytváření materiálu')
  } finally {
    creating.value = false
    materialsLoading.value = false
  }
}

async function removeMaterial(m: MaterialInput) {
  const confirmed = await dialog.confirm({
    title: 'Odstranit materiál?',
    message: `Materiál "${m.material_item?.name ?? m.price_category?.name ?? m.id}" bude odstraněn z dílu.`,
    confirmLabel: 'Odstranit',
    dangerous: true,
  })
  if (!confirmed) return
  try {
    await materialInputsApi.remove(m.id)
    materialItems.value = materialItems.value.filter((x) => x.id !== m.id)
    if (part.value) _materialCache.set(part.value.id, [...materialItems.value])
    ui.showSuccess('Materiál odstraněn')
  } catch {
    ui.showError('Chyba při odstraňování materiálu')
  }
}

function linkedOperationId(m: MaterialInput): number | null {
  return m.operations[0]?.id ?? null
}

async function onMaterialOperationChange(m: MaterialInput, nextOpId: number | null) {
  const currentOpIds = m.operations.map((x) => x.id)
  const alreadySingleMatch =
    nextOpId != null && currentOpIds.length === 1 && currentOpIds[0] === nextOpId
  const alreadyNone = nextOpId == null && currentOpIds.length === 0
  if (alreadySingleMatch || alreadyNone) return

  linkingMaterialIds.value = [...linkingMaterialIds.value, m.id]
  try {
    for (const opId of currentOpIds) {
      if (nextOpId == null || opId !== nextOpId) {
        await materialInputsApi.unlinkOperation(m.id, opId)
      }
    }
    if (nextOpId != null && !currentOpIds.includes(nextOpId)) {
      await materialInputsApi.linkOperation(m.id, nextOpId)
    }
    if (nextOpId == null) {
      m.operations = []
    } else {
      const selectedOp = operations.value.find((x) => x.id === nextOpId)
      m.operations = selectedOp
        ? [{ id: selectedOp.id, seq: selectedOp.seq, name: selectedOp.name, type: selectedOp.type }]
        : []
    }
    if (part.value) _materialCache.set(part.value.id, [...materialItems.value])
    ui.showSuccess('Vazba operace uložena')
  } catch {
    ui.showError('Chyba při ukládání vazby operace')
  } finally {
    linkingMaterialIds.value = linkingMaterialIds.value.filter((id) => id !== m.id)
  }
}

watch(operations, (list) => list.forEach(initDraft), { immediate: true })

watch(parseInput, () => {
  if (parseResult.value) {
    parseResult.value = null
    selectedItem.value = null
  }
})

watch(manualShape, (newShape) => {
  if (!newShape || !manualPriceCategoryId.value || !priceCategories.value.length) return
  const cat = priceCategories.value.find((c) => c.id === manualPriceCategoryId.value)
  if (cat?.shape && cat.shape !== newShape) {
    manualPriceCategoryId.value = null
    manualPriceCategoryName.value = null
  }
})

watch(
  part,
  async (p) => {
    if (p && !ops.byPartId[p.id]) ops.fetchByPartId(p.id)

    if (!p) {
      materialItems.value = []
      materialsError.value = false
      return
    }

    if (_materialCache.has(p.id)) {
      materialItems.value = _materialCache.get(p.id)!
      materialItems.value.forEach(initRowDims)
    }

    if (_materialFetchedFor.get(props.leafId) === p.id) return
    _materialFetchedFor.set(props.leafId, p.id)

    materialsLoading.value = true
    materialsError.value = false
    try {
      materialItems.value = await materialInputsApi.getByPartId(p.id)
      materialItems.value.forEach(initRowDims)
      _materialCache.set(p.id, [...materialItems.value])
    } catch {
      materialsError.value = true
      _materialFetchedFor.delete(props.leafId)
      if (!materialItems.value.length) materialItems.value = []
    } finally {
      materialsLoading.value = false
    }
  },
  { immediate: true },
)

onMounted(() => {
  wcStore.fetchIfNeeded()
})
</script>

<template>
  <div class="wops">
    <div v-if="!typeGuard.isSupported(props.ctx)" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Nedostupné pro {{ typeGuard.focusedTypeName(props.ctx) }}</span>
    </div>

    <div v-else-if="!part" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Vyberte díl ze seznamu</span>
    </div>

    <template v-else>
      <div class="mat-collapsible">
        <button class="mat-toggle" data-testid="tech-material-toggle" @click="toggleMaterials">
          <span>Materiál</span>
          <span :class="['mat-toggle-chevron', { open: materialsOpen }]">▾</span>
        </button>
        <div v-if="materialsOpen" :class="['mat-body', { refetching: materialsRefetching }]">
          <div class="rib">
            <div class="rib-r">
              <div class="rib-i">
                <span class="rib-l">Materiálů</span>
                <span class="rib-v">{{ materialItems.length }}</span>
              </div>
              <div class="rib-i">
                <span class="rib-l">Hmotnost / ks</span>
                <span class="rib-v">{{ formatNumber(totalWeight, 3) }} kg</span>
              </div>
              <div class="rib-i">
                <span class="rib-l">Náklady / ks</span>
                <span class="rib-v green">{{ formatCurrency(totalCost) }}</span>
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

          <div v-if="showAdd" class="add-form">
            <div class="add-row">
              <Input
                v-model="parseInput"
                bare
                class="parse-input"
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
                <span v-else>Hledat</span>
              </button>
            </div>

            <div v-if="!parseResult && !manualMode && !parsing" class="parse-hint">
              <div class="hint-row"><span class="hint-pat">D20 1,4301 100</span><span class="hint-desc">kulatina ∅20, nerez, délka 100mm</span></div>
              <div class="hint-row"><span class="hint-pat">5083 D20 100</span><span class="hint-desc">hliník AW5083, kulatina ∅20, délka 100mm</span></div>
              <div class="hint-row"><span class="hint-pat">20,30 S235 500</span><span class="hint-desc">plochá ocel 20×30 (čárka místo x), délka 500mm</span></div>
              <div class="hint-row"><span class="hint-pat">t3 1,4301 1000,1500</span><span class="hint-desc">plech 3mm, nerez, rozměr 1000×1500mm</span></div>
              <div class="hint-row"><span class="hint-pat">D20/2 1,4301 100</span><span class="hint-desc">trubka ∅20/2, nerez, délka 100mm</span></div>
            </div>

            <div v-if="parseResult && !manualMode" class="parse-result">
              <div class="pr-meta">
                <span v-if="parseResult.shape" class="pr-chip">{{ SHAPE_LABELS[parseResult.shape] }}</span>
                <span v-if="parseResult.suggested_price_category_name" class="pr-chip">{{ parseResult.suggested_price_category_name }}</span>
                <span :class="['pr-chip', parseResult.confidence > 0.7 ? 'pr-chip-ok' : 'pr-chip-warn']">
                  {{ Math.round(parseResult.confidence * 100) }}%
                </span>
              </div>
              <div v-for="w in parseResult.warnings" :key="w" class="pr-warning">{{ w }}</div>

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

                <button class="pr-item-opt pr-item-manual" data-testid="enter-manual-btn" @click="enterManualMode">
                  <span class="pr-item-opt-name">Zadat ručně</span>
                  <span class="pr-item-opt-code">
                    {{ parseResult.suggested_material_items.length ? 'Bez katalogové položky' : 'Žádné katalogové položky — hodnoty předvyplněny' }}
                  </span>
                </button>
              </div>

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

            <div v-if="manualMode" class="manual-form">
              <div class="manual-row">
                <InlineSelect
                  :modelValue="manualShape ?? ''"
                  class="shape-select"
                  data-testid="manual-shape-select"
                  @update:modelValue="(v) => { manualShape = (v as StockShape) || null }"
                >
                  <option value="" disabled>Tvar…</option>
                  <option v-for="(label, key) in SHAPE_LABELS" :key="key" :value="key">{{ label }}</option>
                </InlineSelect>
                <InlineSelect
                  :modelValue="manualPriceCategoryId ? String(manualPriceCategoryId) : ''"
                  class="cat-select"
                  data-testid="manual-cat-select"
                  @update:modelValue="onManualCatChange"
                >
                  <option value="" disabled>Cenová kategorie…</option>
                  <option v-for="cat in filteredCategories" :key="cat.id" :value="String(cat.id)">{{ cat.name }}</option>
                </InlineSelect>
              </div>
              <div v-if="manualShape" class="manual-dims">
                <template v-for="(slot, si) in manualDimSlots(manualShape)" :key="si">
                  <span v-if="slot.kind === 'sep'" class="dim-sep">{{ slot.text }}</span>
                  <InlineInput
                    v-else
                    numeric
                    type="number"
                    class="dim-input-inline"
                    :modelValue="manualDims[slot.field!] ?? null"
                    :data-testid="`manual-dim-${slot.field}`"
                    step="0.1"
                    min="0"
                    @update:modelValue="(v) => { manualDims[slot.field!] = v as number | null }"
                  />
                </template>
              </div>
              <div class="pr-actions">
                <button
                  class="btn-primary"
                  :disabled="!manualShape || !manualPriceCategoryId || creating"
                  data-testid="confirm-manual-create-btn"
                  @click="confirmManualCreate"
                >
                  <Spinner v-if="creating" size="sm" :inline="true" />
                  <span v-else>Vytvořit materiál</span>
                </button>
                <button class="btn-secondary" data-testid="exit-manual-btn" @click="exitManualMode">Zpět</button>
                <button class="btn-secondary" @click="toggleAdd">Zrušit</button>
              </div>
            </div>
          </div>

          <div v-if="materialsLoading && !materialItems.length" class="mod-placeholder mat-ph">
            <Spinner size="sm" />
          </div>

          <div v-else-if="materialsError" class="mod-placeholder mat-ph">
            <div class="mod-dot" />
            <span class="mod-label">Chyba při načítání materiálů</span>
          </div>

          <div v-else-if="!materialItems.length" class="mod-placeholder mat-ph">
            <div class="mod-dot" />
            <span class="mod-label">Díl nemá žádné materiály</span>
          </div>

          <div v-else class="ot-wrap">
            <table class="ot">
              <thead>
                <tr>
                  <th style="width:24px">#</th>
                  <th>Materiál</th>
                  <th>Rozměry</th>
                  <th>Operace</th>
                  <th class="r" style="width:80px">Hmotnost</th>
                  <th class="r" style="width:100px">Cena / ks</th>
                  <th style="width:32px"></th>
                </tr>
              </thead>
              <tbody v-for="m in materialItems" :key="m.id">
                <tr :class="['mat-row', { saving: savingRowIds.includes(m.id) }]" :data-testid="`mat-row-${m.id}`">
                  <td class="t4">{{ m.seq + 1 }}</td>
                  <td>
                    <div class="mat-name">{{ matPrimary(m) }}</div>
                    <div v-if="m.material_item?.code" class="mat-code">{{ m.material_item.code }}</div>
                    <div v-if="matSub(m)" class="mat-sub t4">{{ matSub(m) }}</div>
                  </td>
                  <td>
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
                    <OperationCombobox
                      :modelValue="linkedOperationId(m)"
                      class="op-bind-wrap"
                      :data-testid="`op-bind-combo-${m.id}`"
                      :options="operations"
                      :meta-by-id="operationCrossMetaMap(m.id)"
                      :disabled="linkingMaterialIds.includes(m.id)"
                      @update:modelValue="onMaterialOperationChange(m, $event)"
                    />
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
                  <td class="r"><span class="badge price-val">{{ formatCurrency(m.cost_per_piece) }}</span></td>
                  <td class="act-cell">
                    <button
                      class="icon-btn icon-btn-danger"
                      :data-testid="`delete-mat-${m.id}`"
                      title="Odstranit materiál"
                      @click="removeMaterial(m)"
                    >
                      <Trash2Icon :size="ICON_SIZE_SM" />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="ops-collapsible">
        <button class="ops-toggle" data-testid="tech-ops-toggle" @click="toggleOps">
          <span>Operace</span>
          <span :class="['ops-toggle-chevron', { open: opsOpen }]">▾</span>
        </button>
        <div v-if="opsOpen" class="ops-block">
          <div v-if="ops.loading && !operations.length" class="mod-placeholder">
            <Spinner size="sm" />
          </div>

          <div v-else-if="!operations.length" class="mod-placeholder">
            <div class="mod-dot" />
            <span class="mod-label">Díl nemá žádné operace</span>
          </div>

          <template v-else>
            <div class="tbl-wrap" @keydown.ctrl.d.prevent="handleCtrlD">
              <table class="ops">
                <thead>
                  <tr>
                    <th style="width: 22px" />
                    <th style="width: 28px">#</th>
                    <th style="width: 160px">Pracoviště</th>
                    <th class="r" style="width: 80px">Seřízení</th>
                    <th class="r" style="width: 84px">Strojní čas</th>
                    <th class="r" style="width: 96px">Ke % <span class="th-sub">· čas stroje</span></th>
                    <th class="r" style="width: 96px">Ko % <span class="th-sub">· obsluha</span></th>
                    <th style="width: 26px" />
                  </tr>
                </thead>
                <tbody>
                  <template v-for="op in operations" :key="op.id">
                    <tr
                      class="op-row"
                      :class="{ act: activeOpId === op.id }"
                      :data-testid="`op-row-${op.id}`"
                      @focusin="onFocusRow(op.id)"
                      @click="onFocusRow(op.id)"
                    >
                      <td class="seq-cell td-icon">
                        <button
                          class="chev"
                          :class="{ open: openDetails.has(op.id) }"
                          :data-testid="`op-chev-${op.id}`"
                          tabindex="-1"
                          @click.stop="toggleDetail(op.id)"
                        >▶</button>
                      </td>

                      <td><span class="seq-num">{{ String(op.seq).padStart(2, '0') }}</span></td>

                      <td>
                        <WcCombobox
                          :ref="(el) => { if (el) wcComboRefs[op.id] = el as unknown as { focus: () => void } }"
                          :modelValue="d(op.id).work_center_id"
                          :options="wcStore.items"
                          :data-testid="`op-wc-${op.id}`"
                          @update:modelValue="onWcSelect(op, $event)"
                        />
                      </td>

                      <td class="r">
                        <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
                        <input
                          v-select-on-focus
                          class="inp num"
                          type="number"
                          step="1"
                          min="0"
                          :value="d(op.id).setup_time_min ?? ''"
                          :data-testid="`op-setup-${op.id}`"
                          @input="onTimeInput($event, op.id, 'setup_time_min')"
                          @blur="saveOp(op)"
                          @keydown.enter.prevent="focusOptime(op.id)"
                          @keydown.escape="onEscape($event, op)"
                        />
                      </td>

                      <td class="r">
                        <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
                        <input
                          :ref="(el) => { if (el) optimeRefs[op.id] = el as HTMLInputElement }"
                          v-select-on-focus
                          class="inp num"
                          type="number"
                          step="1"
                          min="0"
                          :value="d(op.id).operation_time_min ?? ''"
                          :data-testid="`op-optime-${op.id}`"
                          @input="onTimeInput($event, op.id, 'operation_time_min')"
                          @blur="saveOp(op)"
                          @keydown.enter.prevent="focusKe(op.id)"
                          @keydown.escape="onEscape($event, op)"
                        />
                      </td>

                      <td class="r">
                        <div class="coef-cell">
                          <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
                          <input
                            :ref="(el) => { if (el) keRefs[op.id] = el as HTMLInputElement }"
                            v-select-on-focus
                            class="inp num inp-coef"
                            type="number"
                            step="1"
                            min="0"
                            max="200"
                            :value="d(op.id).ke"
                            :data-testid="`op-ke-${op.id}`"
                            @input="onCoefInput($event, op.id, 'ke')"
                            @blur="saveOp(op)"
                            @keydown.enter.prevent="focusKo(op.id)"
                            @keydown.escape="onEscape($event, op)"
                          />
                          <span class="coef-hint ke-hint">{{ fmtMmSs(keTime(d(op.id))) }}</span>
                        </div>
                      </td>

                      <td class="r">
                        <div class="coef-cell">
                          <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
                          <input
                            :ref="(el) => { if (el) koRefs[op.id] = el as HTMLInputElement }"
                            v-select-on-focus
                            class="inp num inp-coef"
                            type="number"
                            step="1"
                            min="0"
                            max="200"
                            :value="d(op.id).ko"
                            :data-testid="`op-ko-${op.id}`"
                            @input="onCoefInput($event, op.id, 'ko')"
                            @blur="saveOp(op)"
                            @keydown.enter.prevent="onEnterLastField(op)"
                            @keydown.escape="onEscape($event, op)"
                          />
                          <span class="coef-hint ko-hint">{{ fmtMmSs(koTime(d(op.id))) }}</span>
                        </div>
                      </td>

                      <td class="td-icon">
                        <button
                          class="del-btn"
                          :data-testid="`op-del-${op.id}`"
                          title="Smazat (Ctrl+D)"
                          tabindex="-1"
                          @click="deleteOp(op.id)"
                        >×</button>
                      </td>
                    </tr>

                    <tr v-show="openDetails.has(op.id)" class="detail-tr">
                      <td colspan="8">
                        <div class="detail-inner">
                          <div class="detail-section">
                            <div class="ds-head">Navázaný materiál</div>
                            <div v-if="materialsByOperation[op.id]?.length" class="ds-mat-list">
                              <div
                                v-for="m in materialsByOperation[op.id]"
                                :key="`op-${op.id}-mat-${m.id}`"
                                class="ds-mat-item"
                              >
                                <span class="badge ds-mat-code">{{ materialShortRef(m) }}</span>
                                <span class="ds-mat-name">{{ matPrimary(m) }}</span>
                              </div>
                            </div>
                            <div v-else class="ds-empty">Bez navázaného materiálu</div>
                          </div>
                          <div class="detail-section">
                            <div class="ds-head">Nástroje</div>
                            <div class="ds-placeholder">Připravujeme…</div>
                          </div>
                          <div class="detail-section">
                            <div class="ds-head">Řezné podmínky</div>
                            <div class="ds-placeholder">Připravujeme…</div>
                          </div>
                          <div class="detail-section">
                            <div class="ds-head">Kroky operace</div>
                            <div class="ds-placeholder">Připravujeme…</div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  </template>

                  <tr class="add-tr">
                    <td colspan="8">
                      <button class="add-btn" data-testid="op-add-btn" @click="addOp">
                        <span class="add-plus">+</span>
                        Přidat operaci
                        <span class="kbd add-hint">↵ z posledního pole</span>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="sum-bar">
              <div class="sum-kpi">
                <span class="sum-label">Σ Seřízení</span>
                <span class="sum-val">{{ fmtMmSs(totalSetup) }}</span>
              </div>
              <div class="sum-kpi">
                <span class="sum-label">Σ Strojní čas</span>
                <span class="sum-val">{{ fmtMmSs(totalStrojni) }}</span>
              </div>
              <div class="sum-kpi">
                <span class="sum-label">Σ Čas stroje</span>
                <span class="sum-val ke-hint">{{ fmtMmSs(totalKe) }}</span>
              </div>
              <div class="sum-kpi">
                <span class="sum-label">Σ Čas obsluhy</span>
                <span class="sum-val ko-hint">{{ fmtMmSs(totalKo) }}</span>
              </div>
            </div>
          </template>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wops {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  gap: 8px;
}

.ops-block {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--surface);
}

.ops-collapsible {
  border-top: 1px solid var(--b2);
  background: var(--surface);
}

.ops-toggle {
  width: 100%;
  border: none;
  background: none;
  color: var(--t2);
  font-size: var(--fsm);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  font-weight: 600;
  padding: 8px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}

.ops-toggle:hover {
  background: var(--b1);
}

.ops-toggle-chevron {
  transition: transform 120ms var(--ease);
}

.ops-toggle-chevron.open {
  transform: rotate(180deg);
}

.mod-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--t4);
}

.mat-ph {
  min-height: 110px;
}

.mod-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--b2);
}

.mod-label {
  font-size: var(--fsm);
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.kbd {
  display: inline-flex;
  align-items: center;
  padding: 1px 5px;
  background: var(--raised);
  border: 1px solid var(--b3);
  border-radius: var(--rs);
  font-size: var(--fss);
  color: var(--t4);
  font-family: var(--font);
  line-height: 1.5;
  white-space: nowrap;
}

.tbl-wrap {
  overflow: visible;
  flex: 1;
  min-height: 0;
}

.ops {
  width: 100%;
  border-collapse: collapse;
}

.ops thead {
  background: transparent;
  border-bottom: 1px solid var(--b2);
}

.ops th {
  padding: 5px 8px;
  font-family: var(--font);
  font-size: var(--fsm);
  font-weight: 400;
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  text-align: left;
  border-bottom: 1px solid var(--b2);
  white-space: nowrap;
}

.ops th.r,
.ot th.r,
.ot td.r,
.op-row td.r {
  text-align: right;
}

.th-sub {
  font-size: var(--fss);
  color: var(--t4);
  margin-left: 3px;
  letter-spacing: 0;
}

.op-row {
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  transition: background 60ms var(--ease);
}

.op-row:hover {
  background: var(--b1);
}

.op-row.act {
  background: rgba(255, 255, 255, 0.035);
}

.op-row.act .seq-cell {
  box-shadow: inset 3px 0 0 var(--red);
}

.op-row td,
.ot td {
  padding: 4px 8px;
  font-size: var(--fs);
  color: var(--t2);
  vertical-align: middle;
  border: none;
}

.op-row td.td-icon {
  padding: 0 4px;
  text-align: center;
}

.op-row:hover .del-btn,
.op-row.act .del-btn {
  opacity: 1;
}

.seq-num {
  font-family: var(--font);
  font-size: var(--fsm);
  color: var(--t4);
  letter-spacing: 0.04em;
  font-variant-numeric: tabular-nums;
}

.op-row.act .seq-num {
  color: var(--red);
}

.chev {
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: var(--fss);
  color: var(--t4);
  background: none;
  border: none;
  border-radius: var(--rs);
  cursor: pointer;
  padding: 0;
  transition: color 80ms var(--ease), background 80ms var(--ease), transform 120ms var(--ease);
}

.chev:hover {
  background: var(--b2);
  color: var(--t3);
}

.chev.open {
  transform: rotate(90deg);
  color: var(--t3);
}

.inp {
  background: var(--b1);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t2);
  font-family: var(--font);
  font-size: var(--fs);
  padding: 3px 6px;
  outline: none;
  width: 100%;
  transition: border-color 80ms var(--ease), background 80ms var(--ease), color 80ms var(--ease);
}

.inp::placeholder {
  color: var(--t4);
  font-size: var(--fss);
}

.inp:focus {
  border-color: var(--b3);
  background: rgba(255, 255, 255, 0.08);
  color: var(--t1);
}

.inp:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.5);
  outline-offset: 2px;
}

.inp.num {
  text-align: right;
  width: 52px;
  font-variant-numeric: tabular-nums;
}

.inp.inp-coef {
  width: 42px;
}

.inp[type='number']::-webkit-outer-spin-button,
.inp[type='number']::-webkit-inner-spin-button,
.dim-input-inline::-webkit-inner-spin-button,
.dim-input-inline::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.inp[type='number'],
.dim-input-inline[type='number'] {
  -moz-appearance: textfield;
}

input::selection {
  background: transparent;
}

.coef-cell {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 5px;
}

.coef-hint {
  font-family: var(--font);
  font-size: var(--fsm);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  min-width: 28px;
  text-align: right;
}

.ke-hint,
.sum-val.ke-hint {
  color: var(--chart-material);
}

.ko-hint,
.sum-val.ko-hint {
  color: var(--chart-machining);
}

.del-btn {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: 1px solid transparent;
  border-radius: var(--rs);
  color: var(--t4);
  cursor: pointer;
  font-size: var(--fs);
  line-height: 1;
  opacity: 0;
  padding: 0;
  transition: opacity 70ms var(--ease), background 70ms var(--ease), color 70ms var(--ease), border-color 70ms var(--ease);
}

.del-btn:hover {
  color: var(--err);
  background: rgba(248, 113, 113, 0.1);
  border-color: rgba(248, 113, 113, 0.25);
}

.add-tr td {
  padding: 0;
  border-top: 1px dashed rgba(255, 255, 255, 0.06);
}

.add-btn {
  width: 100%;
  padding: 6px 12px;
  background: none;
  border: none;
  color: var(--t4);
  font-family: var(--font);
  font-size: var(--fsm);
  font-weight: 600;
  cursor: pointer;
  text-align: left;
  letter-spacing: 0.03em;
  display: flex;
  align-items: center;
  gap: 7px;
  transition: background 80ms var(--ease), color 80ms var(--ease);
}

.add-btn:hover {
  background: var(--b1);
  color: var(--t2);
}

.add-plus {
  font-size: var(--fs);
  line-height: 1;
  color: var(--t3);
}

.add-hint {
  margin-left: auto;
}

.detail-tr {
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.ops tbody .detail-tr td {
  padding: 0;
  background: var(--raised);
}

.detail-inner {
  padding: 12px 10px 14px 50px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.ds-head {
  font-family: var(--font);
  font-size: var(--fsm);
  font-weight: 400;
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--b2);
}

.ds-placeholder {
  font-size: var(--fsm);
  color: var(--t4);
  font-style: italic;
}

.ds-empty {
  font-size: var(--fsm);
  color: var(--t4);
}

.ds-mat-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ds-mat-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.ds-mat-code {
  flex-shrink: 0;
}

.ds-mat-name {
  font-size: var(--fsm);
  color: var(--t2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sum-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--b2);
  border-top: 1px solid var(--b2);
  overflow: hidden;
  flex-shrink: 0;
}

.sum-kpi {
  background: var(--raised);
  padding: 6px 14px;
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.sum-label {
  font-size: var(--fsm);
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  font-weight: 600;
}

.sum-val {
  font-family: var(--font);
  font-size: var(--fs);
  color: var(--t1);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.mat-collapsible {
  border-top: 1px solid var(--b2);
  background: var(--surface);
}

.mat-toggle {
  width: 100%;
  border: none;
  background: none;
  color: var(--t2);
  font-size: var(--fsm);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  font-weight: 600;
  padding: 8px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}

.mat-toggle:hover {
  background: var(--b1);
}

.mat-toggle-chevron {
  transition: transform 120ms var(--ease);
}

.mat-toggle-chevron.open {
  transform: rotate(180deg);
}

.mat-body {
  border-top: 1px solid var(--b2);
  max-height: none;
  overflow: visible;
  transition: opacity 150ms var(--ease);
  background: var(--surface);
}

.mat-body.refetching {
  opacity: 0.45;
}

.rib {
  padding: 6px 8px;
  background: transparent;
  border-bottom: 1px solid var(--b2);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.rib-r {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.rib-i {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.rib-l {
  font-size: var(--fss);
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
}

.rib-v {
  font-size: var(--fs);
  color: var(--t1);
  font-weight: 500;
}

.rib-v.green {
  color: var(--green);
}

.add-active {
  background: var(--red-10);
}

.add-form {
  padding: 8px;
  border-bottom: 1px solid var(--b2);
  background: transparent;
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
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t2);
  font-size: var(--fs);
  outline: none;
  transition: border-color 120ms var(--ease), background 120ms var(--ease), color 120ms var(--ease);
}

.parse-input:focus {
  border-color: var(--b3);
  background: rgba(255, 255, 255, 0.07);
  color: var(--t1);
}

.parse-input::placeholder {
  color: var(--t4);
}

.parse-hint {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.hint-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.hint-pat {
  font-size: var(--fsm);
  color: var(--t2);
  white-space: nowrap;
  min-width: 140px;
  font-family: monospace;
}

.hint-desc {
  font-size: var(--fsm);
  color: var(--t4);
}

.parse-result {
  margin-top: 8px;
}

.pr-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.pr-chip {
  font-size: var(--fsm);
  color: var(--t3);
  background: var(--b1);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  padding: 1px 6px;
}

.pr-chip-ok {
  color: var(--ok);
}

.pr-chip-warn {
  color: var(--warn);
}

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

.pr-item-opt:hover {
  border-color: var(--b3);
}

.pr-item-opt.pr-item-selected {
  border-color: var(--t3);
  background: var(--b1);
}

.pr-item-opt-name {
  font-size: var(--fs);
  color: var(--t1);
}

.pr-item-opt-code {
  font-size: var(--fsm);
  color: var(--t3);
}

.pr-item-manual {
  border-style: dashed;
}

.pr-item-manual .pr-item-opt-name {
  color: var(--t3);
}

.pr-item-manual:hover {
  border-color: var(--t4);
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

.manual-form {
  margin-top: 8px;
}

.manual-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.shape-select {
  height: 26px;
  padding: 0 6px;
}

.cat-select {
  flex: 1;
  min-width: 120px;
  height: 26px;
  padding: 0 6px;
}

.manual-dims,
.inline-dims {
  display: flex;
  align-items: center;
  gap: 3px;
  flex-wrap: nowrap;
}

.manual-dims {
  margin-bottom: 2px;
}

.ot-wrap {
  border-top: 1px solid var(--b2);
  flex: 1;
  overflow: visible;
  min-height: 0;
}

.ot {
  width: 100%;
  border-collapse: collapse;
}

.ot thead {
  background: transparent;
  border-bottom: 1px solid var(--b2);
}

.ot th {
  padding: 5px 8px;
  font-size: var(--fsm);
  font-weight: 400;
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  text-align: left;
  white-space: nowrap;
  border-bottom: 1px solid var(--b2);
}

.mat-row:hover td {
  background: var(--b1);
}

.mat-row.saving {
  opacity: 0.6;
}

.mat-row {
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.t4 {
  color: var(--t4);
}

.fsl {
  font-size: var(--fsm);
}

.mat-name {
  font-weight: 500;
  color: var(--t1);
}

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

.mat-sub {
  font-size: var(--fsm);
  margin-top: 1px;
  color: var(--t4);
}

.dim-sep {
  font-size: var(--fsm);
  color: var(--t4);
  white-space: nowrap;
}

.dim-locked {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 52px;
  height: 24px;
  padding: 0 4px;
  font-size: var(--fs);
  background: var(--b1);
  border: 1px solid var(--b2);
  color: var(--t3);
  border-radius: var(--rs);
  white-space: nowrap;
}

.dim-input-inline {
  width: 52px;
  height: 24px;
  padding: 0 4px;
  font-size: var(--fs);
  background: var(--b1);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t2);
  text-align: right;
}

.op-bind-wrap {
  width: 52px;
  min-width: 52px;
  position: relative;
  z-index: 20;
}

.wt-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.wsrc-badge {
  font-size: var(--fss);
  padding: 0 4px;
}

.wsrc-catalog {
  color: var(--ok);
}

.wsrc-volume {
  color: var(--t4);
}

.price-val {
  color: var(--green);
}

.act-cell {
  text-align: right;
  white-space: nowrap;
}
</style>
