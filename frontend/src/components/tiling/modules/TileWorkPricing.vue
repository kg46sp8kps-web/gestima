<script setup lang="ts">
import { ref, computed, reactive, watch, nextTick } from 'vue'
import { Plus, RefreshCw, Lock, Copy, Trash2, ChevronDown, ChevronRight, BarChart2 } from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import BatchBreakdownModal from '@/components/tiling/modules/BatchBreakdownModal.vue'
import { usePartsStore } from '@/stores/parts'
import { useOperationsStore } from '@/stores/operations'
import { useItemTypeGuard } from '@/composables/useItemTypeGuard'
import { useDialog } from '@/composables/useDialog'
import { useUiStore } from '@/stores/ui'
import * as batchSetsApi from '@/api/batch-sets'
import * as batchesApi from '@/api/batches'
import type { BatchSet } from '@/types/batch-set'
import type { Batch } from '@/types/batch'
import type { ContextGroup } from '@/types/workspace'
import { formatCurrency, formatNumber } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'
import InlineInput from '@/components/ui/InlineInput.vue'
import { ICON_SIZE_SM } from '@/config/design'

interface Props {
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const parts = usePartsStore()
const ops = useOperationsStore()
const typeGuard = useItemTypeGuard(['part'])
const dialog = useDialog()
const ui = useUiStore()

const part = computed(() => parts.getFocusedPart(props.ctx))

// State
const batchSets = ref<BatchSet[]>([])
const batches = ref<Batch[]>([])
const loading = ref(false)
const error = ref(false)
const expandedSetId = ref<number | null>(null)
const newQtyBySet = reactive<Record<number, string | null>>({})
const newLooseQty = ref<string | null>('')
const submitting = reactive<Record<string, boolean>>({})

// Breakdown modal state
const breakdownOpen = ref(false)
const breakdownPartNumber = ref('')
const breakdownQuantity = ref(1)

function openBreakdown(b: Batch) {
  if (!part.value) return
  breakdownPartNumber.value = part.value.part_number
  breakdownQuantity.value = b.quantity
  breakdownOpen.value = true
}

// Computed
const batchesBySetId = computed(() => {
  const map = new Map<number, Batch[]>()
  for (const b of batches.value) {
    if (b.batch_set_id !== null) {
      if (!map.has(b.batch_set_id)) map.set(b.batch_set_id, [])
      map.get(b.batch_set_id)!.push(b)
    }
  }
  for (const arr of map.values()) arr.sort((a, b) => a.quantity - b.quantity)
  return map
})

const looseBatches = computed(() =>
  batches.value.filter(b => b.batch_set_id === null).sort((a, b) => a.quantity - b.quantity),
)

// Auto-recalculate: signature of ops for current part (id:updated_at pairs)
const opsKey = computed(() => {
  if (!part.value) return null
  const list = ops.byPartId[part.value.id]
  if (!list) return null
  return list.map(o => `${o.id}:${o.updated_at}`).join('|')
})

watch(opsKey, async (newKey, oldKey) => {
  // Skip initial load (oldKey null = ops just loaded for the first time)
  if (!newKey || !oldKey) return
  if (!part.value) return
  try {
    await batchesApi.recalculateByPartId(part.value.id)
    batches.value = await batchesApi.getByPartId(part.value.id)
  } catch {
    // silently ignore — user can recalculate manually
  }
})


const isBusy = computed(() => Object.values(submitting).some(v => v))

function pct(value: number): string {
  return formatNumber(value, 1) + ' %'
}

// Data loading
async function loadData(partId: number) {
  loading.value = true
  error.value = false
  try {
    const [setsResult, batchesResult] = await Promise.all([
      batchSetsApi.getByPartId(partId),
      batchesApi.getByPartId(partId),
    ])
    batchSets.value = setsResult
    batches.value = batchesResult
  } catch {
    error.value = true
    batchSets.value = []
    batches.value = []
  } finally {
    loading.value = false
  }
}

watch(
  part,
  (p) => {
    if (!p) { batchSets.value = []; batches.value = []; return }
    loadData(p.id)
  },
  { immediate: true },
)

// Actions
async function createSet() {
  if (!part.value) return
  const key = 'create-set'
  if (submitting[key]) return
  submitting[key] = true
  try {
    const newSet = await batchSetsApi.create(part.value.id)
    batchSets.value = [newSet, ...batchSets.value]
    expandedSetId.value = newSet.id
    ui.showSuccess('Sada cen vytvořena')
  } catch {
    ui.showError('Nepodařilo se vytvořit sadu')
  } finally {
    submitting[key] = false
  }
}

async function recalculateSet(setId: number) {
  const key = `recalc-${setId}`
  if (submitting[key]) return
  submitting[key] = true
  try {
    const result = await batchSetsApi.recalculate(setId)
    for (const b of result.batches) {
      const idx = batches.value.findIndex(x => x.id === b.id)
      if (idx >= 0) batches.value[idx] = b
    }
    const setItem = batchSets.value.find(s => s.id === setId)
    if (setItem) setItem.status = result.status
    ui.showSuccess('Přepočítáno')
  } catch {
    ui.showError('Přepočet selhal')
  } finally {
    submitting[key] = false
  }
}

async function freezeSet(set: BatchSet) {
  const confirmed = await dialog.confirm({
    title: 'Zmrazit sadu?',
    message: `Sada ${set.name} bude zmrazena. Ceny nelze poté měnit.`,
    confirmLabel: 'Zmrazit',
    dangerous: true,
  })
  if (!confirmed) return
  const key = `freeze-${set.id}`
  submitting[key] = true
  try {
    const result = await batchSetsApi.freeze(set.id)
    for (const b of result.batches) {
      const idx = batches.value.findIndex(x => x.id === b.id)
      if (idx >= 0) batches.value[idx] = b
    }
    const setItem = batchSets.value.find(s => s.id === set.id)
    if (setItem) setItem.status = result.status
    ui.showSuccess('Sada zmrazena')
  } catch {
    ui.showError('Zmrazení selhalo')
  } finally {
    submitting[key] = false
  }
}

async function cloneSet(setId: number) {
  const key = `clone-${setId}`
  if (submitting[key]) return
  submitting[key] = true
  try {
    const newSet = await batchSetsApi.clone(setId)
    if (part.value) await loadData(part.value.id)
    expandedSetId.value = newSet.id
    ui.showSuccess('Sada klonována')
  } catch {
    ui.showError('Klonování selhalo')
  } finally {
    submitting[key] = false
  }
}

async function deleteSet(set: BatchSet) {
  const confirmed = await dialog.confirm({
    title: 'Smazat sadu?',
    message: `Sada "${set.name}" a všechny její dávky budou smazány.`,
    confirmLabel: 'Smazat',
    dangerous: true,
  })
  if (!confirmed) return
  const key = `delete-${set.id}`
  submitting[key] = true
  try {
    await batchSetsApi.remove(set.id)
    batches.value = batches.value.filter(b => b.batch_set_id !== set.id)
    batchSets.value = batchSets.value.filter(s => s.id !== set.id)
    if (expandedSetId.value === set.id) expandedSetId.value = null
    ui.showSuccess('Sada smazána')
  } catch {
    ui.showError('Smazání selhalo')
  } finally {
    submitting[key] = false
  }
}

async function addBatch(setId: number) {
  const qty = parseInt(newQtyBySet[setId] ?? '', 10)
  if (!qty || qty <= 0 || isNaN(qty)) { ui.showError('Zadejte platné množství'); return }
  const key = `add-${setId}`
  if (submitting[key]) return
  submitting[key] = true
  try {
    const newBatch = await batchSetsApi.addBatch(setId, qty)
    batches.value = [...batches.value, newBatch]
    newQtyBySet[setId] = null
    const setItem = batchSets.value.find(s => s.id === setId)
    if (setItem) setItem.batch_count = (setItem.batch_count ?? 0) + 1
    ui.showSuccess(`Dávka ${qty} ks přidána`)
    await nextTick()
    const input = document.querySelector<HTMLInputElement>(`[data-testid="add-qty-${setId}"]`)
    input?.focus()
  } catch {
    ui.showError('Nepodařilo se přidat dávku')
  } finally {
    submitting[key] = false
  }
}

async function removeBatch(setId: number, batch: Batch) {
  const confirmed = await dialog.confirm({
    title: 'Odebrat dávku?',
    message: `Dávka ${formatNumber(batch.quantity, 0)} ks bude odstraněna ze sady.`,
    confirmLabel: 'Odebrat',
    dangerous: true,
  })
  if (!confirmed) return
  const key = `rm-${batch.id}`
  submitting[key] = true
  try {
    await batchSetsApi.removeBatch(setId, batch.id)
    batches.value = batches.value.filter(b => b.id !== batch.id)
    const setItem = batchSets.value.find(s => s.id === setId)
    if (setItem) setItem.batch_count = Math.max(0, (setItem.batch_count ?? 1) - 1)
  } catch {
    ui.showError('Nepodařilo se odebrat dávku')
  } finally {
    submitting[key] = false
  }
}

async function createLooseBatch() {
  if (!part.value) return
  const qty = parseInt(newLooseQty.value ?? '', 10)
  if (!qty || qty <= 0 || isNaN(qty)) { ui.showError('Zadejte platné množství'); return }
  const key = 'new-loose'
  if (submitting[key]) return
  submitting[key] = true
  try {
    const newBatch = await batchesApi.create({ part_id: part.value.id, quantity: qty })
    batches.value = [...batches.value, newBatch]
    newLooseQty.value = null
    ui.showSuccess(`Dávka ${qty} ks vytvořena`)
  } catch {
    ui.showError('Nepodařilo se vytvořit dávku')
  } finally {
    submitting[key] = false
  }
}

async function freezeLooseBatches() {
  if (!part.value) return
  const confirmed = await dialog.confirm({
    title: 'Zmrazit volné dávky jako sadu?',
    message: `${looseBatches.value.length} dávek bude zmrazeno do nové sady cen.`,
    confirmLabel: 'Zmrazit',
    dangerous: true,
  })
  if (!confirmed) return
  const key = 'freeze-loose'
  submitting[key] = true
  try {
    const result = await batchSetsApi.freezeLooseBatches(part.value.id)
    for (const b of result.batches) {
      const idx = batches.value.findIndex(x => x.id === b.id)
      if (idx >= 0) batches.value[idx] = b
    }
    batchSets.value = [result, ...batchSets.value]
    ui.showSuccess('Sada vytvořena a zmrazena')
  } catch {
    ui.showError('Zmrazení selhalo')
  } finally {
    submitting[key] = false
  }
}

function toggleExpand(setId: number) {
  expandedSetId.value = expandedSetId.value === setId ? null : setId
}
</script>

<template>
  <div class="wprc">
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
    <div v-else-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>

    <!-- Data view -->
    <template v-else>
      <!-- Header ribbon -->
      <div class="rib">
        <span class="rib-l">Sad</span>
        <span class="rib-v">{{ batchSets.length }}</span>
        <div class="rib-gap" />
        <Spinner v-if="isBusy" size="sm" inline />
        <Button
          variant="secondary"
          :disabled="!!submitting['create-set']"
          data-testid="pricing-create-set-btn"
          @click="createSet"
        >
          <Plus :size="ICON_SIZE_SM" />
          Nová sada
        </Button>
      </div>

      <!-- Empty state -->
      <div v-if="!batchSets.length && !looseBatches.length" class="mod-placeholder">
        <div class="mod-dot" />
        <span class="mod-label">Žádné dávky ani sady cen</span>
      </div>

      <!-- Batch sets list -->
      <div v-if="batchSets.length" class="sets-wrap">
        <div v-for="set in batchSets" :key="set.id" class="set-block">
          <!-- Set header row -->
          <div
            class="set-hdr"
            :data-testid="`set-hdr-${set.id}`"
            @click="toggleExpand(set.id)"
          >
            <component
              :is="expandedSetId === set.id ? ChevronDown : ChevronRight"
              :size="ICON_SIZE_SM"
              class="chevron"
            />
            <span class="set-num">{{ set.set_number }}</span>
            <span class="set-name">{{ set.name }}</span>
            <span :class="['status-pill', set.status]">
              {{ set.status === 'frozen' ? 'ZAM' : 'DRAFT' }}
            </span>
            <span class="set-cnt">{{ set.batch_count }} ks</span>
            <!-- Add batch inline (draft only) -->
            <div v-if="set.status !== 'frozen'" class="hdr-add" @click.stop>
              <InlineInput
                type="number"
                min="1"
                placeholder="qty"
                class="qty-input"
                :modelValue="newQtyBySet[set.id] ?? null"
                :data-testid="`add-qty-${set.id}`"
                @update:modelValue="newQtyBySet[set.id] = $event != null ? String($event) : null"
                @keydown.enter.prevent="addBatch(set.id)"
              />
              <button
                class="icon-btn"
                title="Přidat dávku"
                :disabled="!!submitting[`add-${set.id}`]"
                :data-testid="`add-batch-${set.id}`"
                @click="addBatch(set.id)"
              >
                <Plus :size="ICON_SIZE_SM" />
              </button>
            </div>
            <div class="set-actions" @click.stop>
              <button
                class="icon-btn"
                title="Přepočítat"
                :disabled="set.status === 'frozen' || !!submitting[`recalc-${set.id}`]"
                :data-testid="`recalc-set-${set.id}`"
                @click="recalculateSet(set.id)"
              >
                <RefreshCw :size="ICON_SIZE_SM" />
              </button>
              <button
                class="icon-btn"
                title="Zmrazit"
                :disabled="set.status === 'frozen' || !!submitting[`freeze-${set.id}`]"
                :data-testid="`freeze-set-${set.id}`"
                @click="freezeSet(set)"
              >
                <Lock :size="ICON_SIZE_SM" />
              </button>
              <button
                class="icon-btn"
                title="Klonovat sadu"
                :disabled="!!submitting[`clone-${set.id}`]"
                :data-testid="`clone-set-${set.id}`"
                @click="cloneSet(set.id)"
              >
                <Copy :size="ICON_SIZE_SM" />
              </button>
              <button
                class="icon-btn icon-btn-danger"
                title="Smazat sadu"
                :disabled="!!submitting[`delete-${set.id}`]"
                :data-testid="`delete-set-${set.id}`"
                @click="deleteSet(set)"
              >
                <Trash2 :size="ICON_SIZE_SM" />
              </button>
            </div>
          </div>

          <!-- Expanded: batch table -->
          <template v-if="expandedSetId === set.id">
            <table class="ot set-batches">
              <thead>
                <tr>
                  <th class="r" style="width:68px">Qty (ks)</th>
                  <th class="r" style="width:64px">Mat. %</th>
                  <th class="r" style="width:64px">Seř. %</th>
                  <th class="r" style="width:64px">Stroj. %</th>
                  <th class="r" style="width:94px">Náklady / ks</th>
                  <th class="r" style="width:94px">Cena / ks</th>
                  <th style="width:28px"></th>
                  <th style="width:28px"></th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="b in (batchesBySetId.get(set.id) ?? [])"
                  :key="b.id"
                  :data-testid="`batch-row-${b.id}`"
                >
                  <td class="r">{{ formatNumber(b.quantity, 0) }}</td>
                  <td class="r"><span class="badge pct-mat">{{ pct(b.material_percent) }}</span></td>
                  <td class="r"><span class="badge pct-setup">{{ pct(b.setup_percent) }}</span></td>
                  <td class="r"><span class="badge pct-mach">{{ pct(b.machining_percent) }}</span></td>
                  <td class="r">{{ formatCurrency(b.unit_cost_net) }}</td>
                  <td class="r"><span class="price-val">{{ formatCurrency(b.unit_cost) }}</span></td>
                  <td>
                    <button
                      class="icon-btn"
                      title="Rozpad ceny"
                      :data-testid="`breakdown-btn-${b.id}`"
                      @click="openBreakdown(b)"
                    >
                      <BarChart2 :size="ICON_SIZE_SM" />
                    </button>
                  </td>
                  <td>
                    <button
                      v-if="set.status !== 'frozen'"
                      class="icon-btn icon-btn-danger"
                      title="Odebrat dávku"
                      :disabled="!!submitting[`rm-${b.id}`]"
                      :data-testid="`remove-batch-${b.id}`"
                      @click="removeBatch(set.id, b)"
                    >
                      <Trash2 :size="ICON_SIZE_SM" />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>

          </template>
        </div>
      </div>

      <!-- Loose batches section -->
      <div v-if="looseBatches.length" class="loose-section">
        <div class="section-hdr">
          <span class="section-title">Volné dávky</span>
          <div class="hdr-add">
            <InlineInput
              type="number"
              min="1"
              placeholder="qty"
              class="qty-input"
              :modelValue="newLooseQty"
              data-testid="new-loose-qty"
              @update:modelValue="newLooseQty = $event != null ? String($event) : null"
              @keydown.enter.prevent="createLooseBatch"
            />
            <button
              class="icon-btn"
              title="Přidat dávku"
              :disabled="!!submitting['new-loose']"
              data-testid="create-loose-btn"
              @click="createLooseBatch"
            >
              <Plus :size="ICON_SIZE_SM" />
            </button>
          </div>
          <Button
            variant="secondary"
            :disabled="!!submitting['freeze-loose']"
            data-testid="freeze-loose-btn"
            @click="freezeLooseBatches"
          >
            <Lock :size="ICON_SIZE_SM" />
            Zmrazit jako sadu
          </Button>
        </div>
        <table class="ot">
          <thead>
            <tr>
              <th class="r" style="width:68px">Qty (ks)</th>
              <th class="r" style="width:64px">Mat. %</th>
              <th class="r" style="width:64px">Seř. %</th>
              <th class="r" style="width:64px">Stroj. %</th>
              <th class="r" style="width:94px">Náklady / ks</th>
              <th class="r" style="width:94px">Cena / ks</th>
              <th style="width:28px"></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="b in looseBatches"
              :key="b.id"
              :data-testid="`loose-row-${b.id}`"
            >
              <td class="r">{{ formatNumber(b.quantity, 0) }}</td>
              <td class="r"><span class="badge pct-mat">{{ pct(b.material_percent) }}</span></td>
              <td class="r"><span class="badge pct-setup">{{ pct(b.setup_percent) }}</span></td>
              <td class="r"><span class="badge pct-mach">{{ pct(b.machining_percent) }}</span></td>
              <td class="r">{{ formatCurrency(b.unit_cost_net) }}</td>
              <td class="r"><span class="price-val">{{ formatCurrency(b.unit_cost) }}</span></td>
              <td>
                <button
                  class="icon-btn"
                  title="Rozpad ceny"
                  :data-testid="`breakdown-btn-${b.id}`"
                  @click="openBreakdown(b)"
                >
                  <BarChart2 :size="ICON_SIZE_SM" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- Breakdown modal -->
    <BatchBreakdownModal
      v-model="breakdownOpen"
      :part-number="breakdownPartNumber"
      :quantity="breakdownQuantity"
    />
  </div>
</template>

<style scoped>
.wprc {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow-y: auto;
}

/* ─── Placeholders ─── */
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

/* ─── Header ribbon ─── */
.rib {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.rib-gap { flex: 1; }
.rib-l { font-size: var(--fsm); color: var(--t4); text-transform: uppercase; letter-spacing: 0.05em; }
.rib-v { font-size: var(--fs); color: var(--t1); font-weight: 500; }

/* ─── Batch sets ─── */
.sets-wrap { flex-shrink: 0; }

.set-block {
  border-bottom: 1px solid var(--b1);
}

.set-hdr {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px var(--pad);
  cursor: pointer;
  user-select: none;
}
.set-hdr:hover { background: rgba(255,255,255,0.025); }

.chevron { color: var(--t4); flex-shrink: 0; }
.set-num { font-size: var(--fsm); color: var(--t4); }
.set-name { font-size: var(--fs); color: var(--t2); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.set-cnt { font-size: var(--fsm); color: var(--t4); white-space: nowrap; }

.status-pill {
  font-size: var(--fss);
  font-weight: 600;
  letter-spacing: 0.05em;
  padding: 1px 5px;
  border-radius: var(--rs);
  flex-shrink: 0;
}
.status-pill.draft { background: var(--b2); color: var(--t3); }
.status-pill.frozen { background: rgba(255,255,255,0.06); color: var(--ok); }

.set-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}

/* ─── Expanded batch table ─── */
.set-batches { margin-bottom: 0; }

/* ─── Header inline add ─── */
.hdr-add {
  display: flex;
  align-items: center;
  gap: 2px;
}
/* qty-input: size + mono override on top of InlineInput .ii base styles */
.qty-input {
  width: 44px;
  height: 22px;
  padding: 1px 4px;
  font-size: var(--fsm);
 
  text-align: right;
}
.qty-input::placeholder { font-family: var(--font); }
/* Remove browser spinner arrows */
.qty-input::-webkit-outer-spin-button,
.qty-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.qty-input[type=number] { -moz-appearance: textfield; }

/* ─── Loose section ─── */
.loose-section {
  flex-shrink: 0;
  border-top: 1px solid var(--b1);
}
.section-hdr {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px var(--pad);
  background: rgba(255,255,255,0.015);
}
.section-title {
  font-size: var(--fsm);
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--t3);
  flex: 1;
}

/* pct-*: percent cost breakdown badges — extend global .badge with chart colors */
.pct-mat  { color: var(--chart-material); }
.pct-mach { color: var(--chart-machining); }
.pct-setup { color: var(--chart-setup); }

/* ─── Price value ─── */
.price-val { font-weight: 600; color: var(--green); }

/* ─── Mono ─── */
.mono { }
</style>
