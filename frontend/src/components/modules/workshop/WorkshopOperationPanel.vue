<template>
  <div class="oper-panel" data-testid="workshop-operation-panel">
    <!-- Žádná zakázka vybrána -->
    <div v-if="!store.activeJob" class="oper-panel__empty">
      <span>Vyberte zakázku ze seznamu</span>
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
          <span class="oper-panel__job-num">{{ store.activeJob.Job }}</span>
          <span class="oper-panel__job-item">{{ store.activeJob.DerJobItem }}</span>
        </div>
        <span class="oper-panel__job-desc">{{ store.activeJob.JobDescription }}</span>
      </div>

      <!-- Loading operací -->
      <div v-if="store.loadingOperations" class="oper-panel__loading">
        <Spinner text="Načítám operace…" />
      </div>

      <!-- Operace -->
      <div v-else class="oper-panel__opers">
        <button
          v-for="oper in store.operations"
          :key="oper.OperNum"
          class="oper-btn"
          :class="{ 'oper-btn--active': isActiveOper(oper) }"
          :data-testid="`oper-btn-${oper.OperNum}`"
          @click="store.selectOperation(oper)"
        >
          <span class="oper-btn__num">Op {{ oper.OperNum }}</span>
          <span class="oper-btn__wc">{{ oper.Wc }}</span>
          <span v-if="oper.QtyComplete != null" class="oper-btn__qty">
            {{ Math.round(oper.QtyComplete) }}/{{ oper.QtyReleased != null ? Math.round(oper.QtyReleased) : '?' }} ks
          </span>
          <!-- Plánované hodiny dle módu -->
          <span v-if="store.workMode === 'setup' && oper.SetupHrs" class="oper-btn__hrs">
            {{ oper.SetupHrs }} hod seř.
          </span>
          <span v-else-if="store.workMode === 'production' && oper.RunHrs" class="oper-btn__hrs">
            {{ oper.RunHrs }} hod/ks
          </span>
        </button>
      </div>

      <!-- Materiály k vybrané operaci -->
      <div v-if="store.activeOperation" class="oper-panel__materials">
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

      <!-- Časovač (zobrazí se jen když je operace vybrána) -->
      <div v-if="store.activeOperation" class="oper-panel__timer">
        <div class="timer-display" :class="{ 'timer-display--running': store.timer.running }">
          <span class="timer-display__time">{{ formattedTime }}</span>
          <span class="timer-display__label">{{ store.timer.running ? 'Probíhá' : 'Připraveno' }}</span>
        </div>

        <!-- START / STOP tlačítka -->
        <div class="timer-buttons">
          <button
            v-if="!store.timer.running"
            class="timer-btn timer-btn--start"
            :disabled="store.startingTimer"
            data-testid="timer-start"
            @click="onStartTimer"
          >
            <Loader v-if="store.startingTimer" :size="ICON_SIZE_LG" class="timer-btn__spin" />
            <Play v-else :size="ICON_SIZE_LG" />
            <span>{{ store.startingTimer ? 'Odesílám…' : 'START' }}</span>
          </button>
          <button
            v-else
            class="timer-btn timer-btn--stop"
            data-testid="timer-stop"
            @click="onStopTimer"
          >
            <Square :size="ICON_SIZE_LG" />
            <span>STOP</span>
          </button>
        </div>

        <!-- Info o aktivním timeru (jiná zakázka) -->
        <div
          v-if="store.timer.running && store.timer.job !== store.activeJob?.Job"
          class="timer-warn"
        >
          Časovač běží pro jinou zakázku: {{ store.timer.job }} / Op {{ store.timer.operNum }}
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Play, Square, Wrench, Cog, Loader } from 'lucide-vue-next'
import { useWorkshopStore } from '@/stores/workshop'
import { useUiStore } from '@/stores/ui'
import Spinner from '@/components/ui/Spinner.vue'
import type { WorkshopOperation } from '@/types/workshop'

const ICON_SIZE_LG = 28

const store = useWorkshopStore()
const ui = useUiStore()

function isActiveOper(oper: WorkshopOperation) {
  return store.activeOperation?.OperNum === oper.OperNum
}

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

async function onStartTimer() {
  if (!store.activeJob || !store.activeOperation) return
  if (store.timer.running) {
    ui.showError('Časovač již běží. Nejdřív ho zastavte.')
    return
  }
  await store.startTimer(store.activeJob, store.activeOperation)
}

async function onStopTimer() {
  await store.stopTimer()
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

.oper-panel__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
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
}

.oper-panel__job-num {
  font-size: var(--fsh);
  font-weight: 700;
  color: var(--t1);
}

.oper-panel__job-item {
  font-size: var(--fs);
  color: var(--t2);
}

.oper-panel__job-desc {
  font-size: var(--fsm);
  color: var(--t3);
}

/* Operace */
.oper-panel__opers {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap);
  padding: var(--pad);
  flex-shrink: 0;
}

/* Velká touch tlačítka pro operace */
.oper-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 100px;
  min-height: 80px;
  padding: 12px;
  background: var(--surface);
  border: 2px solid var(--b2);
  border-radius: var(--r);
  cursor: pointer;
  transition: background 120ms var(--ease), border-color 120ms var(--ease);
  font-family: var(--font);
}

.oper-btn:hover {
  background: var(--raised);
  border-color: var(--b3);
}

.oper-btn--active {
  background: var(--raised);
  border-color: var(--red);
}

.oper-btn:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.5);
  outline-offset: 2px;
}

.oper-btn__num {
  font-size: var(--fsh);
  font-weight: 700;
  color: var(--t1);
}

.oper-btn__wc {
  font-size: var(--fsm);
  color: var(--t3);
}

.oper-btn__qty {
  font-size: var(--fss);
  color: var(--t3);
}

.oper-btn__hrs {
  font-size: var(--fss);
  color: var(--warn);
}

/* Materiály */
.oper-panel__materials {
  padding: var(--pad);
  border-top: 1px solid var(--b2);
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
  border-top: 1px solid var(--b2);
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

/* Velká tlačítka pro START/STOP */
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

.timer-btn__spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
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
