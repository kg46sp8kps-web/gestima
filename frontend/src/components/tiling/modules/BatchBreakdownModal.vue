<script setup lang="ts">
import { ref, watch } from 'vue'
import Modal from '@/components/ui/Modal.vue'
import Spinner from '@/components/ui/Spinner.vue'
import * as partsApi from '@/api/parts'
import type { PriceBreakdown } from '@/types/pricing'
import { formatCurrency, formatNumber } from '@/utils/formatters'

interface Props {
  modelValue: boolean
  partNumber: string
  quantity: number
}

const props = defineProps<Props>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const loading = ref(false)
const error = ref(false)
const data = ref<PriceBreakdown | null>(null)

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    loading.value = true
    error.value = false
    data.value = null
    try {
      data.value = await partsApi.getPricing(props.partNumber, props.quantity)
    } catch {
      error.value = true
    } finally {
      loading.value = false
    }
  },
)

function pct(val: number): string {
  return formatNumber(val, 1) + ' %'
}

function coeff(val: number): string {
  return '×' + formatNumber(val, 2)
}

function perPiece(val: number): string {
  if (!data.value || data.value.quantity <= 0) return '—'
  return formatCurrency(val / data.value.quantity)
}

// val je již per-piece — dávka = val × qty
function batchFromPiece(val: number): string {
  if (!data.value) return '—'
  return formatCurrency(val * data.value.quantity)
}
</script>

<template>
  <Modal
    :model-value="modelValue"
    :title="`Rozpad ceny — ${quantity} ks`"
    size="lg"
    data-testid="breakdown-modal"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <!-- Loading -->
    <div v-if="loading" class="bd-center">
      <Spinner size="md" text="Načítám rozpad ceny…" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="bd-center bd-error">
      <span>Chyba při načítání kalkulace</span>
    </div>

    <!-- Data — single CSS grid pro zarovnání všech sloupců -->
    <div v-else-if="data" class="bd-grid">

      <!-- Záhlaví sloupců -->
      <div class="g-full" />
      <div class="bd-col-h">/ ks</div>
      <div class="bd-col-h">dávka {{ quantity }} ks</div>

      <!-- ── SEŘÍZENÍ ───────────────────────────────── -->
      <div class="bd-sec g-full">Seřízení</div>

      <div class="bd-lbl">Čas</div>
      <div class="bd-shared">{{ formatNumber(data.machine_setup_time_min, 1) }} min</div>

      <div class="bd-lbl bd-indent bd-sm">Odpisy</div>
      <div class="bd-val bd-sm">{{ perPiece(data.setup_amortization) }}</div>
      <div class="bd-val bd-sm">{{ formatCurrency(data.setup_amortization) }}</div>

      <div class="bd-lbl bd-indent bd-sm">Mzdy</div>
      <div class="bd-val bd-sm">{{ perPiece(data.setup_labor) }}</div>
      <div class="bd-val bd-sm">{{ formatCurrency(data.setup_labor) }}</div>

      <div class="bd-lbl bd-indent bd-sm">Provozní režie</div>
      <div class="bd-val bd-sm">{{ perPiece(data.setup_overhead) }}</div>
      <div class="bd-val bd-sm">{{ formatCurrency(data.setup_overhead) }}</div>

      <div class="bd-lbl bd-tot">Seřízení celkem</div>
      <div class="bd-val bd-emph bd-tot">{{ perPiece(data.machine_setup_cost) }}</div>
      <div class="bd-val bd-emph bd-tot">{{ formatCurrency(data.machine_setup_cost) }}</div>

      <!-- ── VÝROBA ──────────────────────────────────── -->
      <div class="bd-sec g-full">Výroba</div>

      <div class="bd-lbl">Čas</div>
      <div class="bd-shared">{{ formatNumber(data.machine_operation_time_min, 1) }} min</div>

      <div class="bd-lbl bd-indent bd-sm">Odpisy</div>
      <div class="bd-val bd-sm">{{ perPiece(data.operation_amortization) }}</div>
      <div class="bd-val bd-sm">{{ formatCurrency(data.operation_amortization) }}</div>

      <div class="bd-lbl bd-indent bd-sm">Mzdy</div>
      <div class="bd-val bd-sm">{{ perPiece(data.operation_labor) }}</div>
      <div class="bd-val bd-sm">{{ formatCurrency(data.operation_labor) }}</div>

      <div class="bd-lbl bd-indent bd-sm">Nástroje</div>
      <div class="bd-val bd-sm">{{ perPiece(data.operation_tools) }}</div>
      <div class="bd-val bd-sm">{{ formatCurrency(data.operation_tools) }}</div>

      <div class="bd-lbl bd-indent bd-sm">Provozní režie</div>
      <div class="bd-val bd-sm">{{ perPiece(data.operation_overhead) }}</div>
      <div class="bd-val bd-sm">{{ formatCurrency(data.operation_overhead) }}</div>

      <div class="bd-lbl bd-tot">Výroba celkem</div>
      <div class="bd-val bd-emph bd-tot">{{ perPiece(data.machine_operation_cost) }}</div>
      <div class="bd-val bd-emph bd-tot">{{ formatCurrency(data.machine_operation_cost) }}</div>

      <!-- ── ZMETKOVITOST (pouze pokud > 0) ──────────── -->
      <template v-if="data.scrap_rate_percent > 0">
        <div class="bd-sec g-full">Zmetkovitost</div>

        <div class="bd-lbl">Procento zmetků</div>
        <div class="bd-shared">{{ pct(data.scrap_rate_percent) }}</div>

        <div class="bd-lbl">Strojní po odpadu</div>
        <div class="bd-val">{{ perPiece(data.machine_total) }}</div>
        <div class="bd-val">{{ formatCurrency(data.machine_total) }}</div>
      </template>

      <!-- ── REŽIE + MARŽE ────────────────────────────── -->
      <div class="bd-sec g-full">Režie + Marže</div>

      <div class="bd-lbl">Přirážka režie ({{ coeff(data.overhead_coefficient) }})</div>
      <div class="bd-val bd-plus">+{{ perPiece(data.overhead_markup) }}</div>
      <div class="bd-val bd-plus">+{{ formatCurrency(data.overhead_markup) }}</div>

      <div class="bd-lbl">Přirážka marže ({{ coeff(data.margin_coefficient) }})</div>
      <div class="bd-val bd-plus">+{{ perPiece(data.margin_markup) }}</div>
      <div class="bd-val bd-plus">+{{ formatCurrency(data.margin_markup) }}</div>

      <div class="bd-lbl bd-tot">Stroje s marží</div>
      <div class="bd-val bd-emph bd-tot">{{ perPiece(data.work_with_margin) }}</div>
      <div class="bd-val bd-emph bd-tot">{{ formatCurrency(data.work_with_margin) }}</div>

      <!-- ── KOOPERACE ─────────────────────────────────── -->
      <div class="bd-sec g-full">Kooperace</div>

      <div class="bd-lbl bd-indent bd-sm">Cena raw</div>
      <div class="bd-val bd-sm">{{ formatCurrency(data.coop_cost_raw) }}</div>
      <div class="bd-val bd-sm">{{ batchFromPiece(data.coop_cost_raw) }}</div>

      <div class="bd-lbl bd-indent bd-sm">Koef. kooperace ({{ coeff(data.coop_coefficient) }})</div>
      <div class="bd-shared bd-sm" />

      <div class="bd-lbl bd-tot">Kooperace celkem</div>
      <div class="bd-val bd-emph bd-tot">{{ perPiece(data.coop_cost) }}</div>
      <div class="bd-val bd-emph bd-tot">{{ formatCurrency(data.coop_cost) }}</div>

      <!-- ── MATERIÁL ──────────────────────────────────── -->
      <div class="bd-sec g-full">Materiál</div>

      <template v-if="data.material_weight_kg > 0">
        <div class="bd-lbl">Hmotnost / ks</div>
        <div class="bd-shared">{{ formatNumber(data.material_weight_kg, 4) }} kg</div>
      </template>

      <template v-if="data.material_price_per_kg > 0">
        <div class="bd-lbl">Cena materiálu</div>
        <div class="bd-shared">{{ formatCurrency(data.material_price_per_kg) }} / kg</div>
      </template>

      <div class="bd-lbl bd-indent bd-sm">Cena raw</div>
      <div class="bd-val bd-sm">{{ formatCurrency(data.material_cost_raw) }}</div>
      <div class="bd-val bd-sm">{{ batchFromPiece(data.material_cost_raw) }}</div>

      <div class="bd-lbl bd-indent bd-sm">Koef. skladu ({{ coeff(data.stock_coefficient) }})</div>
      <div class="bd-shared bd-sm" />

      <div class="bd-lbl bd-tot">Materiál celkem</div>
      <div class="bd-val bd-emph bd-tot">{{ perPiece(data.material_cost) }}</div>
      <div class="bd-val bd-emph bd-tot">{{ formatCurrency(data.material_cost) }}</div>

      <!-- ══ CELKEM ════════════════════════════════════ -->
      <div class="bd-lbl bd-grand-lbl">Náklady celkem</div>
      <div class="bd-val bd-grand-val">{{ formatCurrency(data.cost_per_piece) }}</div>
      <div class="bd-val bd-grand-total">{{ formatCurrency(data.total_cost) }}</div>

    </div>
  </Modal>
</template>

<style scoped>
.bd-center {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px;
}

.bd-error {
  color: var(--err);
  font-size: var(--fs);
}

/* ─── Grid ─── */
.bd-grid {
  display: grid;
  grid-template-columns: 1fr 128px 128px;
  column-gap: 20px;
  align-items: baseline;
  row-gap: 5px;
}

/* Span all 3 columns */
.g-full { grid-column: 1 / 4; }

/* Shared value spanning columns 2-3 (e.g. time, rate) */
.bd-shared {
  grid-column: 2 / 4;
  font-size: var(--fs);
  color: var(--t4);
  text-align: center;
}

/* ─── Column headers ─── */
.bd-col-h {
  font-size: var(--fsm);
  color: var(--t4);
  text-align: right;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding-bottom: 6px;
}

/* ─── Section headers ─── */
.bd-sec {
  font-size: var(--fsm);
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--t4);
  padding: 14px 0 4px;
  border-bottom: 1px solid var(--b1);
  margin-top: 2px;
}

/* ─── Labels ─── */
.bd-lbl {
  font-size: var(--fs);
  color: var(--t3);
}
.bd-indent {
  padding-left: 16px;
  color: var(--t4);
}

/* ─── Values ─── */
.bd-val {
  font-size: var(--fs);
  color: var(--t2);
  text-align: right;
  white-space: nowrap;
}

/* Sub rows — smaller */
.bd-sm { font-size: var(--fsm); }

.bd-plus { color: var(--t3); }
.bd-emph { font-weight: 600; color: var(--t1); }

/* ─── Total rows — border top on all 3 cells ─── */
.bd-tot {
  border-top: 1px solid var(--b1);
  padding-top: 6px;
  margin-top: 3px;
}

/* ─── Grand total ─── */
.bd-grand-lbl,
.bd-grand-val,
.bd-grand-total {
  border-top: 2px solid var(--b2);
  padding-top: 12px;
  margin-top: 6px;
}

.bd-grand-lbl {
  font-size: var(--fs);
  color: var(--t3);
}

.bd-grand-val {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
  text-align: right;
  white-space: nowrap;
}

.bd-grand-total {
  font-size: var(--fsh);
  font-weight: 700;
  color: var(--green);
  text-align: right;
  white-space: nowrap;
}
</style>
