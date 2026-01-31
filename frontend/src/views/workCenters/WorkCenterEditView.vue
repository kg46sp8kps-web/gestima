<script setup lang="ts">
/**
 * Work Center Edit/Create View
 * Editace nebo vytvoření nového pracoviště
 */

import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useOperationsStore } from '@/stores/operations'
import { useUiStore } from '@/stores/ui'
import type { WorkCenterType } from '@/types/operation'
import Input from '@/components/ui/Input.vue'

const route = useRoute()
const router = useRouter()
const operationsStore = useOperationsStore()
const uiStore = useUiStore()

// Mode detection
const isCreateMode = computed(() => !route.params.workCenterNumber)

// Form state
const form = ref({
  name: '',
  work_center_type: 'CNC_LATHE' as WorkCenterType,
  hourly_rate_amortization: 0,
  hourly_rate_labor: 0,
  hourly_rate_tools: 0,
  hourly_rate_overhead: 0,
  is_active: true,
  priority: 100,
  version: 0
})

const saving = ref(false)

// Computed
const hourlyRate = computed(() => {
  return (
    form.value.hourly_rate_amortization +
    form.value.hourly_rate_labor +
    form.value.hourly_rate_tools +
    form.value.hourly_rate_overhead
  )
})

// Methods
async function loadWorkCenter() {
  if (isCreateMode.value) return

  // Ensure workCenters are loaded
  if (operationsStore.workCenters.length === 0) {
    await operationsStore.loadWorkCenters()
  }

  const wcNumber = route.params.workCenterNumber as string
  const wc = operationsStore.workCenters.find(
    w => w.work_center_number === wcNumber
  )

  if (!wc) {
    console.error('WorkCenter not found:', wcNumber)
    uiStore.showError(`Pracoviště ${wcNumber} nenalezeno`)
    router.push({ name: 'work-centers-list' })
    return
  }

  // Populate form with work center data (backend returns 4 individual rates)
  form.value = {
    name: wc.name,
    work_center_type: wc.work_center_type,
    hourly_rate_amortization: wc.hourly_rate_amortization ?? 0,
    hourly_rate_labor: wc.hourly_rate_labor ?? 0,
    hourly_rate_tools: wc.hourly_rate_tools ?? 0,
    hourly_rate_overhead: wc.hourly_rate_overhead ?? 0,
    is_active: wc.is_active,
    priority: wc.priority,
    version: wc.version
  }
}

async function handleSave() {
  saving.value = true
  try {
    if (isCreateMode.value) {
      // Exclude version and priority for create
      const { version, priority, ...createData } = form.value
      await operationsStore.createWorkCenter(createData)
      uiStore.showSuccess('Pracoviště vytvořeno')
    } else {
      const wcNumber = route.params.workCenterNumber as string
      const wc = operationsStore.workCenters.find(
        w => w.work_center_number === wcNumber
      )
      if (wc) {
        // Include version for optimistic locking
        const updateData = {
          ...form.value,
          version: wc.version
        }
        await operationsStore.updateWorkCenter(wcNumber, updateData)
        uiStore.showSuccess('Pracoviště uloženo')
      }
    }
    router.push({ name: 'work-centers-list' })
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Chyba při ukládání'
    uiStore.showError(message)
  } finally {
    saving.value = false
  }
}

function goBack() {
  router.push({ name: 'work-centers-list' })
}

onMounted(() => {
  loadWorkCenter()
})
</script>

<template>
  <div class="work-center-edit-view">
    <header class="page-header">
      <button class="btn-back" @click="goBack">← Zpět</button>
      <div class="header-content">
        <h1 class="page-title">
          {{ isCreateMode ? 'Nové pracoviště' : `Úprava: ${form.name}` }}
        </h1>
      </div>
    </header>

    <div class="page-content">
      <form class="edit-form" @submit.prevent="handleSave">
        <div class="form-card">
          <h2 class="card-title">Základní údaje</h2>

          <div class="form-group">
            <label>Název *</label>
            <input v-model="form.name" required maxlength="200" />
          </div>

          <div class="form-group">
            <label>Typ *</label>
            <select v-model="form.work_center_type" required>
              <optgroup label="CNC Soustruhy">
                <option value="CNC_LATHE">CNC Soustruh</option>
              </optgroup>
              <optgroup label="CNC Frézky">
                <option value="CNC_MILL_3AX">CNC Frézka 3-osá</option>
                <option value="CNC_MILL_4AX">CNC Frézka 4-osá</option>
                <option value="CNC_MILL_5AX">CNC Frézka 5-osá</option>
              </optgroup>
              <optgroup label="Ostatní stroje">
                <option value="SAW">Pila</option>
                <option value="DRILL">Vrtačka</option>
              </optgroup>
              <optgroup label="Virtuální pracoviště">
                <option value="QUALITY_CONTROL">Kontrola</option>
                <option value="MANUAL_ASSEMBLY">Mechanik/Montáž</option>
                <option value="EXTERNAL">Externí kooperace</option>
              </optgroup>
            </select>
          </div>

          <div class="form-group">
            <label>
              <input v-model="form.is_active" type="checkbox" />
              Aktivní
            </label>
          </div>
        </div>

        <div class="form-card">
          <h2 class="card-title">Hodinové sazby (Kč/h)</h2>

          <div class="form-group">
            <Input v-model="form.hourly_rate_amortization" type="number" label="Amortizace" />
          </div>

          <div class="form-group">
            <Input v-model="form.hourly_rate_labor" type="number" label="Mzdy" />
          </div>

          <div class="form-group">
            <Input v-model="form.hourly_rate_tools" type="number" label="Nástroje" />
          </div>

          <div class="form-group">
            <Input v-model="form.hourly_rate_overhead" type="number" label="Režie" />
          </div>

          <div class="total-rate">
            <strong>Celková sazba:</strong>
            <span>{{ hourlyRate.toFixed(2) }} Kč/h</span>
          </div>
        </div>

        <div class="form-actions">
          <button type="button" class="btn btn-secondary" @click="goBack">
            Zrušit
          </button>
          <button type="submit" class="btn btn-primary" :disabled="saving">
            {{ saving ? 'Ukládám...' : 'Uložit' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.work-center-edit-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-default);
}

.page-header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-6);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
}

.btn-back {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  cursor: pointer;
}

.btn-back:hover {
  background: var(--state-hover);
}

.page-title {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
}

.page-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
}

.edit-form {
  max-width: 600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.form-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.card-title {
  margin: 0 0 var(--space-5);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}

.form-group {
  margin-bottom: var(--space-4);
}

.form-group label {
  display: block;
  margin-bottom: var(--space-2);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.form-group input,
.form-group select {
  width: 100%;
  padding: var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
}

.total-rate {
  display: flex;
  justify-content: space-between;
  padding-top: var(--space-4);
  border-top: 2px solid var(--border-default);
  font-size: var(--text-lg);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

</style>
