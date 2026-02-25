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

    <!-- Data -->
    <template v-else-if="data">
      <!-- ── STROJNÍ NÁKLADY ─────────────────────────── -->
      <div class="bd-section-hdr">Strojní náklady</div>
      <table class="bd-tbl">
        <tbody>
          <tr>
            <td class="bd-lbl">Čas seřízení</td>
            <td class="bd-val">{{ formatNumber(data.machine_setup_time_min, 1) }} min</td>
          </tr>
          <tr>
            <td class="bd-lbl">Náklady seřízení</td>
            <td class="bd-val">{{ formatCurrency(data.machine_setup_cost) }}</td>
          </tr>
          <tr>
            <td class="bd-lbl">Čas operace</td>
            <td class="bd-val">{{ formatNumber(data.machine_operation_time_min, 1) }} min</td>
          </tr>
          <tr>
            <td class="bd-lbl">Náklady operace</td>
            <td class="bd-val">{{ formatCurrency(data.machine_operation_cost) }}</td>
          </tr>
          <tr class="bd-sub">
            <td class="bd-lbl bd-indent">Odpisy</td>
            <td class="bd-val">{{ formatCurrency(data.machine_amortization) }}</td>
          </tr>
          <tr class="bd-sub">
            <td class="bd-lbl bd-indent">Mzdy</td>
            <td class="bd-val">{{ formatCurrency(data.machine_labor) }}</td>
          </tr>
          <tr class="bd-sub">
            <td class="bd-lbl bd-indent">Nástroje</td>
            <td class="bd-val">{{ formatCurrency(data.machine_tools) }}</td>
          </tr>
          <tr class="bd-sub">
            <td class="bd-lbl bd-indent">Provozní režie</td>
            <td class="bd-val">{{ formatCurrency(data.machine_overhead) }}</td>
          </tr>
          <tr class="bd-total">
            <td class="bd-lbl">Strojní celkem</td>
            <td class="bd-val bd-emph">{{ formatCurrency(data.machine_total) }}</td>
          </tr>
        </tbody>
      </table>

      <!-- ── ZMETKOVITOST (pouze pokud > 0) ──────────── -->
      <template v-if="data.scrap_rate_percent > 0">
        <div class="bd-section-hdr">Zmetkovitost</div>
        <table class="bd-tbl">
          <tbody>
            <tr>
              <td class="bd-lbl">Procento zmetků</td>
              <td class="bd-val">{{ pct(data.scrap_rate_percent) }}</td>
            </tr>
            <tr>
              <td class="bd-lbl">Strojní po odpadu</td>
              <td class="bd-val">{{ formatCurrency(data.machine_total) }}</td>
            </tr>
          </tbody>
        </table>
      </template>

      <!-- ── REŽIE + MARŽE ────────────────────────────── -->
      <div class="bd-section-hdr">Režie + Marže</div>
      <table class="bd-tbl">
        <tbody>
          <tr>
            <td class="bd-lbl">Přirážka režie ({{ coeff(data.overhead_coefficient) }})</td>
            <td class="bd-val bd-plus">+{{ formatCurrency(data.overhead_markup) }}</td>
          </tr>
          <tr>
            <td class="bd-lbl">Přirážka marže ({{ coeff(data.margin_coefficient) }})</td>
            <td class="bd-val bd-plus">+{{ formatCurrency(data.margin_markup) }}</td>
          </tr>
          <tr class="bd-total">
            <td class="bd-lbl">Stroje s marží</td>
            <td class="bd-val bd-emph">{{ formatCurrency(data.work_with_margin) }}</td>
          </tr>
        </tbody>
      </table>

      <!-- ── KOOPERACE ─────────────────────────────────── -->
      <div class="bd-section-hdr">Kooperace ({{ coeff(data.coop_coefficient) }})</div>
      <table class="bd-tbl">
        <tbody>
          <tr>
            <td class="bd-lbl">Kooperace celkem</td>
            <td class="bd-val">{{ formatCurrency(data.coop_cost) }}</td>
          </tr>
        </tbody>
      </table>

      <!-- ── MATERIÁL ──────────────────────────────────── -->
      <div class="bd-section-hdr">Materiál ({{ coeff(data.stock_coefficient) }})</div>
      <table class="bd-tbl">
        <tbody>
          <tr>
            <td class="bd-lbl">Materiál za 1 ks (raw)</td>
            <td class="bd-val">{{ formatCurrency(data.material_cost_raw) }}</td>
          </tr>
          <tr>
            <td class="bd-lbl">Materiál celkem</td>
            <td class="bd-val">{{ formatCurrency(data.material_cost) }}</td>
          </tr>
        </tbody>
      </table>

      <!-- ══ CELKEM ════════════════════════════════════ -->
      <div class="bd-grand">
        <div class="bd-grand-row">
          <span class="bd-grand-lbl">Za kus</span>
          <span class="bd-grand-val">{{ formatCurrency(data.cost_per_piece) }}</span>
        </div>
        <div class="bd-grand-row">
          <span class="bd-grand-lbl">Dávka {{ quantity }} ks</span>
          <span class="bd-grand-total">{{ formatCurrency(data.total_cost) }}</span>
        </div>
      </div>
    </template>
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

/* ─── Section header ─── */
.bd-section-hdr {
  font-size: var(--fsm);
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--t4);
  padding: 10px 0 4px;
  border-bottom: 1px solid var(--b1);
  margin-bottom: 2px;
}

/* ─── Table ─── */
.bd-tbl {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 2px;
}

.bd-tbl td {
  padding: 3px 0;
  vertical-align: middle;
}

.bd-lbl {
  font-size: var(--fs);
  color: var(--t3);
  width: 60%;
}

.bd-indent {
  padding-left: 16px;
  color: var(--t4);
}

.bd-val {
  font-size: var(--fs);
  color: var(--t2);
  text-align: right;
  white-space: nowrap;
}

.bd-sub .bd-lbl,
.bd-sub .bd-val {
  font-size: var(--fsm);
}

.bd-plus {
  color: var(--t3);
}

.bd-total td {
  border-top: 1px solid var(--b1);
  padding-top: 5px;
  margin-top: 3px;
}

.bd-emph {
  font-weight: 600;
  color: var(--t1);
}

/* ─── Grand total ─── */
.bd-grand {
  border-top: 2px solid var(--b2);
  margin-top: 8px;
  padding-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bd-grand-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.bd-grand-lbl {
  font-size: var(--fs);
  color: var(--t3);
}

.bd-grand-val {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
}

.bd-grand-total {
  font-size: var(--fsh);
  font-weight: 700;
  color: var(--green);
}
</style>
