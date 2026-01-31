<script setup lang="ts">
/**
 * Pricing Detail Panel Component
 * Displays batches list with cost breakdown and management actions
 */
import { ref, computed, watch } from 'vue'
import { useBatchesStore } from '@/stores/batches'
import type { Batch } from '@/types/batch'
import type { LinkingGroup } from '@/stores/windows'

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
const showAddModal = ref(false)
const showDeleteConfirm = ref(false)
const selectedBatch = ref<Batch | null>(null)
const batchToDelete = ref<Batch | null>(null)
const newQuantity = ref<number>(100)
const saving = ref(false)

// Computed from store
const displayedBatches = computed(() => batchesStore.getDisplayedBatches(props.linkingGroup))
const loading = computed(() => {
  const ctx = batchesStore.getContext(props.linkingGroup)
  return ctx.loading || ctx.batchesLoading
})

// Format price
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
    <div v-else-if="displayedBatches.length === 0" class="empty">
      <div class="empty-icon">💰</div>
      <p>Žádné cenové dávky</p>
      <p class="hint">Přidejte první dávku pro výpočet ceny</p>
      <button class="btn-primary" @click="openAddBatch" :disabled="!partId">
        + Přidat dávku
      </button>
    </div>

    <!-- Batches List -->
    <div v-else class="batches-list">
      <!-- Actions Bar -->
      <div class="actions-bar">
        <button class="btn-primary btn-sm" @click="openAddBatch" :disabled="!partId || saving">
          + Přidat dávku
        </button>
        <span class="batches-count">{{ displayedBatches.length }} dávek</span>
      </div>

      <!-- Batches Table -->
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

      <!-- Cost Legend -->
      <div class="cost-legend">
        <span class="legend-item"><span class="dot material"></span> Materiál</span>
        <span class="legend-item"><span class="dot machining"></span> Obrábění</span>
        <span class="legend-item"><span class="dot setup"></span> Seřízení</span>
        <span class="legend-item"><span class="dot overhead"></span> Režie</span>
        <span class="legend-item"><span class="dot margin"></span> Marže</span>
        <span class="legend-item"><span class="dot coop"></span> Kooperace</span>
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

    <!-- Add Batch Modal -->
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
              <button type="button" class="btn-secondary" @click="showAddModal = false">Zrušit</button>
              <button type="submit" class="btn-primary" :disabled="saving || !newQuantity || newQuantity < 1">
                {{ saving ? 'Vytvářím...' : 'Vytvořit' }}
              </button>
            </div>
          </form>
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
  font-size: 3rem;
}

.hint {
  font-size: var(--text-sm);
  margin-top: 0;
}

/* Actions Bar */
.actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3);
  background: var(--bg-raised);
  border-radius: var(--radius-md);
}

.batches-count {
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

/* Batches List */
.batches-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
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

.col-qty { width: 150px; }
.col-unit { width: 120px; }
.col-total { width: 140px; }
.col-breakdown { width: auto; min-width: 200px; }
.col-actions { width: 80px; text-align: center !important; }

.qty-value {
  font-weight: var(--font-semibold);
}

.default-badge {
  font-size: var(--text-xs);
  padding: var(--space-1);
  background: var(--palette-info);
  color: white;
  border-radius: var(--radius-sm);
  margin-left: var(--space-2);
}

.frozen-badge {
  margin-left: var(--space-1);
}

.price-main {
  font-weight: var(--font-semibold);
  color: var(--color-primary);
}

.price-total {
  color: var(--text-secondary);
}

/* Cost Bar */
.cost-bar {
  display: flex;
  height: 16px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--bg-raised);
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
  padding: var(--space-1);
  opacity: 0.7;
  transition: var(--transition-fast);
}

.action-btn:hover {
  opacity: 1;
}

/* Cost Legend */
.cost-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--bg-raised);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--text-secondary);
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-sm);
}

.dot.material { background: #3b82f6; }
.dot.machining { background: #10b981; }
.dot.setup { background: #f59e0b; }
.dot.overhead { background: #8b5cf6; }
.dot.margin { background: #ef4444; }
.dot.coop { background: #ec4899; }

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
  border-color: var(--color-primary);
  background: var(--bg-surface);
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
