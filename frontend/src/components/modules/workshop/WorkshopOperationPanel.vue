<template>
  <div class="oper-panel" data-testid="workshop-operation-panel">
    <!-- Žádná operace vybrána -->
    <div v-if="!store.activeQueueItem" class="oper-panel__empty">
      <span>Vyberte operaci z fronty</span>
    </div>

    <template v-else>
      <!-- Toggle: Seřizuji vs Vyrábím -->
      <div class="oper-panel__mode" data-testid="work-mode-toggle">
        <button
          class="mode-btn"
          :class="{ 'mode-btn--active': store.workMode === 'setup' }"
          data-testid="mode-btn-setup"
          @click="store.setWorkMode('setup')"
        >
          <Wrench :size="16" />
          <span>Seřizuji</span>
        </button>
        <button
          class="mode-btn"
          :class="{ 'mode-btn--active': store.workMode === 'production' }"
          data-testid="mode-btn-production"
          @click="store.setWorkMode('production')"
        >
          <Cog :size="16" />
          <span>Vyrábím</span>
        </button>
      </div>

      <!-- Hlavička zakázky -->
      <div class="oper-panel__job-header">
        <div class="oper-panel__job-title">
          <span class="oper-panel__job-num">{{ store.activeQueueItem.Job }}</span>
          <span class="oper-panel__job-oper">Op {{ store.activeQueueItem.OperNum }}</span>
          <span class="oper-panel__job-item">{{ store.activeQueueItem.DerJobItem }}</span>
        </div>
        <span class="oper-panel__job-desc">{{ store.activeQueueItem.JobDescription }}</span>
        <div class="oper-panel__job-plan" data-testid="oper-plan-times">
          <span>Plán od: {{ formatInforDate(store.activeQueueItem.OpDatumSt) }}</span>
          <span>Plán do: {{ formatInforDate(store.activeQueueItem.OpDatumSp) }}</span>
        </div>
      </div>

      <!-- Materiály k operaci -->
      <div class="oper-panel__materials">
        <div class="oper-panel__materials-header">
          <span>Materiály</span>
          <Spinner v-if="store.loadingMaterials" size="sm" inline />
        </div>

        <div v-if="!store.loadingMaterials && store.materials.length === 0" class="oper-panel__no-materials">
          Bez materiálů
        </div>

        <div v-else class="mat-table-wrap">
          <table class="mat-table">
            <thead>
              <tr>
                <th @click="toggleMaterialSort('Material')">Materiál <span>{{ materialSortMark('Material') }}</span></th>
                <th @click="toggleMaterialSort('Desc')">Popis <span>{{ materialSortMark('Desc') }}</span></th>
                <th class="num" @click="toggleMaterialSort('Qty')">Na ks <span>{{ materialSortMark('Qty') }}</span></th>
                <th class="num" @click="toggleMaterialSort('BatchCons')">Dávka <span>{{ materialSortMark('BatchCons') }}</span></th>
                <th class="num">Odvedeno</th>
                <th>Jedn.</th>
                <th class="action">Odvod</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="mat in store.materials"
                :key="`${activeMaterialKey}-${mat.Material}`"
                :data-testid="`mat-row-${mat.Material}`"
              >
                <td class="mat-code">{{ mat.Material }}</td>
                <td class="mat-desc">{{ mat.Desc ?? '—' }}</td>
                <td class="num">{{ formatMaterialQty(mat.Qty, mat.UM) }}</td>
                <td class="num">{{ formatMaterialQty(mat.BatchCons, mat.UM) }}</td>
                <td class="num">{{ formatMaterialQty(mat.QtyIssued, mat.UM) }}</td>
                <td>{{ mat.UM ?? '—' }}</td>
                <td class="action">
                  <button
                    class="btn-secondary mat-issue-trigger"
                    :data-testid="`mat-issue-open-${mat.Material}`"
                    :disabled="isCoopWorkcenter"
                    @click="openMaterialIssue(mat.Material)"
                  >
                    {{ isCoopWorkcenter ? 'Kooperace' : 'Odvést' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="isCoopWorkcenter" class="oper-panel__coop-note">
          Odvod materiálu je na kooperaci (`Wc` začíná `KOO`) zablokován.
        </div>
        <div v-if="materialIssueOpen" class="mat-issue-form" data-testid="mat-issue-form">
          <div class="mat-issue-form__title">
            Odvod materiálu: <strong>{{ materialIssue.material }}</strong>
          </div>
          <div class="mat-issue-form__note">
            Sklad: <strong>MAIN</strong>, skladové místo: <strong>PRIJEM</strong>
          </div>
          <div class="mat-issue-form__fields">
            <Select
              :model-value="materialIssue.um"
              :options="materialIssue.ums.map((um) => ({ value: um, label: um }))"
              label="Jednotka"
              placeholder="Vyberte jednotku"
              @update:model-value="onMaterialIssueUmChange"
            />
            <Input
              :model-value="materialIssue.qty != null ? String(materialIssue.qty) : null"
              type="number"
              :label="materialIssue.um ? `Množství (${materialIssue.um})` : 'Množství'"
              :min="0.0001"
              :step="0.01"
              testid="mat-issue-qty"
              @update:model-value="materialIssue.qty = $event != null ? Number($event) : null"
            />
          </div>
          <div class="mat-issue-form__actions">
            <button
              class="timer-btn timer-btn--stop"
              data-testid="mat-issue-submit"
              @click="submitMaterialIssue"
            >
              Odeslat odvod
            </button>
            <button class="btn-secondary" data-testid="mat-issue-cancel" @click="cancelMaterialIssue">
              Zrušit
            </button>
          </div>
        </div>
      </div>

      <!-- Časovač -->
      <div class="oper-panel__timer">
        <div class="timer-display" :class="{ 'timer-display--running': store.timer.running }">
          <span class="timer-display__time">{{ formattedTime }}</span>
          <span class="timer-display__label">{{ store.timer.running ? 'Probíhá' : 'Připraveno' }}</span>
        </div>

        <!-- START (timer neběží) -->
        <div v-if="!store.timer.running" class="timer-buttons">
          <button
            class="timer-btn timer-btn--start"
            :disabled="store.startingTimer"
            data-testid="timer-start"
            @click="onStartTimer"
          >
            <Loader v-if="store.startingTimer" :size="ICON_SIZE_LG" class="timer-btn__spin" />
            <Play v-else :size="ICON_SIZE_LG" />
            <span>{{ store.startingTimer ? 'Odesílám…' : 'START' }}</span>
          </button>
        </div>

        <!-- STOP sekce (timer běží) -->
        <template v-else>
          <!-- Seřízení: přímý stop bez formuláře -->
          <div v-if="store.timer.mode === 'setup'" class="timer-buttons">
            <button
              class="timer-btn timer-btn--stop"
              data-testid="timer-stop"
              @click="onSetupStop"
            >
              <Square :size="ICON_SIZE_LG" />
              <span>Ukončit seřízení</span>
            </button>
          </div>

          <!-- Výroba: STOP tlačítko → inline formulář s kusy -->
          <template v-else>
            <!-- Trigger STOP -->
            <div v-if="!showStopForm" class="timer-buttons">
              <button
                class="timer-btn timer-btn--stop"
                data-testid="timer-stop"
                @click="openStopForm"
              >
                <Square :size="ICON_SIZE_LG" />
                <span>STOP</span>
              </button>
            </div>

            <!-- Inline formulář pro zadání kusů při STOP -->
            <div v-else class="timer-stop-form" data-testid="timer-stop-form">
              <div v-if="qtyRemaining !== null" class="stop-qty-hint" data-testid="stop-qty-hint">
                <span class="stop-qty-hint__label">Zbývá k odvedení</span>
                <span class="stop-qty-hint__value">{{ qtyRemaining }} ks</span>
              </div>
              <div
                v-if="isSawWorkcenter"
                class="stop-qty-policy stop-qty-policy--warn"
                data-testid="stop-qty-policy-saw"
              >
                Na pile lze vykázat více kusů. U první operace se po odvodu automaticky navýší VP.
              </div>
              <div
                v-else
                class="stop-qty-policy"
                data-testid="stop-qty-policy-standard"
              >
                Mimo pilu nelze vykázat více kusů než zbývá na operaci.
              </div>
              <Input
                :model-value="stopForm.qty_completed != null ? String(stopForm.qty_completed) : null"
                type="number"
                label="Hotové kusy"
                placeholder="0"
                :min="0"
                :step="1"
                testid="stop-qty-completed"
                class="timer-stop-form__input--large"
                @update:model-value="stopForm.qty_completed = $event != null ? Number($event) : null"
              />
              <Input
                :model-value="stopForm.qty_scrapped != null ? String(stopForm.qty_scrapped) : null"
                type="number"
                label="Zmetky"
                placeholder="0"
                :min="0"
                :step="1"
                testid="stop-qty-scrapped"
                @update:model-value="stopForm.qty_scrapped = $event != null ? Number($event) : null"
              />
              <label class="flag-check" data-testid="stop-oper-complete">
                <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
                <input
                  v-model="stopForm.oper_complete"
                  type="checkbox"
                  class="flag-check__input"
                />
                <span class="flag-check__label">Operace dokončena</span>
              </label>
              <div class="timer-stop-form__actions">
                <button
                  class="timer-btn timer-btn--stop timer-stop-form__confirm"
                  data-testid="timer-stop-confirm"
                  @click="onProductionStop"
                >
                  <Square :size="20" />
                  <span>Potvrdit STOP</span>
                </button>
                <button
                  class="btn-secondary timer-stop-form__cancel"
                  data-testid="timer-stop-cancel"
                  @click="cancelStopForm"
                >
                  Zrušit
                </button>
              </div>
            </div>
          </template>
        </template>

        <!-- Info o aktivním timeru (jiná zakázka) -->
        <div
          v-if="store.timer.running && store.timer.job !== store.activeQueueItem?.Job"
          class="timer-warn"
        >
          Časovač běží pro jinou zakázku: {{ store.timer.job }} / Op {{ store.timer.operNum }}
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Play, Square, Wrench, Cog, Loader } from 'lucide-vue-next'
import { useWorkshopStore } from '@/stores/workshop'
import { useUiStore } from '@/stores/ui'
import Spinner from '@/components/ui/Spinner.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import { formatInforDate } from '@/utils/formatters'
import type { WorkshopMaterialSortBy } from '@/types/workshop'

const ICON_SIZE_LG = 28

const store = useWorkshopStore()
const ui = useUiStore()

const formattedTime = computed(() => {
  const s = store.timerElapsed
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  return [
    h.toString().padStart(2, '0'),
    m.toString().padStart(2, '0'),
    sec.toString().padStart(2, '0'),
  ].join(':')
})

// Inline STOP formulář pro výrobní mód
const showStopForm = ref(false)
const stopForm = ref({
  qty_completed: null as number | null,
  qty_scrapped: null as number | null,
  oper_complete: false,
})
const SAW_WC_PREFIXES = ['PS', 'PILA', 'SAW']
const materialSortBy = ref<WorkshopMaterialSortBy>(store.materialSortBy)
const materialIssueOpen = ref(false)
const materialIssue = ref({
  material: '' as string,
  qty: null as number | null,
  um: null as string | null,
  ums: [] as string[],
})
const activeMaterialKey = computed(() => {
  const item = store.activeQueueItem
  if (!item) return 'none'
  return `${item.Job}-${item.Suffix}-${item.OperNum}`
})

/** Zbývající kusy k odvedení (JobQtyReleased - QtyComplete). Zobrazeno jako nápověda. */
const qtyRemaining = computed(() => {
  const item = store.activeQueueItem
  if (!item) return null
  const released = item.JobQtyReleased ?? 0
  const completed = item.QtyComplete ?? 0
  const scrapped = item.QtyScrapped ?? 0
  return Math.max(0, Math.round(released - completed - scrapped))
})

const isSawWorkcenter = computed(() => {
  const wc = (store.activeQueueItem?.Wc ?? '').trim().toUpperCase()
  if (!wc) return false
  return SAW_WC_PREFIXES.some((prefix) => wc.startsWith(prefix))
})

const isCoopWorkcenter = computed(() => {
  const wc = (store.activeQueueItem?.Wc ?? '').trim().toUpperCase()
  if (!wc) return false
  return wc.startsWith('KOO')
})

function openStopForm() {
  stopForm.value = {
    qty_completed: qtyRemaining.value,
    qty_scrapped: null,
    oper_complete: false,
  }
  showStopForm.value = true
}

function cancelStopForm() {
  showStopForm.value = false
  stopForm.value = { qty_completed: null, qty_scrapped: null, oper_complete: false }
}

function toggleMaterialSort(column: WorkshopMaterialSortBy) {
  if (materialSortBy.value === column) {
    store.materialSortDir = store.materialSortDir === 'asc' ? 'desc' : 'asc'
  } else {
    materialSortBy.value = column
    store.materialSortDir = 'asc'
  }
  store.setMaterialSort(materialSortBy.value, store.materialSortDir)
  const item = store.activeQueueItem
  if (!item) return
  void store.fetchMaterials(item.Job, item.OperNum, item.Suffix)
}

function materialSortMark(column: WorkshopMaterialSortBy): string {
  if (materialSortBy.value !== column) return ''
  return store.materialSortDir === 'asc' ? '▲' : '▼'
}

function openMaterialIssue(material: string) {
  const selected = store.materials.find((mat) => mat.Material === material)
  const availableUms = (selected?.UMs ?? []).filter((candidate) => !!candidate)
  if (selected?.UM && !availableUms.includes(selected.UM)) {
    availableUms.push(selected.UM)
  }
  const defaultUm = selected?.UM ?? availableUms[0] ?? null
  const batchByUm = selected?.BatchConsByUM ?? {}
  const qtyFromUm = defaultUm ? (batchByUm[defaultUm] ?? null) : null
  materialIssue.value = {
    material,
    qty: qtyFromUm ?? selected?.BatchCons ?? null,
    um: defaultUm,
    ums: availableUms,
  }
  materialIssueOpen.value = true
}

function cancelMaterialIssue() {
  materialIssueOpen.value = false
}

watch(
  () => store.activeQueueItem,
  () => {
    materialIssueOpen.value = false
    materialIssue.value = {
      material: '',
      qty: null,
      um: null,
      ums: [],
    }
  },
)

function onMaterialIssueUmChange(value: string | number | null) {
  const selectedUm = typeof value === 'string' ? value : null
  materialIssue.value.um = selectedUm
  if (!selectedUm) return
  const selected = store.materials.find((mat) => mat.Material === materialIssue.value.material)
  if (!selected) return
  const batchByUm = selected.BatchConsByUM ?? {}
  const suggested = batchByUm[selectedUm]
  if (suggested != null) {
    materialIssue.value.qty = suggested
  }
}

async function submitMaterialIssue() {
  const item = store.activeQueueItem
  const qty = materialIssue.value.qty ?? 0
  if (!item || !materialIssue.value.material) return
  if (isCoopWorkcenter.value) {
    ui.showError('Odvod materiálu je na kooperaci zablokován')
    return
  }
  if (qty <= 0) {
    ui.showError('Množství materiálu musí být větší než 0')
    return
  }
  const posted = await store.postMaterialIssue({
    job: item.Job,
    suffix: item.Suffix,
    oper_num: item.OperNum,
    material: materialIssue.value.material,
    um: materialIssue.value.um,
    qty,
    wc: item.Wc,
  })
  if (posted) {
    materialIssueOpen.value = false
  }
}

function formatMaterialQty(value: number | null | undefined, um: string | null | undefined): string {
  if (value == null) return '—'
  if (!um) return String(value)
  return `${value} ${um}`
}

async function onStartTimer() {
  if (!store.activeJob || !store.activeOperation) return
  if (store.timer.running) {
    ui.showError('Časovač již běží. Nejdřív ho zastavte.')
    return
  }
  await store.startTimer(store.activeJob, store.activeOperation)
}

async function onSetupStop() {
  await store.stopTimer()
}

async function onProductionStop() {
  const qtyCompleted = stopForm.value.qty_completed ?? 0
  const qtyScrapped = stopForm.value.qty_scrapped ?? 0
  const requestedTotal = qtyCompleted + qtyScrapped
  const remaining = qtyRemaining.value

  if (
    remaining != null &&
    requestedTotal > remaining &&
    !isSawWorkcenter.value
  ) {
    ui.showError(`Nelze vykázat více kusů než zbývá (${remaining} ks).`)
    return
  }

  if (
    remaining != null &&
    requestedTotal > remaining &&
    isSawWorkcenter.value
  ) {
    ui.showWarning('Přeodvod na pile: po odvodu proběhne pokus o navýšení VP.')
  }

  showStopForm.value = false
  await store.stopTimer({
    qty_completed: stopForm.value.qty_completed,
    qty_scrapped: stopForm.value.qty_scrapped,
    oper_complete: stopForm.value.oper_complete,
  })
  stopForm.value = { qty_completed: null, qty_scrapped: null, oper_complete: false }
}
</script>

<style scoped>
.oper-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}

.oper-panel__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--t3);
  font-size: var(--fs);
}

/* Seřizuji / Vyrábím toggle */
.oper-panel__mode {
  display: flex;
  gap: 0;
  padding: var(--pad);
  border-bottom: 1px solid var(--b2);
  flex-shrink: 0;
}

.mode-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex: 1;
  min-height: 44px;
  background: var(--surface);
  border: 1px solid var(--b2);
  cursor: pointer;
  font-family: var(--font);
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t3);
  transition: background 120ms var(--ease), color 120ms var(--ease);
}

.mode-btn:first-child {
  border-radius: var(--r) 0 0 var(--r);
  border-right: none;
}

.mode-btn:last-child {
  border-radius: 0 var(--r) var(--r) 0;
}

.mode-btn--active {
  background: var(--raised);
  color: var(--t1);
  border-color: var(--b3);
}

.mode-btn:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.5);
  outline-offset: 2px;
}

/* Hlavička zakázky */
.oper-panel__job-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px var(--pad);
  border-bottom: 1px solid var(--b2);
  flex-shrink: 0;
}

.oper-panel__job-title {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}

.oper-panel__job-num {
  font-size: var(--fsh);
  font-weight: 700;
  color: var(--t1);
}

.oper-panel__job-oper {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--red);
}

.oper-panel__job-item {
  font-size: var(--fs);
  color: var(--t2);
}

.oper-panel__job-desc {
  font-size: var(--fsm);
  color: var(--t3);
}

.oper-panel__job-plan {
  margin-top: 4px;
  display: grid;
  gap: 2px;
  font-size: var(--fss);
  color: var(--t2);
}

/* Materiály */
.oper-panel__materials {
  padding: var(--pad);
  border-bottom: 1px solid var(--b2);
  flex-shrink: 0;
}

.oper-panel__materials-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fsm);
  font-weight: 500;
  color: var(--t3);
  margin-bottom: 6px;
}

.oper-panel__no-materials {
  font-size: var(--fsm);
  color: var(--t4);
  padding: 4px 0;
}

.oper-panel__coop-note {
  margin-top: 8px;
  font-size: var(--fss);
  color: var(--warn);
}

.mat-table-wrap {
  overflow-x: auto;
}

.mat-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fss);
}

.mat-table th {
  text-align: left;
  color: var(--t3);
  font-weight: 600;
  border-bottom: 1px solid var(--b2);
  padding: 6px 4px;
  cursor: pointer;
  white-space: nowrap;
}

.mat-table td {
  border-bottom: 1px solid var(--b1);
  padding: 7px 4px;
  color: var(--t2);
}

.mat-table .num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.mat-table .action {
  text-align: right;
}

.mat-code {
  font-weight: 600;
}

.mat-desc {
  max-width: 160px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mat-issue-trigger {
  min-height: 30px;
  padding: 4px 8px;
}

.mat-issue-form {
  margin-top: 10px;
  padding: 10px;
  border: 1px solid var(--b2);
  border-radius: var(--r);
  background: var(--surface);
}

.mat-issue-form__title {
  font-size: var(--fsm);
  color: var(--t2);
  margin-bottom: 8px;
}

.mat-issue-form__note {
  font-size: var(--fss);
  color: var(--t3);
  margin-bottom: 8px;
}

.mat-issue-form__fields {
  display: grid;
  gap: 8px;
}

.mat-issue-form__actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}

/* Časovač */
.oper-panel__timer {
  padding: var(--pad);
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex-shrink: 0;
}

.timer-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
  background: var(--ground);
  border-radius: var(--r);
  border: 1px solid var(--b2);
}

.timer-display--running {
  border-color: var(--ok);
  box-shadow: 0 0 12px rgba(0, 0, 0, 0.5);
}

.timer-display__time {
  font-size: 48px;
  font-weight: 700;
  font-family: var(--font);
  color: var(--t1);
  letter-spacing: 4px;
}

.timer-display__label {
  font-size: var(--fsm);
  color: var(--t3);
  margin-top: 4px;
}

.timer-buttons {
  display: flex;
  gap: var(--pad);
}

/* Velká tlačítka START/STOP */
.timer-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex: 1;
  min-height: 64px;
  border-radius: var(--r);
  border: none;
  cursor: pointer;
  font-family: var(--font);
  font-size: var(--fsh);
  font-weight: 700;
  letter-spacing: 1px;
  transition: opacity 120ms var(--ease);
}

.timer-btn:active {
  opacity: 0.8;
}

.timer-btn:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.5);
  outline-offset: 2px;
}

.timer-btn--start {
  background: var(--ok);
  color: var(--base);
}

.timer-btn--stop {
  background: var(--err);
  color: var(--base);
}

.timer-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.timer-btn__spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* Inline STOP formulář */
.timer-stop-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  background: var(--ground);
  border-radius: var(--r);
  border: 1px solid var(--b3);
}

.stop-qty-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
}

.stop-qty-hint__label {
  font-size: var(--fsm);
  color: var(--t3);
}

.stop-qty-hint__value {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
}

.stop-qty-policy {
  margin-top: 8px;
  margin-bottom: 2px;
  padding: 8px 10px;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  font-size: var(--fss);
  color: var(--t3);
}

.stop-qty-policy--warn {
  border-color: var(--warn);
}

.timer-stop-form__input--large :deep(.input-ctrl) {
  min-height: 52px;
  font-size: 24px;
  font-weight: 700;
  text-align: center;
  padding: 8px 12px;
}

.flag-check {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  cursor: pointer;
}

.flag-check__input {
  width: 20px;
  height: 20px;
  accent-color: var(--red);
  cursor: pointer;
}

.flag-check__label {
  font-size: var(--fs);
  color: var(--t2);
}

.timer-stop-form__actions {
  display: flex;
  gap: var(--pad);
}

.timer-stop-form__confirm {
  flex: 2;
  min-height: 52px;
  font-size: var(--fs);
  letter-spacing: 0.5px;
}

.timer-stop-form__cancel {
  flex: 1;
  min-height: 52px;
  padding: 8px 12px;
  font-size: var(--fs);
}

.timer-warn {
  font-size: var(--fsm);
  color: var(--warn);
  padding: 8px;
  background: var(--ground);
  border-radius: var(--rs);
  border: 1px solid var(--warn);
}
</style>
