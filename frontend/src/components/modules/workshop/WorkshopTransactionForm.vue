<template>
  <div class="tx-form" data-testid="workshop-transaction-form">
    <!-- Žádná operace vybrána -->
    <div v-if="!store.activeOperation" class="tx-form__empty">
      <span>Vyberte operaci</span>
    </div>

    <template v-else>
      <!-- Kontextový header -->
      <div class="tx-form__header">
        <span class="tx-form__job">{{ store.activeJob?.Job }} / Op {{ store.activeOperation.OperNum }}</span>
        <span class="tx-form__wc">{{ store.activeOperation.Wc }}</span>
      </div>

      <!-- Setup mód — info o plánovaném seřízení -->
      <div v-if="store.workMode === 'setup'" class="tx-form__mode-info" data-testid="setup-mode-info">
        <span class="tx-form__mode-badge">SEŘÍZENÍ</span>
        <span v-if="store.activeOperation.SetupHrs" class="tx-form__mode-hrs">
          Plán: {{ store.activeOperation.SetupHrs }} hod
        </span>
        <span v-else class="tx-form__mode-hint">Zaznamenejte čas seřízení</span>
      </div>

      <!-- Šablony odvodu -->
      <div class="tx-form__templates">
        <button
          v-for="tpl in templates"
          :key="tpl.type"
          class="tpl-btn"
          :class="{ 'tpl-btn--active': activeTemplate === tpl.type }"
          :data-testid="`tpl-btn-${tpl.type}`"
          @click="selectTemplate(tpl.type)"
        >
          <component :is="tpl.icon" :size="ICON_SIZE" />
          <span>{{ tpl.label }}</span>
        </button>
      </div>

      <!-- Formulář dle šablony -->
      <div v-if="activeTemplate" class="tx-form__fields">
        <!-- Odvod kusů -->
        <template v-if="activeTemplate === 'qty_complete'">
          <Input
            :model-value="form.qty_completed != null ? String(form.qty_completed) : null"
            type="number"
            label="Hotové kusy"
            placeholder="0"
            :min="0"
            :step="1"
            testid="input-qty-completed"
            class="tx-form__input-wrap tx-form__input-wrap--large"
            @update:model-value="form.qty_completed = $event != null ? Number($event) : null"
          />
          <Input
            :model-value="form.qty_moved != null ? String(form.qty_moved) : null"
            type="number"
            label="Přesunuto na sklad"
            placeholder="0"
            :min="0"
            :step="1"
            testid="input-qty-moved"
            @update:model-value="form.qty_moved = $event != null ? Number($event) : null"
          />
          <!-- Příznaky dokončení -->
          <div class="tx-form__flags">
            <label class="flag-check" data-testid="flag-oper-complete">
              <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
              <input
                v-model="form.oper_complete"
                type="checkbox"
                class="flag-check__input"
              />
              <span class="flag-check__label">Operace dokončena</span>
            </label>
            <label class="flag-check" data-testid="flag-job-complete">
              <!-- eslint-disable-next-line vue/no-restricted-html-elements -->
              <input
                v-model="form.job_complete"
                type="checkbox"
                class="flag-check__input"
              />
              <span class="flag-check__label">VP dokončeno</span>
            </label>
          </div>
        </template>

        <!-- Zmetek -->
        <template v-if="activeTemplate === 'scrap'">
          <Input
            :model-value="form.qty_scrapped != null ? String(form.qty_scrapped) : null"
            type="number"
            label="Zmetky"
            placeholder="0"
            :min="0"
            :step="1"
            testid="input-qty-scrapped"
            class="tx-form__input-wrap tx-form__input-wrap--large"
            @update:model-value="form.qty_scrapped = $event != null ? Number($event) : null"
          />
          <Input
            :model-value="form.scrap_reason"
            type="text"
            label="Kód důvodu"
            placeholder="Kód z Inforu…"
            testid="input-scrap-reason"
            @update:model-value="form.scrap_reason = $event != null ? String($event) : null"
          />
        </template>

        <!-- Ruční zadání času -->
        <template v-if="activeTemplate === 'time'">
          <Input
            :model-value="form.actual_hours != null ? String(form.actual_hours) : null"
            type="number"
            label="Hodiny"
            placeholder="0.00"
            :min="0"
            :step="0.25"
            testid="input-actual-hours"
            class="tx-form__input-wrap tx-form__input-wrap--large"
            @update:model-value="form.actual_hours = $event != null ? Number($event) : null"
          />
        </template>

        <!-- Odeslat tlačítko -->
        <button
          class="tx-form__submit btn-primary"
          :disabled="submitting || !isFormValid"
          data-testid="tx-form-submit"
          @click="submitTransaction"
        >
          <span v-if="submitting">Ukládám…</span>
          <span v-else>Zapsat &amp; odeslat do Inforu</span>
        </button>
      </div>

      <!-- Poslední transakce -->
      <div v-if="recentTxs.length > 0" class="tx-form__recent">
        <div class="tx-form__recent-header">Poslední transakce</div>
        <div
          v-for="tx in recentTxs"
          :key="tx.id"
          class="tx-row"
          :data-testid="`tx-row-${tx.id}`"
        >
          <span class="tx-row__type">{{ txTypeLabel(tx.trans_type) }}</span>
          <span class="tx-row__value">{{ txValueLabel(tx) }}</span>
          <span class="tx-row__status" :class="`tx-row__status--${tx.status}`">
            {{ statusLabel(tx.status) }}
          </span>
          <span v-if="tx.error_msg" class="tx-row__err" :title="tx.error_msg">!</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { CheckSquare, Trash2, Clock } from 'lucide-vue-next'
import { useWorkshopStore } from '@/stores/workshop'
import Input from '@/components/ui/Input.vue'
import { ICON_SIZE } from '@/config/design'
import type { WorkshopTransType, WorkshopTxStatus, WorkshopTransaction } from '@/types/workshop'

const store = useWorkshopStore()

type TemplateType = Extract<WorkshopTransType, 'qty_complete' | 'scrap' | 'time'>

// V seřízení módu nabízíme jen čas, ve výrobním módu všechny typy
const allTemplates: { type: TemplateType; label: string; icon: typeof CheckSquare }[] = [
  { type: 'qty_complete', label: 'Odvod kusů', icon: CheckSquare },
  { type: 'scrap', label: 'Zmetek', icon: Trash2 },
  { type: 'time', label: 'Čas', icon: Clock },
]

const templates = computed(() =>
  store.workMode === 'setup'
    ? allTemplates.filter((t) => t.type === 'time')
    : allTemplates,
)

const activeTemplate = ref<TemplateType | null>(null)
const submitting = ref(false)

const form = ref({
  qty_completed: null as number | null,
  qty_scrapped: null as number | null,
  qty_moved: null as number | null,
  scrap_reason: null as string | null,
  actual_hours: null as number | null,
  oper_complete: false,
  job_complete: false,
})

// Reset formuláře při změně šablony
watch(activeTemplate, () => {
  form.value = {
    qty_completed: null,
    qty_scrapped: null,
    qty_moved: null,
    scrap_reason: null,
    actual_hours: null,
    oper_complete: false,
    job_complete: false,
  }
})

function selectTemplate(type: TemplateType) {
  activeTemplate.value = activeTemplate.value === type ? null : type
}

const isFormValid = computed(() => {
  if (!activeTemplate.value) return false
  if (activeTemplate.value === 'qty_complete') return (form.value.qty_completed ?? 0) > 0
  if (activeTemplate.value === 'scrap') return (form.value.qty_scrapped ?? 0) > 0
  if (activeTemplate.value === 'time') return (form.value.actual_hours ?? 0) > 0
  return false
})

const recentTxs = computed(() => store.transactions.slice(0, 5))

async function submitTransaction() {
  if (!store.activeJob || !store.activeOperation || !activeTemplate.value) return

  submitting.value = true
  try {
    const tx = await store.createTransaction({
      infor_job: store.activeJob.Job,
      infor_suffix: store.activeJob.Suffix ?? '0',
      oper_num: store.activeOperation.OperNum,
      wc: store.activeOperation.Wc,
      trans_type: activeTemplate.value,
      qty_completed: form.value.qty_completed,
      qty_scrapped: form.value.qty_scrapped,
      qty_moved: form.value.qty_moved,
      scrap_reason: form.value.scrap_reason,
      actual_hours: form.value.actual_hours,
      oper_complete: form.value.oper_complete,
      job_complete: form.value.job_complete,
    })

    if (!tx) return

    // Odešli okamžitě do Inforu
    await store.postTransaction(tx.id)

    // Reset
    form.value = {
      qty_completed: null,
      qty_scrapped: null,
      qty_moved: null,
      scrap_reason: null,
      actual_hours: null,
      oper_complete: false,
      job_complete: false,
    }
    activeTemplate.value = null
  } finally {
    submitting.value = false
  }
}

function txTypeLabel(type: WorkshopTransType): string {
  const map: Record<WorkshopTransType, string> = {
    qty_complete: 'Odvod',
    scrap: 'Zmetek',
    time: 'Čas',
    start: 'Start výroby',
    stop: 'Stop výroby',
    setup_start: 'Start seřízení',
    setup_end: 'Konec seřízení',
  }
  return map[type] ?? type
}

function txValueLabel(tx: WorkshopTransaction): string {
  if (tx.trans_type === 'qty_complete') return `${tx.qty_completed ?? 0} ks`
  if (tx.trans_type === 'scrap') return `${tx.qty_scrapped ?? 0} ks`
  if (tx.trans_type === 'time') return `${tx.actual_hours ?? 0} hod`
  if (tx.trans_type === 'stop') return `${tx.actual_hours?.toFixed(2) ?? '?'} hod`
  return ''
}

function statusLabel(status: WorkshopTxStatus): string {
  const map: Record<WorkshopTxStatus, string> = {
    pending: 'Čeká',
    posting: 'Odesílá…',
    posted: 'Odesláno',
    failed: 'Chyba',
  }
  return map[status] ?? status
}
</script>

<style scoped>
.tx-form {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
}

.tx-form__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--t3);
  font-size: var(--fs);
}

/* Header kontextu */
.tx-form__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px var(--pad);
  border-bottom: 1px solid var(--b2);
  flex-shrink: 0;
}

.tx-form__job {
  font-size: var(--fsh);
  font-weight: 700;
  color: var(--t1);
}

.tx-form__wc {
  font-size: var(--fsm);
  color: var(--t3);
  background: var(--ground);
  padding: 2px 8px;
  border-radius: var(--rs);
}

/* Setup mód info */
.tx-form__mode-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px var(--pad);
  background: var(--ground);
  border-bottom: 1px solid var(--b2);
  flex-shrink: 0;
}

.tx-form__mode-badge {
  font-size: var(--fss);
  font-weight: 700;
  color: var(--warn);
  background: var(--ground);
  border: 1px solid var(--warn);
  padding: 1px 6px;
  border-radius: var(--rs);
  letter-spacing: 0.5px;
}

.tx-form__mode-hrs {
  font-size: var(--fsm);
  color: var(--t2);
}

.tx-form__mode-hint {
  font-size: var(--fsm);
  color: var(--t3);
}

/* Šablony */
.tx-form__templates {
  display: flex;
  gap: var(--gap);
  padding: var(--pad);
  border-bottom: 1px solid var(--b2);
  flex-shrink: 0;
}

/* Velká tlačítka šablon pro iPad touch */
.tpl-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex: 1;
  min-height: 72px;
  background: var(--surface);
  border: 2px solid var(--b2);
  border-radius: var(--r);
  cursor: pointer;
  font-family: var(--font);
  font-size: var(--fsm);
  font-weight: 500;
  color: var(--t2);
  transition: background 120ms var(--ease), border-color 120ms var(--ease), color 120ms var(--ease);
}

.tpl-btn:hover {
  background: var(--raised);
  border-color: var(--b3);
  color: var(--t1);
}

.tpl-btn--active {
  background: var(--raised);
  border-color: var(--red);
  color: var(--t1);
}

.tpl-btn:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.5);
  outline-offset: 2px;
}

/* Formulářová pole */
.tx-form__fields {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: var(--pad);
  flex-shrink: 0;
}

/* Velký input wrapper pro iPad touch — override Input.vue výšky */
.tx-form__input-wrap--large :deep(.input-ctrl) {
  min-height: 60px;
  font-size: 28px;
  font-weight: 700;
  text-align: center;
  padding: 12px;
}

/* Příznaky dokončení */
.tx-form__flags {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.flag-check {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--ground);
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

/* Odeslat tlačítko */
.tx-form__submit {
  min-height: 56px;
  font-size: var(--fsh);
  font-weight: 600;
}

.tx-form__submit:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Poslední transakce */
.tx-form__recent {
  border-top: 1px solid var(--b2);
  padding: var(--pad);
  flex-shrink: 0;
}

.tx-form__recent-header {
  font-size: var(--fsm);
  font-weight: 500;
  color: var(--t3);
  margin-bottom: var(--gap);
}

.tx-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--b1);
  font-size: var(--fsm);
}

.tx-row:last-child {
  border-bottom: none;
}

.tx-row__type {
  color: var(--t2);
  min-width: 60px;
}

.tx-row__value {
  color: var(--t1);
  flex: 1;
  font-weight: 500;
}

.tx-row__status {
  font-size: var(--fss);
  padding: 2px 6px;
  border-radius: var(--rs);
  font-weight: 500;
}

.tx-row__status--pending {
  color: var(--t3);
  background: var(--ground);
}

.tx-row__status--posting {
  color: var(--warn);
  background: var(--ground);
}

.tx-row__status--posted {
  color: var(--ok);
  background: var(--green-10);
}

.tx-row__status--failed {
  color: var(--err);
  background: var(--red-10);
}

.tx-row__err {
  color: var(--err);
  font-weight: 700;
  font-size: var(--fsh);
  cursor: help;
}
</style>
