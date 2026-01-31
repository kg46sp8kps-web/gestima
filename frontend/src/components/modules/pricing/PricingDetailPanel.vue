<script setup lang="ts">
/**
 * Pricing Detail Panel Component
 * Displays batches list with cost breakdown and management actions
 */
import { ref, computed, watch, nextTick } from 'vue'
import { useBatchesStore } from '@/stores/batches'
import type { Batch } from '@/types/batch'
import type { LinkingGroup } from '@/stores/windows'
import { DollarSign, Trash2, Snowflake, RefreshCw, BarChart3 } from 'lucide-vue-next'

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

// Format price
function formatPrice(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return '0,00'
  return value.toLocaleString('cs-CZ', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

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
    // Keep focus on input for quick consecutive additions
    await nextTick()
    // Focus on ribbon input (the one in the main view)
    await nextTick() // Double nextTick to ensure DOM is fully updated
    ribbonInputRef.value?.focus()
  } catch (error) {
    // Error handled in store
  } finally {
    saving.value = false
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
    <!-- Loading -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Načítám kalkulaci...</p>
    </div>

    <!-- Empty -->
    <div v-else-if="displayedBatches.length === 0 && batchSets.length === 0" class="empty">
      <DollarSign :size="48" class="empty-icon" />
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

          <!-- Inline Add Batch (only for active set) -->
          <div v-if="selectedSet === null || selectedSet.status === 'draft'" class="add-batch-inline">
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

          <!-- Actions (only for active set) -->
          <div v-if="selectedSet === null || selectedSet.status === 'draft'" class="panel-actions">
            <button
              class="panel-btn"
              @click="recalculateBatches"
              :disabled="!partId || saving || displayedBatches.length === 0"
            >
              <RefreshCw :size="14" />
              Přepočítat
            </button>
            <button
              class="panel-btn freeze-all"
              @click="freezeActiveSet"
              :disabled="!partId || saving || displayedBatches.length === 0"
            >
              <Snowflake :size="14" />
              Zmrazit sadu
            </button>
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
              <th class="col-cost">Cena práce</th>
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
                  <Trash2 :size="16" />
                </button>
                <button
                  class="action-btn"
                  @click="expandBatch(batch)"
                  title="Detail"
                >
                  <BarChart3 :size="16" />
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
                <span class="value">{{ formatPrice(selectedBatch.unit_price) }} Kč</span>
              </div>
              <div class="detail-row">
                <span class="label">Celková cena:</span>
                <span class="value">{{ formatPrice(selectedBatch.total_cost) }} Kč</span>
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
  gap: var(--space-4);
  height: 100%;
  overflow-y: auto;
  padding: var(--space-4);
}

/* Loading */
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-8);
  color: var(--text-secondary);
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-default);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Empty */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-8);
  color: var(--text-tertiary);
  text-align: center;
}

.empty-icon {
  color: var(--text-secondary);
}

.hint {
  font-size: var(--text-sm);
  margin-top: 0;
}

.empty-add {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

.empty-input {
  width: 100px;
  padding: var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-input);
  color: var(--text-primary);
  text-align: center;
  font-size: var(--text-base);
}

.empty-input:focus {
  outline: none;
  border-color: var(--state-focus-border);
  background: var(--state-focus-bg);
}

/* Add Batch Inline */
.add-batch-inline {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.add-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  white-space: nowrap;
  font-weight: var(--font-medium);
}

.add-input-row {
  display: flex;
  gap: var(--space-2);
}

.add-input {
  width: 100px;
  padding: var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: var(--text-sm);
  text-align: center;
}

.add-input:focus {
  outline: none;
  border-color: var(--state-focus-border);
  background: var(--state-focus-bg);
}

.add-btn {
  padding: var(--space-2) var(--space-3);
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  cursor: pointer;
  transition: var(--transition-fast);
}

.add-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.add-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Main Grid Layout */
.main-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  height: 100%;
}

/* Info Panel (top ribbon) */
.info-panel {
  background: var(--bg-raised);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
}

.panel-content {
  display: grid;
  grid-template-columns: 200px 180px auto;
  gap: var(--space-6);
  align-items: center;
}

/* Set Selector */
.set-selector {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.set-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  white-space: nowrap;
  font-weight: var(--font-medium);
}

.set-dropdown {
  padding: var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: var(--text-sm);
  min-width: 180px;
  cursor: pointer;
}

.set-dropdown:focus {
  outline: none;
  border-color: var(--state-focus-border);
  background: var(--state-focus-bg);
}

/* Batches List */
.batches-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  overflow-y: auto;
}

.info-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2) var(--space-4);
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--text-sm);
  gap: var(--space-2);
}

.stat-label {
  color: var(--text-secondary);
}

.stat-value {
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.stat-value.highlight {
  color: var(--color-primary);
}

.stat-value.frozen {
  color: var(--palette-success);
}

.panel-actions {
  display: flex;
  gap: var(--space-2);
}

.panel-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: var(--transition-fast);
  white-space: nowrap;
}

.panel-btn:hover:not(:disabled) {
  background: var(--state-hover);
  border-color: var(--color-primary);
}

.panel-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.panel-btn.freeze-all {
  background: rgba(5, 150, 105, 0.1);
  border-color: var(--palette-success);
  color: var(--palette-success);
}

.panel-btn.freeze-all:hover:not(:disabled) {
  background: rgba(5, 150, 105, 0.2);
}

/* Batches Table */
.batches-table-wrapper {
  overflow-x: auto;
}

.batches-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-base);
}

.batches-table th,
.batches-table td {
  padding: var(--space-3);
  text-align: left;
  border-bottom: 1px solid var(--border-default);
}

.batches-table th {
  background: var(--bg-raised);
  font-weight: var(--font-semibold);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.batches-table tr:hover {
  background: var(--state-hover);
}

.batches-table tr.is-frozen {
  background: rgba(5, 150, 105, 0.05);
}

.batches-table tr.is-default {
  background: rgba(37, 99, 235, 0.05);
}

.col-qty {
  width: 80px;
  text-align: right;
  font-weight: var(--font-semibold);
}

.col-cost {
  width: 100px;
  text-align: right;
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.col-price {
  width: 120px;
  text-align: right;
  font-weight: var(--font-semibold);
}

.col-actions {
  width: 80px;
  text-align: center !important;
}

.col-breakdown {
  min-width: 200px;
}

.qty-value {
  font-weight: var(--font-semibold);
}

/* Cost Bar */
.cost-bar {
  display: flex;
  height: 24px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--bg-raised);
}

.cost-segment {
  height: 100%;
  transition: var(--transition-fast);
}

.cost-segment.material {
  background: #8b5cf6; /* Purple */
}

.cost-segment.coop {
  background: #f59e0b; /* Orange */
}

.cost-segment.setup {
  background: #3b82f6; /* Blue */
}

.cost-segment.machining {
  background: #10b981; /* Green */
}

.cost-segment.overhead {
  background: #ef4444; /* Red */
}

.cost-segment.margin {
  background: #06b6d4; /* Cyan */
}

.price-highlight {
  color: var(--color-primary);
}

.action-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: var(--text-base);
  padding: var(--space-1);
  opacity: 0.7;
  transition: var(--transition-fast);
}

.action-btn:hover {
  opacity: 1;
}

.action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}


/* Buttons (from design system) */
.btn-primary,
.btn-secondary,
.btn-danger {
  padding: var(--space-2) var(--space-4);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: var(--transition-fast);
}

.btn-sm {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
}

.btn-primary {
  background: var(--color-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-raised);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

.btn-secondary:hover {
  background: var(--state-hover);
}

.btn-danger {
  background: var(--palette-danger-dark);
  color: white;
}

.btn-danger:hover {
  background: var(--palette-danger-hover);
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-surface);
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  max-width: 400px;
  width: 90%;
  box-shadow: var(--shadow-lg);
}

.modal-wide {
  max-width: 600px;
}

.modal-content h3 {
  margin: 0 0 var(--space-4) 0;
  color: var(--text-primary);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-6);
}

.form-group {
  margin-bottom: var(--space-4);
}

.form-group label {
  display: block;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  margin-bottom: var(--space-1);
}

.required {
  color: var(--color-danger);
}

.form-input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  background: var(--bg-input);
  color: var(--text-primary);
  transition: var(--transition-fast);
}

.form-input:focus {
  outline: none;
  border-color: var(--state-focus-border);
  background: var(--state-focus-bg);
}

/* Detail Modal */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-6);
}

.detail-section h4 {
  margin: 0 0 var(--space-3) 0;
  font-size: var(--text-base);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border-default);
}

.detail-row .label {
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.detail-row .value {
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.cost-detail-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.cost-detail-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  background: var(--bg-raised);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}

.cost-detail-item .label {
  flex: 1;
  color: var(--text-secondary);
}

.cost-detail-item .value {
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.cost-detail-item .percent {
  color: var(--text-tertiary);
  font-size: var(--text-xs);
}
</style>
