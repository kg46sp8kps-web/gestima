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
    <div v-if="loading" class="bd-center">
      <Spinner size="md" text="Načítám rozpad ceny…" />
    </div>

    <div v-else-if="error" class="bd-center bd-error">
      Chyba při načítání kalkulace
    </div>

    <div v-else-if="data" class="bd-body">

      <!-- Záhlaví sloupců -->
      <div class="bd-row">
        <div class="lbl"></div>
        <div class="vals">
          <div class="col-h">/ ks</div>
          <div class="col-h">dávka {{ quantity }} ks</div>
        </div>
      </div>

      <!-- ── SEŘÍZENÍ ── -->
      <div class="bd-sec">Seřízení</div>

      <div class="bd-row">
        <div class="lbl">Čas</div>
        <div class="vals"><div class="shared">{{ formatNumber(data.machine_setup_time_min, 1) }} min</div></div>
      </div>
      <div class="bd-row sm">
        <div class="lbl ind">Odpisy</div>
        <div class="vals">
          <div class="v">{{ perPiece(data.setup_amortization) }}</div>
          <div class="v">{{ formatCurrency(data.setup_amortization) }}</div>
        </div>
      </div>
      <div class="bd-row sm">
        <div class="lbl ind">Mzdy</div>
        <div class="vals">
          <div class="v">{{ perPiece(data.setup_labor) }}</div>
          <div class="v">{{ formatCurrency(data.setup_labor) }}</div>
        </div>
      </div>
      <div class="bd-row sm">
        <div class="lbl ind">Provozní režie</div>
        <div class="vals">
          <div class="v">{{ perPiece(data.setup_overhead) }}</div>
          <div class="v">{{ formatCurrency(data.setup_overhead) }}</div>
        </div>
      </div>
      <div class="bd-row tot">
        <div class="lbl">Seřízení celkem</div>
        <div class="vals">
          <div class="v emph">{{ perPiece(data.machine_setup_cost) }}</div>
          <div class="v emph">{{ formatCurrency(data.machine_setup_cost) }}</div>
        </div>
      </div>

      <!-- ── VÝROBA ── -->
      <div class="bd-sec">Výroba</div>

      <div class="bd-row">
        <div class="lbl">Čas</div>
        <div class="vals"><div class="shared">{{ formatNumber(data.machine_operation_time_min, 1) }} min</div></div>
      </div>
      <div class="bd-row sm">
        <div class="lbl ind">Odpisy</div>
        <div class="vals">
          <div class="v">{{ perPiece(data.operation_amortization) }}</div>
          <div class="v">{{ formatCurrency(data.operation_amortization) }}</div>
        </div>
      </div>
      <div class="bd-row sm">
        <div class="lbl ind">Mzdy</div>
        <div class="vals">
          <div class="v">{{ perPiece(data.operation_labor) }}</div>
          <div class="v">{{ formatCurrency(data.operation_labor) }}</div>
        </div>
      </div>
      <div class="bd-row sm">
        <div class="lbl ind">Nástroje</div>
        <div class="vals">
          <div class="v">{{ perPiece(data.operation_tools) }}</div>
          <div class="v">{{ formatCurrency(data.operation_tools) }}</div>
        </div>
      </div>
      <div class="bd-row sm">
        <div class="lbl ind">Provozní režie</div>
        <div class="vals">
          <div class="v">{{ perPiece(data.operation_overhead) }}</div>
          <div class="v">{{ formatCurrency(data.operation_overhead) }}</div>
        </div>
      </div>
      <div class="bd-row tot">
        <div class="lbl">Výroba celkem</div>
        <div class="vals">
          <div class="v emph">{{ perPiece(data.machine_operation_cost) }}</div>
          <div class="v emph">{{ formatCurrency(data.machine_operation_cost) }}</div>
        </div>
      </div>

      <!-- ── ZMETKOVITOST ── -->
      <template v-if="data.scrap_rate_percent > 0">
        <div class="bd-sec">Zmetkovitost</div>
        <div class="bd-row">
          <div class="lbl">Procento zmetků</div>
          <div class="vals"><div class="shared">{{ pct(data.scrap_rate_percent) }}</div></div>
        </div>
        <div class="bd-row tot">
          <div class="lbl">Strojní po odpadu</div>
          <div class="vals">
            <div class="v emph">{{ perPiece(data.machine_total) }}</div>
            <div class="v emph">{{ formatCurrency(data.machine_total) }}</div>
          </div>
        </div>
      </template>

      <!-- ── REŽIE + MARŽE ── -->
      <div class="bd-sec">Režie + Marže</div>

      <div class="bd-row">
        <div class="lbl">Přirážka režie ({{ coeff(data.overhead_coefficient) }})</div>
        <div class="vals">
          <div class="v plus">+{{ perPiece(data.overhead_markup) }}</div>
          <div class="v plus">+{{ formatCurrency(data.overhead_markup) }}</div>
        </div>
      </div>
      <div class="bd-row">
        <div class="lbl">Přirážka marže ({{ coeff(data.margin_coefficient) }})</div>
        <div class="vals">
          <div class="v plus">+{{ perPiece(data.margin_markup) }}</div>
          <div class="v plus">+{{ formatCurrency(data.margin_markup) }}</div>
        </div>
      </div>
      <div class="bd-row tot">
        <div class="lbl">Stroje s marží</div>
        <div class="vals">
          <div class="v emph">{{ perPiece(data.work_with_margin) }}</div>
          <div class="v emph">{{ formatCurrency(data.work_with_margin) }}</div>
        </div>
      </div>

      <!-- ── KOOPERACE ── -->
      <div class="bd-sec">Kooperace</div>

      <div class="bd-row sm">
        <div class="lbl ind">Cena raw</div>
        <div class="vals">
          <div class="v">{{ formatCurrency(data.coop_cost_raw) }}</div>
          <div class="v">{{ batchFromPiece(data.coop_cost_raw) }}</div>
        </div>
      </div>
      <div class="bd-row sm">
        <div class="lbl ind">Koef. kooperace ({{ coeff(data.coop_coefficient) }})</div>
        <div class="vals"><div class="shared"></div></div>
      </div>
      <div class="bd-row tot">
        <div class="lbl">Kooperace celkem</div>
        <div class="vals">
          <div class="v emph">{{ perPiece(data.coop_cost) }}</div>
          <div class="v emph">{{ formatCurrency(data.coop_cost) }}</div>
        </div>
      </div>

      <!-- ── MATERIÁL ── -->
      <div class="bd-sec">Materiál</div>

      <div v-if="data.material_weight_kg > 0" class="bd-row">
        <div class="lbl">Hmotnost / ks</div>
        <div class="vals"><div class="shared">{{ formatNumber(data.material_weight_kg, 4) }} kg</div></div>
      </div>
      <div v-if="data.material_price_per_kg > 0" class="bd-row">
        <div class="lbl">Cena materiálu</div>
        <div class="vals"><div class="shared">{{ formatCurrency(data.material_price_per_kg) }} / kg</div></div>
      </div>
      <div class="bd-row sm">
        <div class="lbl ind">Cena raw</div>
        <div class="vals">
          <div class="v">{{ formatCurrency(data.material_cost_raw) }}</div>
          <div class="v">{{ batchFromPiece(data.material_cost_raw) }}</div>
        </div>
      </div>
      <div class="bd-row sm">
        <div class="lbl ind">Koef. skladu ({{ coeff(data.stock_coefficient) }})</div>
        <div class="vals"><div class="shared"></div></div>
      </div>
      <div class="bd-row tot">
        <div class="lbl">Materiál celkem</div>
        <div class="vals">
          <div class="v emph">{{ perPiece(data.material_cost) }}</div>
          <div class="v emph">{{ formatCurrency(data.material_cost) }}</div>
        </div>
      </div>

      <!-- ══ CELKEM ══ -->
      <div class="bd-row grand">
        <div class="lbl">Náklady celkem</div>
        <div class="vals">
          <div class="v grand-val">{{ formatCurrency(data.cost_per_piece) }}</div>
          <div class="v grand-total">{{ formatCurrency(data.total_cost) }}</div>
        </div>
      </div>

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
.bd-error { color: var(--err); font-size: var(--fs); }

/* ─── Každý řádek je flex ─── */
.bd-row {
  display: flex;
  align-items: center;
  padding: 3px 0;
}

/* Levý sloupec — bere zbývající místo */
.lbl {
  flex: 1;
  min-width: 0;
  font-size: var(--fs);
  color: var(--t3);
  padding-right: 12px;
}
.ind { padding-left: 16px; color: var(--t4); }

/* Pravá skupina — 140 + 20px gap + 140 = 300px */
.vals {
  flex: 0 0 300px;
  display: flex;
  align-items: center;
  gap: 20px;
}

/* Každý value sloupec — přesně 140px */
.v {
  flex: 0 0 140px;
  text-align: center;
  font-size: var(--fs);
  color: var(--t2);
  white-space: nowrap;
}

/* Záhlaví sloupců — 140px, centrováno */
.col-h {
  flex: 0 0 140px;
  text-align: center;
  font-size: var(--fsm);
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding-bottom: 6px;
}

/* Sdílená hodnota — vyplní celých 300px (140 + gap 20 + 140), text na střed
   Střed = 150px = přesně mezi oběma sloupci */
.shared {
  flex: 1;
  text-align: center;
  font-size: var(--fs);
  color: var(--t4);
}

/* Sekce */
.bd-sec {
  font-size: var(--fsm);
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--t4);
  padding: 14px 0 4px;
  border-bottom: 1px solid var(--b1);
}

/* Malé řádky */
.sm .lbl { font-size: var(--fsm); }
.sm .v   { font-size: var(--fsm); }
.sm .shared { font-size: var(--fsm); }

/* Barvy */
.plus { color: var(--t3); }
.emph { font-weight: 600; color: var(--t1); }

/* Oddělovací řádky */
.tot {
  border-top: 1px solid var(--b1);
  padding-top: 6px;
  margin-top: 2px;
}

/* Grand total */
.grand {
  border-top: 2px solid var(--b2);
  padding-top: 12px;
  margin-top: 6px;
}
.grand-val   { font-weight: 700; color: var(--t1); }
.grand-total { font-weight: 700; color: var(--green); }
</style>
