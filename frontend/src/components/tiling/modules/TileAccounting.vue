<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import * as accountingApi from '@/api/accounting'
import type { DashboardOverview } from '@/types/accounting'
import type { ContextGroup } from '@/types/workspace'
import { formatCurrency } from '@/utils/formatters'
import Spinner from '@/components/ui/Spinner.vue'

// Module-level cache: year → data
const _cache = new Map<number, DashboardOverview>()

interface Props {
  leafId: string
  ctx: ContextGroup
}

defineProps<Props>()

const year = ref(new Date().getFullYear())
const data = ref<DashboardOverview | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const MONTHS = ['Led', 'Úno', 'Bře', 'Dub', 'Kvě', 'Čvn', 'Čvc', 'Srp', 'Zář', 'Říj', 'Lis', 'Pro']

function yoyBadge(pct: number | null): string {
  if (pct == null) return ''
  return (pct >= 0 ? '+' : '') + pct.toFixed(1) + ' %'
}

function yoyClass(pct: number | null): string {
  if (pct == null) return ''
  return pct >= 0 ? 'yoy-pos' : 'yoy-neg'
}

async function loadOverview(y: number) {
  if (_cache.has(y)) {
    data.value = _cache.get(y)!
    return
  }
  loading.value = true
  error.value = null
  try {
    const result = await accountingApi.getDashboardOverview(y)
    _cache.set(y, result)
    data.value = result
  } catch (err) {
    const e = err as { response?: { status?: number } }
    if (e.response?.status === 403) {
      error.value = 'Přístup pouze pro administrátory'
    } else if (e.response?.status === 501) {
      error.value = 'Účetní API není nakonfigurováno'
    } else {
      error.value = 'Chyba při načítání účetního přehledu'
    }
  } finally {
    loading.value = false
  }
}

watch(year, loadOverview)
onMounted(() => loadOverview(year.value))
</script>

<template>
  <div class="wacc">
    <!-- Year selector -->
    <div class="yr-bar">
      <button
        class="icon-btn yr-btn"
        data-testid="year-prev"
        @click="year--"
      >‹</button>
      <span class="yr-val">{{ year }}</span>
      <button
        class="icon-btn yr-btn"
        data-testid="year-next"
        @click="year++"
      >›</button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">{{ error }}</span>
    </div>

    <!-- Data -->
    <template v-else-if="data">
      <!-- KPI cards -->
      <div class="kpi-row">
        <div class="kpi-card" data-testid="kpi-revenue">
          <div class="kpi-label">Výnosy YTD</div>
          <div class="kpi-val green">{{ formatCurrency(data.ytd_revenue) }}</div>
          <div v-if="data.revenue_yoy_pct != null" :class="['kpi-yoy', yoyClass(data.revenue_yoy_pct)]">
            {{ yoyBadge(data.revenue_yoy_pct) }} YoY
          </div>
        </div>
        <div class="kpi-card" data-testid="kpi-expenses">
          <div class="kpi-label">Náklady YTD</div>
          <div class="kpi-val red">{{ formatCurrency(data.ytd_expenses) }}</div>
        </div>
        <div class="kpi-card" data-testid="kpi-profit">
          <div class="kpi-label">Zisk YTD</div>
          <div :class="['kpi-val', data.ytd_profit >= 0 ? 'green' : 'red']">
            {{ formatCurrency(data.ytd_profit) }}
          </div>
          <div v-if="data.ytd_margin_pct != null" class="kpi-yoy t4">
            Marže {{ data.ytd_margin_pct.toFixed(1) }} %
          </div>
        </div>
      </div>

      <!-- Monthly table (last 5 non-zero months) -->
      <div class="ot-wrap">
        <table class="ot">
          <thead>
            <tr>
              <th>Měsíc</th>
              <th class="r">Výnosy</th>
              <th class="r">Náklady</th>
              <th class="r">Zisk</th>
              <th class="r" style="width:56px">Marže</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="m in data.monthly" :key="m.mesic">
              <tr v-if="m.revenue > 0 || m.expenses > 0" :data-testid="`month-row-${m.mesic}`">
                <td>{{ MONTHS[m.mesic - 1] }}</td>
                <td class="r green">{{ formatCurrency(m.revenue) }}</td>
                <td class="r t3">{{ formatCurrency(m.expenses) }}</td>
                <td :class="['r', m.profit >= 0 ? 'green' : 'red']">
                  {{ formatCurrency(m.profit) }}
                </td>
                <td class="r t4">
                  {{ m.revenue > 0 ? (m.profit / m.revenue * 100).toFixed(1) + ' %' : '—' }}
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </template>

    <!-- No data yet -->
    <div v-else class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Načítání…</span>
    </div>
  </div>
</template>

<style scoped>
.wacc {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

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
.mod-label { font-size: var(--fsl); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

/* Year selector */
.yr-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
/* yr-btn overrides icon-btn size + adds border for year nav context */
.yr-btn {
  width: 20px;
  height: 20px;
  background: var(--b1);
  border: 1px solid var(--b2);
  font-size: var(--fsh);
}
.yr-btn:hover { border-color: var(--b3); }
.yr-val {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
  min-width: 40px;
  text-align: center;
}

/* KPI row */
.kpi-row {
  display: flex;
  gap: 1px;
  padding: 8px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
  background: rgba(255,255,255,0.02);
}
.kpi-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 8px;
}
.kpi-label {
  font-size: var(--fsm);
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 500;
}
.kpi-val {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
  white-space: nowrap;
}
.kpi-val.green { color: var(--green); }
.kpi-val.red { color: var(--err); }
.kpi-yoy {
  font-size: var(--fsm);
  color: var(--t4);
}
.yoy-pos { color: var(--ok); }
.yoy-neg { color: var(--err); }
.t4 { color: var(--t4); }

/* Table */
.ot-wrap {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

.t3 { color: var(--t3); }
.green { color: var(--green); }
.red { color: var(--err); }
.r { text-align: right; }
</style>
