<script setup lang="ts">
/**
 * Quote Detail Panel
 * Displays quote details with tabs: Základní info | Položky | Snapshot
 */
import { ref, computed, reactive, watch } from 'vue'
import { useQuotesStore } from '@/stores/quotes'
import { usePartnersStore } from '@/stores/partners'
import { usePartsStore } from '@/stores/parts'
import type { QuoteWithItems, QuoteUpdate, QuoteItemCreate } from '@/types/quote'
import FormTabs from '@/components/ui/FormTabs.vue'
import { FileText, Edit, Trash2, Save, Lock, Info, Plus } from 'lucide-vue-next'

interface Props {
  quote: QuoteWithItems | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'updated': []
  'deleted': []
}>()

const quotesStore = useQuotesStore()
const partnersStore = usePartnersStore()
const partsStore = usePartsStore()

// State
const activeTab = ref(0)
const isEditing = ref(false)
const showAddItemForm = ref(false)

const editForm = reactive({
  partner_id: null as number | null,
  title: '',
  description: '',
  customer_request_number: '',
  valid_until: '',
  discount_percent: 0,
  tax_percent: 21,
  notes: ''
})

const newItem = reactive<QuoteItemCreate>({
  part_id: 0,
  quantity: 1,
  notes: ''
})

const saving = computed(() => quotesStore.loading)
const isDraft = computed(() => props.quote?.status === 'draft')
const canEdit = computed(() => isDraft.value)

// Initialize form when quote changes
watch(() => props.quote, (quote) => {
  if (quote) {
    editForm.partner_id = quote.partner_id
    editForm.title = quote.title
    editForm.description = quote.description || ''
    editForm.customer_request_number = quote.customer_request_number || ''
    editForm.valid_until = quote.valid_until || ''
    editForm.discount_percent = quote.discount_percent
    editForm.tax_percent = quote.tax_percent
    editForm.notes = ''
    isEditing.value = false
  }
}, { immediate: true })

function startEdit() {
  isEditing.value = true
}

function cancelEdit() {
  if (props.quote) {
    editForm.partner_id = props.quote.partner_id
    editForm.title = props.quote.title
    editForm.description = props.quote.description || ''
    editForm.customer_request_number = props.quote.customer_request_number || ''
    editForm.valid_until = props.quote.valid_until || ''
    editForm.discount_percent = props.quote.discount_percent
    editForm.tax_percent = props.quote.tax_percent
  }
  isEditing.value = false
}

async function saveQuote() {
  if (!props.quote) return

  const data: QuoteUpdate = {
    partner_id: editForm.partner_id,
    title: editForm.title,
    description: editForm.description || undefined,
    customer_request_number: editForm.customer_request_number || undefined,
    valid_until: editForm.valid_until || undefined,
    discount_percent: editForm.discount_percent,
    tax_percent: editForm.tax_percent,
    version: props.quote.version
  }

  try {
    await quotesStore.updateQuote(props.quote.quote_number, data)
    isEditing.value = false
    emit('updated')
  } catch (error) {
    // Error handled in store
  }
}

function openAddItemForm() {
  newItem.part_id = 0
  newItem.quantity = 1
  newItem.notes = ''
  showAddItemForm.value = true
}

async function addItem() {
  if (!props.quote || !newItem.part_id) return

  try {
    await quotesStore.addQuoteItem(props.quote.quote_number, {
      part_id: newItem.part_id,
      quantity: newItem.quantity,
      notes: newItem.notes || undefined
    })
    showAddItemForm.value = false
    emit('updated')
  } catch (error) {
    // Error handled in store (e.g., no frozen batch)
  }
}

async function deleteItem(itemId: number) {
  if (!confirm('Opravdu smazat položku?')) return

  try {
    await quotesStore.deleteQuoteItem(itemId)
    emit('updated')
  } catch (error) {
    // Error handled in store
  }
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('cs-CZ', {
    style: 'currency',
    currency: 'CZK',
    minimumFractionDigits: 2
  }).format(value)
}

function formatDate(dateString: string | null): string {
  if (!dateString) return '—'
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('cs-CZ').format(date)
}

// Load dependencies
partnersStore.fetchPartners()
partsStore.fetchParts()
</script>

<template>
  <div class="quote-detail-panel">
    <!-- Empty State -->
    <div v-if="!quote" class="empty">
      <FileText :size="48" class="empty-icon" />
      <p>Vyberte nabídku pro zobrazení detailů</p>
    </div>

    <!-- Quote Details -->
    <div v-else class="detail-content">
      <!-- Action Buttons -->
      <div class="panel-actions">
        <button
          v-if="!isEditing && canEdit"
          class="btn-primary"
          @click="startEdit"
        >
          <Edit :size="16" />
          Upravit
        </button>
        <template v-else-if="isEditing">
          <button class="btn-secondary" @click="cancelEdit">
            Zrušit
          </button>
          <button class="btn-primary" @click="saveQuote" :disabled="saving">
            <Save :size="16" />
            {{ saving ? 'Ukládám...' : 'Uložit' }}
          </button>
        </template>
      </div>

      <!-- Tabs -->
      <FormTabs v-model="activeTab" :tabs="['Základní info', 'Položky', 'Snapshot']">
        <!-- Tab 0: Basic Info -->
        <template #tab-0>
          <form @submit.prevent="saveQuote" class="detail-form">
            <div class="form-group">
              <label>Partner</label>
              <select
                v-model="editForm.partner_id"
                class="form-input"
                :disabled="!isEditing"
              >
                <option :value="null">-- Bez partnera --</option>
                <option
                  v-for="partner in partnersStore.customers"
                  :key="partner.id"
                  :value="partner.id"
                >
                  {{ partner.company_name }} ({{ partner.partner_number }})
                </option>
              </select>
            </div>

            <div class="form-group">
              <label>Název <span class="required">*</span></label>
              <input
                v-model="editForm.title"
                type="text"
                class="form-input"
                :disabled="!isEditing"
                required
                maxlength="200"
              />
            </div>

            <div class="form-group">
              <label>Popis</label>
              <textarea
                v-model="editForm.description"
                class="form-textarea"
                :disabled="!isEditing"
                rows="3"
                maxlength="1000"
              ></textarea>
            </div>

            <div class="form-group">
              <label>Číslo poptávky zákazníka</label>
              <input
                v-model="editForm.customer_request_number"
                type="text"
                class="form-input"
                :disabled="!isEditing"
                maxlength="50"
                placeholder="P20971, RFQ-2026-001..."
              />
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Platnost do</label>
                <input
                  v-model="editForm.valid_until"
                  type="date"
                  class="form-input"
                  :disabled="!isEditing"
                />
              </div>
              <div class="form-group">
                <label>Sleva (%)</label>
                <input
                  v-model.number="editForm.discount_percent"
                  type="number"
                  class="form-input"
                  :disabled="!isEditing"
                  min="0"
                  max="100"
                  step="0.01"
                  v-select-on-focus
                />
              </div>
              <div class="form-group">
                <label>DPH (%)</label>
                <input
                  v-model.number="editForm.tax_percent"
                  type="number"
                  class="form-input"
                  :disabled="!isEditing"
                  min="0"
                  max="100"
                  step="0.01"
                  v-select-on-focus
                />
              </div>
            </div>

            <div v-if="!canEdit" class="edit-lock-notice">
              <Lock :size="16" class="lock-icon" />
              <span>Nabídku lze editovat pouze ve stavu "Koncept"</span>
            </div>
          </form>
        </template>

        <!-- Tab 1: Items -->
        <template #tab-1>
          <div class="items-panel">
            <!-- Add Item Button -->
            <div v-if="canEdit" class="items-actions">
              <button class="btn-primary" @click="openAddItemForm">
                <Plus :size="16" />
                Přidat položku
              </button>
            </div>

            <!-- Items Table -->
            <div v-if="quote.items.length > 0" class="items-table-wrapper">
              <table class="items-table">
                <thead>
                  <tr>
                    <th>Pořadí</th>
                    <th>Číslo dílu</th>
                    <th>Název</th>
                    <th>Množství</th>
                    <th>Jednotková cena</th>
                    <th>Celkem</th>
                    <th v-if="canEdit">Akce</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in quote.items" :key="item.id">
                    <td>{{ item.seq }}</td>
                    <td>{{ item.article_number || item.part_number }}</td>
                    <td>{{ item.part_name }}</td>
                    <td>{{ item.quantity }}</td>
                    <td>{{ formatCurrency(item.unit_price) }}</td>
                    <td>{{ formatCurrency(item.line_total) }}</td>
                    <td v-if="canEdit">
                      <button
                        @click="deleteItem(item.id)"
                        class="btn-icon btn-danger"
                        :disabled="saving"
                      >
                        <Trash2 :size="16" />
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Empty State -->
            <div v-else class="items-empty">
              <p>Žádné položky</p>
            </div>

            <div v-if="!canEdit" class="edit-lock-notice">
              <Lock :size="16" class="lock-icon" />
              <span>Položky lze editovat pouze ve stavu "Koncept"</span>
            </div>
          </div>
        </template>

        <!-- Tab 2: Snapshot -->
        <template #tab-2>
          <div class="snapshot-panel">
            <div v-if="quote.status === 'draft'" class="snapshot-empty">
              <p>Snapshot je dostupný až po odeslání nabídky</p>
            </div>
            <div v-else class="snapshot-content">
              <h4>Metadata</h4>
              <div class="snapshot-meta">
                <div class="meta-item">
                  <span class="meta-label">Odesláno:</span>
                  <span class="meta-value">{{ formatDate(quote.sent_at) }}</span>
                </div>
                <div v-if="quote.approved_at" class="meta-item">
                  <span class="meta-label">Schváleno:</span>
                  <span class="meta-value">{{ formatDate(quote.approved_at) }}</span>
                </div>
                <div v-if="quote.rejected_at" class="meta-item">
                  <span class="meta-label">Odmítnuto:</span>
                  <span class="meta-value">{{ formatDate(quote.rejected_at) }}</span>
                </div>
              </div>

              <h4>Verze</h4>
              <div class="snapshot-version">
                <span>Verze: {{ quote.version }}</span>
              </div>

              <div class="snapshot-info">
                <p>Snapshot dat je vytvořen při odeslání nabídky a zachycuje aktuální stav materiálů, cen a operací.</p>
              </div>
            </div>
          </div>
        </template>
      </FormTabs>
    </div>

    <!-- Add Item Modal -->
    <Teleport to="body">
      <div v-if="showAddItemForm" class="modal-overlay" @click.self="showAddItemForm = false">
        <div class="modal-content">
          <h3>Přidat položku</h3>
          <form @submit.prevent="addItem" class="create-form">
            <div class="form-group">
              <label>Díl <span class="required">*</span></label>
              <select
                v-model.number="newItem.part_id"
                class="form-input"
                required
              >
                <option :value="0" disabled>-- Vyberte díl --</option>
                <option
                  v-for="part in partsStore.parts"
                  :key="part.id"
                  :value="part.id"
                >
                  {{ part.article_number || part.part_number }} - {{ part.name }}
                </option>
              </select>
            </div>

            <div class="form-group">
              <label>Množství <span class="required">*</span></label>
              <input
                v-model.number="newItem.quantity"
                type="number"
                class="form-input"
                required
                min="0.01"
                step="0.01"
                v-select-on-focus
              />
            </div>

            <div class="info-notice">
              <Info :size="16" class="info-icon" />
              <span>Cena se automaticky načte z nejnovější zmrazené kalkulace dílu.</span>
            </div>

            <div class="form-group">
              <label>Poznámky</label>
              <textarea
                v-model="newItem.notes"
                class="form-textarea"
                rows="3"
              ></textarea>
            </div>

            <div class="modal-actions">
              <button type="button" class="btn-secondary" @click="showAddItemForm = false">
                Zrušit
              </button>
              <button
                type="submit"
                class="btn-primary"
                :disabled="saving || !newItem.part_id"
              >
                {{ saving ? 'Přidávám...' : 'Přidat' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.quote-detail-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  container-type: inline-size;
  container-name: detail-panel;
}

/* Empty State */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-8);
  color: var(--text-secondary);
  text-align: center;
}

.empty-icon {
  margin-bottom: var(--space-2);
  opacity: 0.5;
  color: var(--text-secondary);
}

.empty p {
  font-size: var(--text-base);
}

/* Detail Content */
.detail-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding: var(--space-5);
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding-bottom: var(--space-4);
  border-bottom: 2px solid var(--border-color);
}

/* Forms */
.detail-form,
.create-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.form-row {
  display: flex;
  gap: var(--space-3);
}

.form-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.form-group label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-body);
}

.required {
  color: var(--palette-danger);
}

.form-input,
.form-textarea {
  padding: var(--space-3);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  background: var(--bg-input);
  color: var(--text-body);
  font-family: inherit;
  transition: all var(--duration-fast);
}

.form-input:disabled,
.form-textarea:disabled {
  background: var(--bg-surface);
  color: var(--text-secondary);
  cursor: not-allowed;
  opacity: 0.7;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  background: var(--state-focus-bg);
  border-color: var(--state-focus-border);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.form-textarea {
  resize: vertical;
  min-height: 100px;
}

.edit-lock-notice,
.info-notice {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: rgba(115, 115, 115, 0.1);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.info-notice {
  background: rgba(37, 99, 235, 0.1);
  border: 1px solid var(--color-info);
  color: var(--text-body);
}

.lock-icon,
.info-icon {
  font-size: var(--text-base);
}

/* Items Panel */
.items-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.items-actions {
  display: flex;
  justify-content: flex-end;
}

.items-table-wrapper {
  overflow-x: auto;
}

.items-table {
  width: 100%;
  border-collapse: collapse;
}

.items-table th,
.items-table td {
  padding: var(--space-3);
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.items-table th {
  background: var(--bg-surface);
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.items-table td {
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-weight: var(--font-medium);
}

.items-empty {
  text-align: center;
  padding: var(--space-8);
  color: var(--text-secondary);
}

/* Snapshot Panel */
.snapshot-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.snapshot-empty {
  text-align: center;
  padding: var(--space-8);
  color: var(--text-secondary);
}

.snapshot-content h4 {
  margin: 0 0 var(--space-2) 0;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.snapshot-meta,
.snapshot-version {
  padding: var(--space-3);
  background: var(--bg-raised);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
}

.snapshot-meta {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.meta-item {
  display: flex;
  justify-content: space-between;
}

.meta-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.meta-value {
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-weight: var(--font-semibold);
}

.snapshot-version {
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.snapshot-info {
  padding: var(--space-3);
  background: var(--palette-info-light, rgba(59, 130, 246, 0.1));
  border-radius: var(--radius-md);
  border: 1px solid var(--palette-info, #3b82f6);
}

.snapshot-info p {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--text-body);
}

/* Buttons */
.btn-primary,
.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  cursor: pointer;
  transition: all var(--duration-normal);
}

.btn-primary {
  background: var(--color-primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-surface);
  color: var(--text-primary);
  border: 2px solid var(--border-color);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--state-hover);
  border-color: var(--border-strong);
  transform: translateY(-1px);
}

.btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: none;
  background: transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-tertiary);
  transition: all var(--duration-fast);
}

.btn-icon:hover:not(:disabled) {
  background: var(--state-hover);
  color: var(--text-primary);
  transform: scale(1.1);
}

.btn-icon.btn-danger:hover:not(:disabled) {
  color: var(--color-danger);
  background: rgba(239, 68, 68, 0.1);
}

.btn-icon:disabled {
  opacity: 0.3;
  cursor: not-allowed;
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
  max-width: 600px;
  width: 90%;
  border: 1px solid var(--border-default);
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content h3 {
  margin: 0 0 var(--space-4) 0;
  color: var(--text-primary);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-4);
}
</style>
