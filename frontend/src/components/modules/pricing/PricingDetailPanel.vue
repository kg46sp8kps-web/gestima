<script setup lang="ts">
/**
 * Pricing Detail Panel Component
 * Displays batches list with cost breakdown and management actions
 */
import { ref, computed, watch, nextTick } from 'vue'
import { useBatchesStore } from '@/stores/batches'
import type { Batch } from '@/types/batch'
import type { LinkingGroup } from '@/stores/windows'
import { DollarSign, Trash2, Snowflake, BarChart3 } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import Tooltip from '@/components/ui/Tooltip.vue'
import { formatPrice } from '@/utils/formatters'

interface Props {
  partId: number | null
  linkingGroup?: LinkingGroup
}

const props = withDefaults(defineProps<Props>(), {
  linkingGroup: null
})

const emit = defineEmits<{
  'batches-updated': [batches: Batch[]]
}>()

const batchesStore = useBatchesStore()

// State
const showDetailModal = ref(false)
const showDeleteConfirm = ref(false)
const selectedBatch = ref<Batch | null>(null)
const batchToDelete = ref<Batch | null>(null)
const newQuantity = ref<number>(100)
const saving = ref(false)
const emptyInputRef = ref<HTMLInputElement | null>(null)
const ribbonInputRef = ref<HTMLInputElement | null>(null)

// Computed from store
const batchSets = computed(() => {
  const ctx = batchesStore.getContext(props.linkingGroup)
  return ctx.batchSets
})
const selectedSet = computed(() => batchesStore.getSelectedSet(props.linkingGroup))
const displayedBatches = computed(() => batchesStore.getDisplayedBatches(props.linkingGroup))
const loading = computed(() => {
  const ctx = batchesStore.getContext(props.linkingGroup)
  return ctx.loading || ctx.batchesLoading
})
const initialLoading = computed(() => {
  const ctx = batchesStore.getContext(props.linkingGroup)
  return ctx.initialLoading
})

// Dropdown options for sets
const setOptions = computed(() => {
  const options: Array<{ value: number | null; label: string; status: 'draft' | 'frozen' }> = [
    { value: null, label: 'Aktivní (rozpracováno)', status: 'draft' }
  ]

  // Add frozen sets
  batchSets.value
    .filter(s => s.status === 'frozen')
    .forEach(s => {
      options.push({
        value: s.id,
        label: s.name,
        status: 'frozen'
      })
    })

  return options
})

// Frozen sets count
const frozenSetsCount = computed(() => {
  return batchSets.value.filter(s => s.status === 'frozen').length
})

// Calculate bar percentages (only for base costs: material, coop, setup, machining)
function getBarPercentages(batch: Batch) {
  const baseCost = batch.material_cost + batch.coop_cost + batch.setup_cost + batch.machining_cost
  if (baseCost === 0) return { material: 0, coop: 0, setup: 0, machining: 0 }

  return {
    material: (batch.material_cost / baseCost) * 100,
    coop: (batch.coop_cost / baseCost) * 100,
    setup: (batch.setup_cost / baseCost) * 100,
    machining: (batch.machining_cost / baseCost) * 100
  }
}

// Add batch inline (Enter key or button)
async function addBatchInline() {
  if (!props.partId || !newQuantity.value || newQuantity.value < 1) return

  saving.value = true
  try {
    await batchesStore.createBatch(newQuantity.value, props.linkingGroup)
    newQuantity.value = 100 // Reset to default
  } catch (error) {
    // Error handled in store
  } finally {
    saving.value = false
    // Keep focus and select content after save completes
    await nextTick()
    if (ribbonInputRef.value) {
      ribbonInputRef.value.focus()
      ribbonInputRef.value.select()
    }
  }
}

// Expand batch detail
function expandBatch(batch: Batch) {
  selectedBatch.value = batch
  showDetailModal.value = true
}

// Delete
function confirmDelete(batch: Batch) {
  batchToDelete.value = batch
  showDeleteConfirm.value = true
}

async function executeDelete() {
  if (!batchToDelete.value) return

  saving.value = true
  try {
    await batchesStore.deleteBatch(batchToDelete.value, props.linkingGroup)
    showDeleteConfirm.value = false
    batchToDelete.value = null
  } catch (error) {
    // Error handled in store
  } finally {
    saving.value = false
  }
}

// Select batch set
function onSelectSet(setId: number | null) {
  batchesStore.selectSet(setId, props.linkingGroup)
}

// Freeze current active set (loose batches)
async function freezeActiveSet() {
  if (displayedBatches.value.length === 0) return

  saving.value = true
  try {
    await batchesStore.freezeLooseBatchesAsSet(props.linkingGroup)
    // Stay on active set (don't switch to frozen one)
    batchesStore.selectSet(null, props.linkingGroup)
  } catch (error) {
    // Error handled in store
  } finally {
    saving.value = false
  }
}

// Recalculate batches
async function recalculateBatches() {
  if (!props.partId) return

  saving.value = true
  try {
    await batchesStore.recalculateBatches(props.linkingGroup)
  } catch (error) {
    // Error handled in store
  } finally {
    saving.value = false
  }
}

// Watch partId changes (works for both linked AND standalone mode)
watch(() => props.partId, async (newPartId) => {
  if (newPartId) {
    const ctx = batchesStore.getContext(props.linkingGroup)
    if (ctx.currentPartId !== newPartId) {
      await batchesStore.setPartContext(newPartId, props.linkingGroup)
    }
  }
}, { immediate: true })

// Emit batches updates
watch(displayedBatches, (newBatches) => {
  emit('batches-updated', newBatches)
}, { immediate: true })
</script>

<template>
  <div class="pricing-detail-panel">
    <!-- Loading (only on first load — no flash on part switch) -->
    <div v-if="initialLoading" class="loading">
      <div class="spinner"></div>
      <p>Načítám kalkulaci...</p>
    </div>

    <!-- Empty -->
    <div v-else-if="displayedBatches.length === 0 && batchSets.length === 0 && !loading" class="empty">
      <DollarSign :size="ICON_SIZE.HERO" class="empty-icon" />
      <p>Žádné cenové dávky</p>
      <p class="hint">Přidejte první dávku pro výpočet ceny</p>
      <div class="empty-add">
        <input
          ref="emptyInputRef"
          v-model.number="newQuantity"
          type="number"
          class="empty-input"
          min="1"
          placeholder="100"
          @keyup.enter="addBatchInline"
          :disabled="!partId || saving"
          v-select-on-focus
        />
        <button class="btn-primary" @click="addBatchInline" :disabled="!partId || saving || !newQuantity">
          + Přidat
        </button>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div v-else class="main-grid">
      <!-- Top Ribbon: Set Selector + Info + Actions -->
      <div class="info-panel">
        <div class="panel-content">
          <!-- Batch Set Selector -->
          <div class="set-selector">
            <label class="set-label">Sada cen:</label>
            <select
              :value="selectedSet?.id ?? null"
              @change="onSelectSet(($event.target as HTMLSelectElement).value === '' ? null : Number(($event.target as HTMLSelectElement).value))"
              class="set-dropdown"
            >
              <option
                v-for="option in setOptions"
                :key="option.value ?? 'active'"
                :value="option.value ?? ''"
              >
                {{ option.label }}
              </option>
            </select>
          </div>

          <!-- Left side: Frozen Sets Count -->
          <div class="panel-left">
            <div class="sets-count">
              <span class="sets-label">Sady:</span>
              <span class="sets-value">{{ frozenSetsCount }}</span>
            </div>
          </div>

          <!-- Right side: Add batch + Freeze button (always rendered to prevent layout shift) -->
          <div class="panel-right">
            <div
              class="add-batch-inline"
              :class="{ 'hidden-no-layout-shift': selectedSet !== null && selectedSet.status === 'frozen' }"
            >
              <label class="add-label">Nová dávka (ks)</label>
              <div class="add-input-row">
                <input
                  ref="ribbonInputRef"
                  v-model.number="newQuantity"
                  type="number"
                  class="add-input"
                  min="1"
                  placeholder="100"
                  @keyup.enter="addBatchInline"
                  :disabled="!partId || saving"
                  v-select-on-focus
                />
                <button
                  class="add-btn"
                  @click="addBatchInline"
                  :disabled="!partId || saving || !newQuantity || newQuantity < 1"
                >
                  +
                </button>
              </div>
            </div>
            <Tooltip
              text="Zmrazit sadu"
              :class="{ 'hidden-no-layout-shift': selectedSet !== null && selectedSet.status === 'frozen' }"
            >
              <button
                class="freeze-btn"
                @click="freezeActiveSet"
                :disabled="!partId || saving || displayedBatches.length === 0"
              >
                <Snowflake :size="ICON_SIZE.STANDARD" :stroke-width="2" class="freeze-icon" />
              </button>
            </Tooltip>
          </div>
        </div>
      </div>

      <!-- Batches List -->
      <div class="batches-list">
      <!-- Batches Table -->
      <div class="batches-table-wrapper">
        <table class="batches-table">
          <thead>
            <tr>
              <th class="col-qty">ks</th>
              <th class="col-cost">Materiál</th>
              <th class="col-cost">Koop</th>
              <th class="col-breakdown">Rozklad nákladů</th>
              <th class="col-cost">Práce</th>
              <th class="col-cost">Režie</th>
              <th class="col-cost">Marže</th>
              <th class="col-price">Cena/ks</th>
              <th v-if="selectedSet === null || selectedSet.status === 'draft'" class="col-actions">Akce</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="batch in displayedBatches" :key="batch.id">
              <td class="col-qty">
                <span class="qty-value">{{ batch.quantity }}</span>
              </td>
              <td class="col-cost">{{ formatPrice(batch.material_cost) }}</td>
              <td class="col-cost">{{ formatPrice(batch.coop_cost) }}</td>
              <td class="col-breakdown">
                <div class="cost-bar">
                  <div
                    class="cost-segment material"
                    :style="{ width: getBarPercentages(batch).material + '%' }"
                    :title="`Materiál: ${formatPrice(batch.material_cost)} Kč (${getBarPercentages(batch).material.toFixed(1)}%)`"
                  ></div>
                  <div
                    v-if="batch.coop_cost > 0"
                    class="cost-segment coop"
                    :style="{ width: getBarPercentages(batch).coop + '%' }"
                    :title="`Kooperace: ${formatPrice(batch.coop_cost)} Kč (${getBarPercentages(batch).coop.toFixed(1)}%)`"
                  ></div>
                  <div
                    class="cost-segment setup"
                    :style="{ width: getBarPercentages(batch).setup + '%' }"
                    :title="`Seřízení: ${formatPrice(batch.setup_cost)} Kč (${getBarPercentages(batch).setup.toFixed(1)}%)`"
                  ></div>
                  <div
                    class="cost-segment machining"
                    :style="{ width: getBarPercentages(batch).machining + '%' }"
                    :title="`Obrábění: ${formatPrice(batch.machining_cost)} Kč (${getBarPercentages(batch).machining.toFixed(1)}%)`"
                  ></div>
                </div>
              </td>
              <td class="col-cost">{{ formatPrice(batch.machining_cost + batch.setup_cost) }}</td>
              <td class="col-cost">{{ formatPrice(batch.overhead_cost) }}</td>
              <td class="col-cost">{{ formatPrice(batch.margin_cost) }}</td>
              <td class="col-price price-highlight">{{ formatPrice(batch.unit_cost) }} Kč</td>
              <td v-if="selectedSet === null || selectedSet.status === 'draft'" class="col-actions">
                <button
                  class="action-btn"
                  @click="confirmDelete(batch)"
                  title="Smazat dávku"
                >
                  <Trash2 :size="ICON_SIZE.SMALL" />
                </button>
                <button
                  class="action-btn"
                  @click="expandBatch(batch)"
                  title="Detail"
                >
                  <BarChart3 :size="ICON_SIZE.SMALL" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      </div>
    </div>

    <!-- Batch Detail Modal -->
    <Teleport to="body">
      <div v-if="showDetailModal && selectedBatch" class="modal-overlay" @click.self="showDetailModal = false">
        <div class="modal-content modal-wide">
          <h3>Detail dávky: {{ selectedBatch.quantity }} ks</h3>

          <div class="detail-grid">
            <div class="detail-section">
              <h4>Ceny</h4>
              <div class="detail-row">
                <span class="label">Cena za kus:</span>
                <span class="value">{{ formatPrice(selectedBatch.unit_cost) }} Kč</span>
              </div>
              <div class="detail-row">
                <span class="label">Celková cena:</span>
                <span class="value">{{ formatPrice(selectedBatch.total_cost) }} Kč</span>
              </div>
              <div class="detail-row">
                <span class="label">Množství:</span>
                <span class="value">{{ selectedBatch.quantity }} ks</span>
              </div>
              <div class="detail-row">
                <span class="label">Čas na kus:</span>
                <span class="value">{{ selectedBatch.unit_time_min.toFixed(2) }} min</span>
              </div>
            </div>

            <div class="detail-section">
              <h4>Rozklad nákladů</h4>
              <div class="cost-detail-list">
                <div class="cost-detail-item">
                  <span class="dot material"></span>
                  <span class="label">Materiál:</span>
                  <span class="value">{{ formatPrice(selectedBatch.material_cost) }} Kč</span>
                  <span class="percent">({{ selectedBatch.material_percent.toFixed(1) }}%)</span>
                </div>
                <div class="cost-detail-item">
                  <span class="dot machining"></span>
                  <span class="label">Obrábění:</span>
                  <span class="value">{{ formatPrice(selectedBatch.machining_cost) }} Kč</span>
                  <span class="percent">({{ selectedBatch.machining_percent.toFixed(1) }}%)</span>
                </div>
                <div class="cost-detail-item">
                  <span class="dot setup"></span>
                  <span class="label">Seřízení:</span>
                  <span class="value">{{ formatPrice(selectedBatch.setup_cost) }} Kč</span>
                  <span class="percent">({{ selectedBatch.setup_percent.toFixed(1) }}%)</span>
                </div>
                <div class="cost-detail-item">
                  <span class="dot overhead"></span>
                  <span class="label">Režie:</span>
                  <span class="value">{{ formatPrice(selectedBatch.overhead_cost) }} Kč</span>
                  <span class="percent">({{ selectedBatch.overhead_percent.toFixed(1) }}%)</span>
                </div>
                <div class="cost-detail-item">
                  <span class="dot margin"></span>
                  <span class="label">Marže:</span>
                  <span class="value">{{ formatPrice(selectedBatch.margin_cost) }} Kč</span>
                  <span class="percent">({{ selectedBatch.margin_percent.toFixed(1) }}%)</span>
                </div>
                <div v-if="selectedBatch.coop_cost > 0" class="cost-detail-item">
                  <span class="dot coop"></span>
                  <span class="label">Kooperace:</span>
                  <span class="value">{{ formatPrice(selectedBatch.coop_cost) }} Kč</span>
                  <span class="percent">({{ selectedBatch.coop_percent.toFixed(1) }}%)</span>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-actions">
            <button class="btn-secondary" @click="showDetailModal = false">Zavřít</button>
          </div>
        </div>
      </div>
    </Teleport>


    <!-- Delete Confirmation -->
    <Teleport to="body">
      <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
        <div class="modal-content">
          <h3>Smazat dávku?</h3>
          <p>Opravdu chcete smazat dávku pro <strong>{{ batchToDelete?.quantity }} ks</strong>?</p>
          <div class="modal-actions">
            <button class="btn-secondary" @click="showDeleteConfirm = false">Zrušit</button>
            <button class="btn-danger" @click="executeDelete">Smazat</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.pricing-detail-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  overflow: hidden;
  padding: 12px;
}

/* Loading */
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 24px;
  color: var(--t3);
}

/* Empty */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--pad);
  padding: 24px;
  color: var(--t3);
  text-align: center;
}

.empty-icon {
  color: var(--t3);
}

.hint {
  font-size: var(--fs);
  margin-top: 0;
}

.empty-add {
  display: flex;
  gap: 6px;
  margin-top: var(--pad);
}

.empty-input {
  width: 100px;
  padding: 6px;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  background: var(--ground);
  color: var(--t1);
  text-align: center;
  font-size: var(--fs);
}

.empty-input:focus {
  outline: none;
  border-color: rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.03);
}

/* Add Batch Inline */
.add-batch-inline {
  display: flex;
  align-items: center;
  gap: 6px;
}

.add-label {
  font-size: var(--fs);
  color: var(--t3);
  white-space: nowrap;
  font-weight: 500;
}

.add-input-row {
  display: flex;
  gap: 6px;
}

.add-input {
  width: 100px;
  padding: 6px;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  background: var(--ground);
  color: var(--t1);
  font-size: var(--fs);
  text-align: center;
}

.add-input:focus {
  outline: none;
  border-color: rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.03);
}

.add-btn {
  padding: 6px var(--pad);
  background: transparent;
  color: var(--t1);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  font-size: var(--fs);
  font-weight: 700;
  cursor: pointer;
  transition: all 100ms var(--ease);
}

.add-btn:hover:not(:disabled) {
  background: var(--red-10);
  border-color: var(--red);
  color: var(--red);
}

.add-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Main Grid Layout */
.main-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

/* Info Panel (top ribbon) */
.info-panel {
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--surface);
  border-radius: var(--r);
  padding: var(--pad) 12px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.panel-content {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 12px;
  align-items: center;
}

/* Set Selector */
.set-selector {
  display: flex;
  align-items: center;
  gap: 6px;
}

.set-label {
  font-size: var(--fs);
  color: var(--t3);
  white-space: nowrap;
  font-weight: 500;
}

.set-dropdown {
  padding: 6px;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  background: var(--ground);
  color: var(--t1);
  font-size: var(--fs);
  min-width: 180px;
  cursor: pointer;
}

.set-dropdown:focus {
  outline: none;
  border-color: rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.03);
}

/* Panel Left (Sets Count) */
.panel-left {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.sets-count {
  display: flex;
  gap: 6px;
  align-items: center;
}

.sets-label {
  color: var(--t3);
  font-size: var(--fs);
  font-weight: 500;
  white-space: nowrap;
}

.sets-value {
  font-weight: 600;
  font-size: var(--fs);
  color: var(--red);
}

/* Panel Right (Add Batch + Freeze) */
.panel-right {
  display: flex;
  align-items: center;
  gap: var(--pad);
  justify-content: flex-end;
}

/* Hidden but maintains layout space (prevents grid shift) */
.hidden-no-layout-shift {
  visibility: hidden;
  pointer-events: none;
}

/* Batches List */
.batches-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.info-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px 12px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--fs);
  gap: 6px;
}

.stat-label {
  color: var(--t3);
}

.stat-value {
  font-weight: 600;
  color: var(--t1);
}

.stat-value.highlight {
  color: var(--red);
}

.stat-value.frozen {
  color: var(--ok);
}

.panel-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px var(--pad);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  background: var(--surface);
  color: var(--t1);
  font-size: var(--fs);
  font-weight: 500;
  cursor: pointer;
  transition: all 100ms var(--ease);
  white-space: nowrap;
}

.panel-btn:hover:not(:disabled) {
  background: var(--b1);
  border-color: var(--red);
}

.panel-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Freeze button (icon only) */
.freeze-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: var(--r);
  cursor: pointer;
  transition: all 100ms var(--ease);
}

.freeze-btn:hover:not(:disabled) {
  background: rgba(37,99,235,0.1);
}

.freeze-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.freeze-icon {
  color: var(--t3);
}

.freeze-btn:hover:not(:disabled) .freeze-icon {
  color: var(--t3);
}

/* Batches Table */
.batches-table-wrapper {
  overflow-x: auto;
}

.batches-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs);
}

.batches-table th,
.batches-table td {
  padding: var(--pad);
  text-align: left;
  border-bottom: 1px solid var(--b2);
}

.batches-table th {
  position: sticky;
  top: 0;
  background: var(--surface);
  font-weight: 600;
  font-size: var(--fs);
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  z-index: 2;
  box-shadow: 0 1px 0 var(--b2);
}

.batches-table tr:hover {
  background: var(--b1);
}

.batches-table tr.is-frozen {
  background: rgba(52,211,153,0.1);
}

.batches-table tr.is-default {
  background: rgba(37,99,235,0.1);
}

.col-qty {
  width: 80px;
  text-align: right;
  font-weight: 600;
}

.col-cost {
  width: 100px;
  text-align: right;
  color: var(--t3);
  font-size: var(--fs);
}

.col-price {
  width: 120px;
  text-align: right;
  font-weight: 600;
}

.col-actions {
  width: 80px;
  text-align: center;
}

.col-breakdown {
  min-width: 200px;
}

.qty-value {
  font-weight: 600;
}

/* Cost Bar */
.cost-bar {
  display: flex;
  height: 24px;
  border-radius: var(--rs);
  overflow: hidden;
  background: var(--raised);
}

.cost-segment {
  height: 100%;
  transition: all 100ms var(--ease);
}

.cost-segment.material {
  background: var(--chart-wages);
}

.cost-segment.coop {
  background: var(--chart-setup);
}

.cost-segment.setup {
  background: var(--chart-material);
}

.cost-segment.machining {
  background: var(--chart-revenue);
}

.cost-segment.overhead {
  background: var(--chart-expenses);
}

.cost-segment.margin {
  background: var(--chart-energy);
}

.price-highlight {
  color: var(--red);
}

.action-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: var(--fs);
  padding: 4px;
  opacity: 0.7;
  transition: all 100ms var(--ease);
}

.action-btn:hover {
  opacity: 1;
}

.action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* Modal */

.modal-wide {
  max-width: 600px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 20px;
}

.required {
  color: var(--err);
}

/* Detail Modal */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.detail-section h4 {
  margin: 0 0 var(--pad) 0;
  font-size: var(--fs);
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid var(--b2);
}

.detail-row .label {
  color: var(--t3);
  font-size: var(--fs);
}

.detail-row .value {
  font-weight: 600;
  color: var(--t1);
}

.cost-detail-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cost-detail-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px;
  background: var(--raised);
  border-radius: var(--rs);
  font-size: var(--fs);
}

.cost-detail-item .label {
  flex: 1;
  color: var(--t3);
}

.cost-detail-item .value {
  font-weight: 600;
  color: var(--t1);
}

.cost-detail-item .percent {
  color: var(--t3);
  font-size: var(--fs);
}
</style>
