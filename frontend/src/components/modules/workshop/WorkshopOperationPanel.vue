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
          @click="store.workMode = 'setup'"
        >
          <Wrench :size="16" />
          <span>Seřizuji</span>
        </button>
        <button
          class="mode-btn"
          :class="{ 'mode-btn--active': store.workMode === 'production' }"
          data-testid="mode-btn-production"
          @click="store.workMode = 'production'"
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

        <div
          v-for="mat in store.materials"
          :key="mat.Material"
          class="mat-row"
          :data-testid="`mat-row-${mat.Material}`"
        >
          <span class="mat-row__code">{{ mat.Material }}</span>
          <span class="mat-row__desc">{{ mat.Desc ?? '—' }}</span>
          <span class="mat-row__qty">{{ mat.BatchCons ?? mat.TotCons ?? '?' }}</span>
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
                @click="showStopForm = true"
              >
                <Square :size="ICON_SIZE_LG" />
                <span>STOP</span>
              </button>
            </div>

            <!-- Inline formulář pro zadání kusů při STOP -->
            <div v-else class="timer-stop-form" data-testid="timer-stop-form">
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
import { ref, computed } from 'vue'
import { Play, Square, Wrench, Cog, Loader } from 'lucide-vue-next'
import { useWorkshopStore } from '@/stores/workshop'
import { useUiStore } from '@/stores/ui'
import Spinner from '@/components/ui/Spinner.vue'
import Input from '@/components/ui/Input.vue'

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

function cancelStopForm() {
  showStopForm.value = false
  stopForm.value = { qty_completed: null, qty_scrapped: null, oper_complete: false }
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

.mat-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--b1);
  font-size: var(--fsm);
}

.mat-row:last-child {
  border-bottom: none;
}

.mat-row__code {
  font-weight: 600;
  color: var(--t2);
  min-width: 80px;
  font-size: var(--fss);
}

.mat-row__desc {
  color: var(--t3);
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mat-row__qty {
  color: var(--t1);
  font-weight: 500;
  text-align: right;
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
