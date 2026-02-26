<script setup lang="ts">
import { ref, watch } from 'vue'
import { ExternalLinkIcon, Trash2Icon, PlusIcon, CheckIcon, TriangleAlertIcon, FileDownIcon } from 'lucide-vue-next'
import * as quotesApi from '@/api/quotes'
import type { QuoteDetail } from '@/types/quote'
import type { Part } from '@/types/part'
import type { ContextGroup } from '@/types/workspace'
import { useUiStore } from '@/stores/ui'
import { useWorkspaceStore } from '@/stores/workspace'
import { useDialog } from '@/composables/useDialog'
import { formatCurrency, formatDate } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'
import InlineInput from '@/components/ui/InlineInput.vue'
import PartCombobox from '@/components/ui/PartCombobox.vue'
import { ICON_SIZE_SM } from '@/config/design'

interface Props {
  quoteNumber: string
  leafId: string
  ctx: ContextGroup
}

const props = defineProps<Props>()
const emit = defineEmits<{ reload: [] }>()

const ui = useUiStore()
const ws = useWorkspaceStore()
const dialog = useDialog()

const quote = ref<QuoteDetail | null>(null)
const loading = ref(false)
const error = ref(false)

// Add item inline form
const addSelectedPart = ref<Part | null>(null)
const addQuantity = ref<number | null>(1)
const addSaving = ref(false)
const partComboRef = ref<InstanceType<typeof PartCombobox> | null>(null)
const selectedItemId = ref<number | null>(null)
const pdfLoading = ref(false)

const STATUS_LABELS: Record<string, string> = {
  draft:    'Rozpracovaná',
  sent:     'Odeslaná',
  approved: 'Schválená',
  rejected: 'Zamítnutá',
}

function statusDotClass(status: string): string {
  if (status === 'approved') return 'badge-dot-ok'
  if (status === 'rejected') return 'badge-dot-error'
  if (status === 'sent') return 'badge-dot-warn'
  return 'badge-dot-neutral'
}

async function load() {
  loading.value = true
  error.value = false
  try {
    quote.value = await quotesApi.getDetail(props.quoteNumber)
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

watch(() => props.quoteNumber, load, { immediate: true })

async function onSend() {
  const confirmed = await dialog.confirm({
    title: 'Odeslat nabídku?',
    message: 'Po odeslání nebude nabídka editovatelná.',
    confirmLabel: 'Odeslat',
  })
  if (!confirmed) return
  try {
    await quotesApi.sendQuote(props.quoteNumber)
    ui.showSuccess('Nabídka odeslána')
    await load()
    emit('reload')
  } catch {
    ui.showError('Chyba při odesílání nabídky')
  }
}

async function onApprove() {
  const confirmed = await dialog.confirm({
    title: 'Schválit nabídku?',
    message: 'Nabídka bude přesunuta do stavu Schválená.',
    confirmLabel: 'Schválit',
  })
  if (!confirmed) return
  try {
    await quotesApi.approveQuote(props.quoteNumber)
    ui.showSuccess('Nabídka schválena')
    await load()
    emit('reload')
  } catch {
    ui.showError('Chyba při schvalování nabídky')
  }
}

async function onReject() {
  const confirmed = await dialog.confirm({
    title: 'Zamítnout nabídku?',
    message: 'Nabídka bude přesunuta do stavu Zamítnutá.',
    confirmLabel: 'Zamítnout',
    dangerous: true,
  })
  if (!confirmed) return
  try {
    await quotesApi.rejectQuote(props.quoteNumber)
    ui.showSuccess('Nabídka zamítnuta')
    await load()
    emit('reload')
  } catch {
    ui.showError('Chyba při zamítání nabídky')
  }
}

async function onClone() {
  try {
    const cloned = await quotesApi.cloneQuote(props.quoteNumber)
    ui.showSuccess(`Nabídka klonována → ${cloned.quote_number}`)
    emit('reload')
  } catch {
    ui.showError('Chyba při klonování nabídky')
  }
}

function openPartDetail() {
  ws.splitLeaf(props.leafId, 'parts-list', 'right', props.ctx)
}

async function onAddItem() {
  if (!addSelectedPart.value) { ui.showError('Vyberte díl ze seznamu'); return }
  const qty = addQuantity.value ?? 0
  if (qty < 1) { ui.showError('Množství musí být ≥ 1'); return }

  addSaving.value = true
  try {
    await quotesApi.addItem(props.quoteNumber, addSelectedPart.value.id, qty)
    const label = addSelectedPart.value.article_number ?? addSelectedPart.value.part_number
    ui.showSuccess(`Díl ${label} přidán`)
    addSelectedPart.value = null
    addQuantity.value = 1
    await load()
    emit('reload')
    // Vrátit focus na combobox pro další přidání
    partComboRef.value?.focus()
  } catch {
    ui.showError('Chyba při přidávání položky')
  } finally {
    addSaving.value = false
  }
}

async function onRemoveItem(itemId: number, label: string | null) {
  const confirmed = await dialog.confirm({
    title: 'Odebrat položku?',
    message: `Odeberete díl ${label ?? itemId} z nabídky.`,
    confirmLabel: 'Odebrat',
    dangerous: true,
  })
  if (!confirmed) return
  try {
    await quotesApi.removeItem(itemId)
    ui.showSuccess('Položka odebrána')
    await load()
    emit('reload')
  } catch {
    ui.showError('Chyba při odebírání položky')
  }
}

function handleRowKeydown(item: { id: number; article_number: string | null; part_number: string | null }, e: KeyboardEvent, isDraft: boolean) {
  if (isDraft && e.ctrlKey && e.key === 'd') {
    e.preventDefault()
    onRemoveItem(item.id, item.article_number ?? item.part_number)
  }
}

function selectItem(id: number) {
  selectedItemId.value = id
}

async function onDownloadPdf() {
  pdfLoading.value = true
  try {
    await quotesApi.downloadPdf(props.quoteNumber)
  } catch {
    ui.showError('Chyba při generování PDF')
  } finally {
    pdfLoading.value = false
  }
}
</script>

<template>
  <div class="wquo-detail">
    <!-- Loading -->
    <div v-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>

    <!-- Data -->
    <template v-else-if="quote">
      <!-- Header -->
      <div class="detail-header">
        <div class="detail-title-row">
          <span class="detail-number t4">{{ quote.quote_number }}</span>
          <span class="detail-title">{{ quote.title || '—' }}</span>
          <span class="badge ml-auto">
            <span :class="['badge-dot', statusDotClass(quote.status)]" />
            {{ STATUS_LABELS[quote.status] }}
          </span>
        </div>
        <div class="detail-actions">
          <template v-if="quote.status === 'draft'">
            <button class="btn-primary" data-testid="quote-send-btn" @click="onSend">Odeslat</button>
            <button class="btn-destructive" data-testid="quote-delete-btn" @click="onReject">Smazat</button>
          </template>
          <template v-else-if="quote.status === 'sent'">
            <button class="btn-primary" data-testid="quote-approve-btn" @click="onApprove">Schválit</button>
            <button class="btn-destructive" data-testid="quote-reject-btn" @click="onReject">Zamítnout</button>
            <button class="btn-secondary" data-testid="quote-clone-btn" @click="onClone">Klonovat</button>
          </template>
          <template v-else>
            <button class="btn-secondary" data-testid="quote-clone-btn" @click="onClone">Klonovat</button>
          </template>
          <button
            class="btn-secondary"
            :disabled="pdfLoading"
            data-testid="quote-pdf-btn"
            @click="onDownloadPdf"
          >
            <FileDownIcon :size="ICON_SIZE_SM" />
            PDF
          </button>
        </div>
      </div>

      <!-- Metadata -->
      <div class="detail-section">
        <div class="meta-grid">
          <div class="meta-row">
            <span class="meta-label">Zákazník</span>
            <span class="meta-value">{{ quote.partner_id ?? '—' }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Číslo poptávky</span>
            <span class="meta-value">{{ quote.customer_request_number ?? '—' }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Datum poptávky</span>
            <span class="meta-value">{{ formatDate(quote.request_date) }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Termín odevzdání</span>
            <span class="meta-value">{{ formatDate(quote.offer_deadline) }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Platnost</span>
            <span class="meta-value">{{ formatDate(quote.valid_until) }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Dodací podmínky</span>
            <span class="meta-value">{{ quote.delivery_terms ?? '—' }}</span>
          </div>
          <div v-if="quote.notes" class="meta-row meta-row-full">
            <span class="meta-label">Poznámky</span>
            <span class="meta-value">{{ quote.notes }}</span>
          </div>
        </div>
      </div>

      <!-- Items table -->
      <div class="detail-section-grow">
        <div class="section-header">
          <span class="section-title">Položky</span>
        </div>

        <div class="ot-wrap">
          <table class="ot">
            <thead>
              <tr>
                <th style="width:80px">Č. artiklu</th>
                <th>Název</th>
                <th style="width:70px">Výkres</th>
                <th class="col-num" style="width:64px">Mn.</th>
                <th class="col-currency" style="width:80px">J. cena</th>
                <th class="col-currency" style="width:84px">Celkem</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in quote.items"
                :key="item.id"
                class="qitem-row"
                tabindex="0"
                :class="{ act: selectedItemId === item.id }"
                :data-testid="`quote-item-row-${item.id}`"
                @click="selectItem(item.id)"
                @focusin="selectItem(item.id)"
                @keydown="handleRowKeydown(item, $event, quote.status === 'draft')"
              >
                <td class="t4">{{ item.article_number ?? '—' }}</td>
                <td class="title-cell">{{ item.part_name ?? '—' }}</td>
                <td class="t4">{{ item.drawing_number ?? '—' }}</td>
                <td class="col-num">{{ item.quantity }}</td>
                <td class="col-currency">{{ formatCurrency(item.unit_price) }}</td>
                <td class="col-currency">{{ formatCurrency(item.line_total) }}</td>
                <td class="act-cell">
                  <TriangleAlertIcon
                    v-if="item.batch_approx"
                    class="approx-warn"
                    :size="ICON_SIZE_SM"
                    title="Neexistuje přesná dávka — cena z nejbližší nižší"
                  />
                  <button
                    v-if="item.part_id"
                    class="icon-btn"
                    title="Otevřít díl"
                    :data-testid="`quote-item-link-${item.id}`"
                    @click.stop="openPartDetail"
                  >
                    <ExternalLinkIcon :size="ICON_SIZE_SM" />
                  </button>
                  <button
                    v-if="quote.status === 'draft'"
                    class="icon-btn icon-btn-danger"
                    title="Odebrat položku (Ctrl+D)"
                    :data-testid="`quote-item-delete-${item.id}`"
                    @click.stop="onRemoveItem(item.id, item.article_number ?? item.part_number)"
                  >
                    <Trash2Icon :size="ICON_SIZE_SM" />
                  </button>
                </td>
              </tr>

              <!-- Add item row — DRAFT only -->
              <tr v-if="quote.status === 'draft'" class="add-row">
                <td colspan="3">
                  <PartCombobox
                    ref="partComboRef"
                    v-model="addSelectedPart"
                    data-testid="add-item-part-combo"
                    @enter="onAddItem"
                  />
                </td>
                <td class="col-num">
                  <InlineInput
                    v-model="addQuantity"
                    numeric
                    type="number"
                    min="1"
                    class="add-input add-qty"
                    data-testid="add-item-quantity"
                    @keydown.enter="onAddItem"
                  />
                </td>
                <td colspan="2" class="t4 add-hint">
                  {{ addSelectedPart ? (addSelectedPart.name ?? '—') : 'hledej article / název' }}
                </td>
                <td class="act-cell">
                  <button
                    class="icon-btn icon-btn-brand"
                    title="Přidat díl"
                    :disabled="addSaving || !addSelectedPart"
                    data-testid="add-item-confirm"
                    @click="onAddItem"
                  >
                    <CheckIcon v-if="!addSaving" :size="ICON_SIZE_SM" />
                    <PlusIcon v-else :size="ICON_SIZE_SM" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Empty + add hint -->
        <div v-if="!quote.items.length && quote.status !== 'draft'" class="items-empty">
          <span class="t4">Žádné položky</span>
        </div>
      </div>

      <!-- Price summary -->
      <div class="price-summary">
        <div class="price-row">
          <span class="price-label">Mezisoučet</span>
          <span class="price-value">{{ formatCurrency(quote.subtotal) }}</span>
        </div>
        <div v-if="quote.discount_percent > 0" class="price-row">
          <span class="price-label">Sleva ({{ quote.discount_percent }}%)</span>
          <span class="price-value">−{{ formatCurrency(quote.discount_amount) }}</span>
        </div>
        <div class="price-row">
          <span class="price-label">DPH ({{ quote.tax_percent }}%)</span>
          <span class="price-value">{{ formatCurrency(quote.tax_amount) }}</span>
        </div>
        <div class="price-row price-total">
          <span class="price-label">Celkem</span>
          <span class="price-value">{{ formatCurrency(quote.total) }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wquo-detail {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

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
.mod-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--b2); }
.mod-dot.err { background: var(--err); }
.mod-label { font-size: var(--fsm); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

/* ─── Header ─── */
.detail-header {
  padding: 8px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.detail-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.detail-number { font-size: var(--fsm); }
.detail-title { font-size: var(--fs); font-weight: 500; color: var(--t1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ml-auto { margin-left: auto; flex-shrink: 0; }
.detail-actions { display: flex; gap: 6px; flex-wrap: wrap; }

/* ─── Sections ─── */
.detail-section {
  padding: 8px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.detail-section-grow {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px var(--pad) 4px;
  flex-shrink: 0;
}
.section-title {
  font-size: var(--fsm);
  font-weight: 600;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ─── Meta grid ─── */
.meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 16px; }
.meta-row { display: flex; flex-direction: column; gap: 1px; }
.meta-row-full { grid-column: 1 / -1; }
.meta-label { font-size: var(--fsm); color: var(--t4); }
.meta-value { font-size: var(--fs); color: var(--t2); }

/* ─── Items ─── */
.items-empty { padding: 12px var(--pad); color: var(--t4); font-size: var(--fsm); }
.ot-wrap { flex: 1; overflow-y: auto; min-height: 0; }
.t4 { color: var(--t4); }
.title-cell { max-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.act-cell { text-align: right; white-space: nowrap; }

/* ─── Item rows ─── */
.qitem-row { cursor: default; }
.qitem-row:hover { background: rgba(255, 255, 255, 0.025); }
.qitem-row.act { background: rgba(255, 255, 255, 0.035); }

/* ─── Add item row ─── */
.add-row td { background: var(--ground); border-top: 1px solid var(--b1); }
/* InlineInput (.ii) handles border/bg/colors — we only need width + height override */
.add-input { width: 100%; height: 22px; }
.add-qty { text-align: right; }
.add-hint { font-size: var(--fss); padding-left: 4px; }
.approx-warn { color: var(--warn); vertical-align: middle; cursor: default; }

/* ─── Price summary ─── */
.price-summary {
  padding: 8px var(--pad);
  border-top: 1px solid var(--b1);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.price-row { display: flex; justify-content: space-between; align-items: center; }
.price-label { font-size: var(--fsm); color: var(--t3); }
.price-value { font-size: var(--fsm); color: var(--t2); font-variant-numeric: tabular-nums; }
.price-total .price-label { font-size: var(--fs); font-weight: 600; color: var(--t1); }
.price-total .price-value { font-size: var(--fsh); font-weight: 600; color: var(--t1); }
</style>
