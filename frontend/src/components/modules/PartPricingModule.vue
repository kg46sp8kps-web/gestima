<template>
  <div class="pricing-module">
    <!-- Header -->
    <div class="module-header">
      <h3 v-if="!inline">💰 Kalkulace cen</h3>
      <div class="header-actions">
        <span v-if="displayedBatches.length > 0" class="batches-count">
          {{ displayedBatches.length }} dávek
        </span>
        <button
          class="btn btn-primary btn-sm"
          @click="openAddBatch"
          :disabled="!partId || saving"
        >
          + Přidat dávku
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <span class="spinner"></span>
      Načítám ceny...
    </div>

    <!-- Empty state -->
    <div v-else-if="displayedBatches.length === 0" class="empty-state">
      <div class="empty-icon">💰</div>
      <p>Žádné cenové dávky</p>
      <p class="hint">Přidejte první dávku pro výpočet ceny</p>
    </div>

    <!-- Batches list -->
    <div v-else class="batches-list">
      <!-- Quick summary bar -->
      <div class="summary-bar">
        <div class="summary-stat">
          <span class="stat-label">Počet dávek:</span>
          <span class="stat-value">{{ displayedBatches.length }}</span>
        </div>
        <div class="summary-stat">
          <span class="stat-label">Min. cena/ks:</span>
          <span class="stat-value">{{ formatPrice(minUnitPrice) }} Kč</span>
        </div>
        <div class="summary-stat">
          <span class="stat-label">Max. cena/ks:</span>
          <span class="stat-value">{{ formatPrice(maxUnitPrice) }} Kč</span>
        </div>
      </div>

      <!-- Batches table -->
      <div class="batches-table-wrapper">
        <table class="batches-table">
          <thead>
            <tr>
              <th class="col-qty">Množství</th>
              <th class="col-unit">Cena/ks</th>
              <th class="col-total">Celkem</th>
              <th class="col-breakdown">Rozklad nákladů</th>
              <th class="col-actions">Akce</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="batch in displayedBatches"
              :key="batch.id"
              :class="{ 'is-frozen': batch.is_frozen, 'is-default': batch.is_default }"
            >
              <td class="col-qty">
                <span class="qty-value">{{ batch.quantity }} ks</span>
                <span v-if="batch.is_default" class="default-badge">Výchozí</span>
                <span v-if="batch.is_frozen" class="frozen-badge">🔒</span>
              </td>
              <td class="col-unit">
                <span class="price-main">{{ formatPrice(batch.unit_price) }} Kč</span>
              </td>
              <td class="col-total">
                <span class="price-total">{{ formatPrice(batch.total_cost) }} Kč</span>
              </td>
              <td class="col-breakdown">
                <div class="cost-bar">
                  <div
                    class="cost-segment material"
                    :style="{ width: batch.material_percent + '%' }"
                    :title="`Materiál: ${formatPrice(batch.material_cost)} Kč (${batch.material_percent.toFixed(1)}%)`"
                  ></div>
                  <div
                    class="cost-segment machining"
                    :style="{ width: batch.machining_percent + '%' }"
                    :title="`Obrábění: ${formatPrice(batch.machining_cost)} Kč (${batch.machining_percent.toFixed(1)}%)`"
                  ></div>
                  <div
                    class="cost-segment setup"
                    :style="{ width: batch.setup_percent + '%' }"
                    :title="`Seřízení: ${formatPrice(batch.setup_cost)} Kč (${batch.setup_percent.toFixed(1)}%)`"
                  ></div>
                  <div
                    class="cost-segment overhead"
                    :style="{ width: batch.overhead_percent + '%' }"
                    :title="`Režie: ${formatPrice(batch.overhead_cost)} Kč (${batch.overhead_percent.toFixed(1)}%)`"
                  ></div>
                  <div
                    class="cost-segment margin"
                    :style="{ width: batch.margin_percent + '%' }"
                    :title="`Marže: ${formatPrice(batch.margin_cost)} Kč (${batch.margin_percent.toFixed(1)}%)`"
                  ></div>
                  <div
                    v-if="batch.coop_percent > 0"
                    class="cost-segment coop"
                    :style="{ width: batch.coop_percent + '%' }"
                    :title="`Kooperace: ${formatPrice(batch.coop_cost)} Kč (${batch.coop_percent.toFixed(1)}%)`"
                  ></div>
                </div>
              </td>
              <td class="col-actions">
                <button
                  v-if="!batch.is_frozen"
                  class="action-btn"
                  @click="confirmDelete(batch)"
                  title="Smazat dávku"
                >
                  🗑️
                </button>
                <button
                  class="action-btn"
                  @click="expandBatch(batch)"
                  title="Detail"
                >
                  📊
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Cost legend -->
      <div class="cost-legend">
        <span class="legend-item"><span class="dot material"></span> Materiál</span>
        <span class="legend-item"><span class="dot machining"></span> Obrábění</span>
        <span class="legend-item"><span class="dot setup"></span> Seřízení</span>
        <span class="legend-item"><span class="dot overhead"></span> Režie</span>
        <span class="legend-item"><span class="dot margin"></span> Marže</span>
        <span class="legend-item"><span class="dot coop"></span> Kooperace</span>
      </div>
    </div>

    <!-- Batch detail modal -->
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
            <button class="btn btn-secondary" @click="showDetailModal = false">Zavřít</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Add batch modal -->
    <Teleport to="body">
      <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
        <div class="modal-content">
          <h3>Nová dávka</h3>
          <form @submit.prevent="addBatch">
            <div class="form-group">
              <label>Množství (ks) <span class="required">*</span></label>
              <input
                v-model.number="newQuantity"
                type="number"
                class="form-input"
                min="1"
                required
                autofocus
              />
            </div>
            <div class="modal-actions">
              <button type="button" class="btn btn-secondary" @click="showAddModal = false">Zrušit</button>
              <button type="submit" class="btn btn-primary" :disabled="saving || !newQuantity || newQuantity < 1">
                {{ saving ? 'Vytvářím...' : 'Vytvořit' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete confirmation -->
    <Teleport to="body">
      <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
        <div class="modal-content">
          <h3>Smazat dávku?</h3>
          <p>Opravdu chcete smazat dávku pro <strong>{{ batchToDelete?.quantity }} ks</strong>?</p>
          <div class="modal-actions">
            <button class="btn btn-secondary" @click="showDeleteConfirm = false">Zrušit</button>
            <button class="btn btn-danger" @click="executeDelete">Smazat</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useBatchesStore } from '@/stores/batches'
import { useWindowContextStore } from '@/stores/windowContext'
import type { Batch } from '@/types/batch'
import type { LinkingGroup } from '@/stores/windows'

// Props
const props = defineProps<{
  inline?: boolean
  partId: number | null
  partNumber: string
  linkingGroup?: LinkingGroup
}>()

// Stores
const batchesStore = useBatchesStore()
const contextStore = useWindowContextStore()

// Local state
const showDetailModal = ref(false)
const showAddModal = ref(false)
const showDeleteConfirm = ref(false)
const selectedBatch = ref<Batch | null>(null)
const batchToDelete = ref<Batch | null>(null)
const newQuantity = ref<number>(100)

// Computed from store (per-context)
const displayedBatches = computed(() => batchesStore.getDisplayedBatches(props.linkingGroup))
const loading = computed(() => {
  const ctx = batchesStore.getContext(props.linkingGroup)
  return ctx.loading || ctx.batchesLoading
})
const saving = ref(false)

// Computed stats
const minUnitPrice = computed(() => {
  if (displayedBatches.value.length === 0) return 0
  return Math.min(...displayedBatches.value.map(b => b.unit_price))
})

const maxUnitPrice = computed(() => {
  if (displayedBatches.value.length === 0) return 0
  return Math.max(...displayedBatches.value.map(b => b.unit_price))
})

// Computed: Get partId from window context (direct property access for fine-grained reactivity)
const contextPartId = computed(() => {
  if (!props.linkingGroup) return null

  // Direct access to specific color's ref (NOT via function call)
  switch (props.linkingGroup) {
    case 'red': return contextStore.redContext.partId
    case 'blue': return contextStore.blueContext.partId
    case 'green': return contextStore.greenContext.partId
    case 'yellow': return contextStore.yellowContext.partId
    default: return null
  }
})

// Effective partId (context or props)
const effectivePartId = computed(() => contextPartId.value ?? props.partId)

// Watch for partId changes
// ONLY REACT if we have a linkingGroup (unlinked windows don't react to changes)
watch(effectivePartId, async (newPartId) => {
  if (newPartId && props.linkingGroup) {
    // Check if this partId is different from current context
    const ctx = batchesStore.getContext(props.linkingGroup)
    if (ctx.currentPartId !== newPartId) {
      await batchesStore.setPartContext(newPartId, props.linkingGroup)
    }
  }
}, { immediate: true })

// Format price (handles null/undefined)
function formatPrice(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return '0,00'
  return value.toLocaleString('cs-CZ', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// Open add batch modal
function openAddBatch() {
  newQuantity.value = 100
  showAddModal.value = true
}

// Add batch
async function addBatch() {
  if (!props.partId || !newQuantity.value || newQuantity.value < 1) return

  saving.value = true
  try {
    await batchesStore.createBatch(newQuantity.value, props.linkingGroup)
    showAddModal.value = false
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
</script>

<style scoped>
.pricing-module {
  padding: var(--density-module-padding, 1rem);
}

.module-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--density-section-gap, 0.75rem);
}

.module-header h3 {
  margin: 0;
  font-size: var(--density-font-md, 1rem);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.batches-count {
  color: var(--text-muted);
  font-size: var(--density-font-sm, 0.8rem);
}

/* Loading & Empty states */
.loading-state,
.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
}

.spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-red);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 0.5rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.hint {
  font-size: 0.875rem;
  margin-top: 0.5rem;
}

/* Summary bar */
.summary-bar {
  display: flex;
  gap: 1.5rem;
  padding: var(--density-cell-py, 0.5rem) var(--density-cell-px, 0.75rem);
  background: var(--bg-primary);
  border-radius: 6px;
  margin-bottom: var(--density-section-gap, 0.75rem);
}

.summary-stat {
  display: flex;
  gap: 0.375rem;
  align-items: center;
}

.stat-label {
  color: var(--text-muted);
  font-size: var(--density-font-sm, 0.75rem);
}

.stat-value {
  font-weight: 600;
  font-size: var(--density-font-base, 0.8rem);
}

/* Batches table */
.batches-table-wrapper {
  overflow-x: auto;
}

.batches-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--density-font-base, 0.8rem);
}

.batches-table th,
.batches-table td {
  padding: var(--density-cell-py, 0.5rem) var(--density-cell-px, 0.75rem);
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.batches-table th {
  background: var(--bg-primary);
  font-weight: 600;
  font-size: var(--density-font-sm, 0.7rem);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.batches-table tr:hover {
  background: var(--bg-primary);
}

.batches-table tr.is-frozen {
  background: #f0fdf4;
}

.batches-table tr.is-default {
  background: #eff6ff;
}

.col-qty { width: 150px; }
.col-unit { width: 120px; }
.col-total { width: 140px; }
.col-breakdown { width: auto; min-width: 200px; }
.col-actions { width: 80px; text-align: center !important; }

.qty-value {
  font-weight: 600;
}

.default-badge {
  font-size: 0.65rem;
  padding: 2px 4px;
  background: #dbeafe;
  color: #1e40af;
  border-radius: 3px;
  margin-left: 0.5rem;
}

.frozen-badge {
  margin-left: 0.25rem;
}

.price-main {
  font-weight: 600;
  color: var(--accent-red);
}

.price-total {
  color: var(--text-secondary);
}

/* Cost bar */
.cost-bar {
  display: flex;
  height: 16px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--bg-primary);
}

.cost-segment {
  height: 100%;
  min-width: 2px;
}

.cost-segment.material { background: #3b82f6; }
.cost-segment.machining { background: #10b981; }
.cost-segment.setup { background: #f59e0b; }
.cost-segment.overhead { background: #8b5cf6; }
.cost-segment.margin { background: #ef4444; }
.cost-segment.coop { background: #ec4899; }

.action-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  padding: 0.25rem;
  opacity: 0.7;
  transition: opacity 0.15s;
}

.action-btn:hover {
  opacity: 1;
}

/* Cost legend */
.cost-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  padding: var(--density-cell-py, 0.5rem) var(--density-cell-px, 0.75rem);
  margin-top: var(--density-section-gap, 0.75rem);
  background: var(--bg-primary);
  border-radius: 6px;
  font-size: var(--density-font-sm, 0.7rem);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: var(--text-secondary);
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.dot.material { background: #3b82f6; }
.dot.machining { background: #10b981; }
.dot.setup { background: #f59e0b; }
.dot.overhead { background: #8b5cf6; }
.dot.margin { background: #ef4444; }
.dot.coop { background: #ec4899; }

/* Buttons */
.btn {
  padding: var(--density-btn-py, 0.375rem) var(--density-btn-px, 0.75rem);
  border: none;
  border-radius: 4px;
  font-size: var(--density-font-base, 0.8rem);
  cursor: pointer;
  transition: all 0.15s;
}

.btn-sm {
  padding: var(--density-btn-py, 0.25rem) var(--density-btn-px, 0.5rem);
  font-size: var(--density-font-sm, 0.75rem);
}

.btn-primary {
  background: var(--accent-red);
  color: white;
}

.btn-primary:hover {
  background: #b91c1c;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-primary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: var(--bg-secondary);
}

.btn-danger {
  background: #fee2e2;
  color: #dc2626;
}

.btn-danger:hover {
  background: #fecaca;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-surface);
  padding: 1.5rem;
  border-radius: 12px;
  max-width: 400px;
  width: 90%;
}

.modal-wide {
  max-width: 600px;
}

.modal-content h3 {
  margin: 0 0 1rem 0;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}

.required {
  color: var(--accent-red);
}

.form-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 0.9rem;
  background: var(--bg-surface);
}

.form-input:focus {
  outline: none;
  border-color: var(--accent-red);
}

/* Detail modal */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.detail-section h4 {
  margin: 0 0 0.75rem 0;
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-color);
}

.detail-row .label {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.detail-row .value {
  font-weight: 600;
}

.cost-detail-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.cost-detail-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: var(--bg-primary);
  border-radius: 4px;
  font-size: 0.8rem;
}

.cost-detail-item .label {
  flex: 1;
}

.cost-detail-item .value {
  font-weight: 600;
}

.cost-detail-item .percent {
  color: var(--text-muted);
  font-size: 0.75rem;
}
</style>
