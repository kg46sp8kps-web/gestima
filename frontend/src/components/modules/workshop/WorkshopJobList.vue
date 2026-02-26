<template>
  <div class="job-list" data-testid="workshop-job-list">
    <!-- Filtr pracoviště -->
    <div class="job-list__filter">
      <Input
        v-model="filterWc"
        bare
        type="text"
        placeholder="Filtr pracoviště (WC)…"
        testid="job-list-wc-filter"
        class="job-list__filter-input"
      />
      <button
        class="btn-secondary job-list__refresh"
        :disabled="store.loadingJobs"
        data-testid="job-list-refresh"
        @click="refresh"
      >
        <RefreshCw :size="ICON_SIZE" />
      </button>
    </div>

    <!-- Loading -->
    <div v-if="store.loadingJobs" class="job-list__empty">
      <Spinner text="Načítám zakázky…" />
    </div>

    <!-- Empty -->
    <div v-else-if="store.filteredJobs.length === 0" class="job-list__empty">
      <span>Žádné otevřené zakázky</span>
    </div>

    <!-- Seznam zakázek -->
    <div v-else class="job-list__items" role="list">
      <button
        v-for="job in store.filteredJobs"
        :key="`${job.Job}-${job.Suffix}`"
        class="job-row"
        :class="{ 'job-row--active': isActive(job) }"
        role="listitem"
        :data-testid="`job-row-${job.Job}`"
        @click="selectJob(job)"
      >
        <div class="job-row__header">
          <span class="job-row__job">{{ job.Job }}<span v-if="job.Suffix && job.Suffix !== '0'">/{{ job.Suffix }}</span></span>
          <span class="job-row__wc">{{ job.Wc }}</span>
        </div>
        <div class="job-row__item">{{ job.DerJobItem }}</div>
        <div class="job-row__desc">{{ job.JobDescription }}</div>
        <div class="job-row__meta">
          <span>Op: {{ job.OperNum }}</span>
          <span v-if="job.JobQtyReleased != null">Ks: {{ Math.round(job.JobQtyReleased) }}</span>
          <span v-if="job.QtyComplete != null" class="job-row__done">✓ {{ Math.round(job.QtyComplete) }}</span>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import { useWorkshopStore } from '@/stores/workshop'
import Spinner from '@/components/ui/Spinner.vue'
import Input from '@/components/ui/Input.vue'
import { ICON_SIZE } from '@/config/design'
import type { WorkshopJob } from '@/types/workshop'

const store = useWorkshopStore()
const filterWc = ref<string | number | null>(store.wcFilter)

// Při změně WC filtru: debounce + server-side refetch (ne jen clientský filtr)
let _filterTimer: ReturnType<typeof setTimeout>
watch(filterWc, (newVal) => {
  clearTimeout(_filterTimer)
  _filterTimer = setTimeout(() => {
    const wc = newVal != null ? String(newVal).trim() : ''
    store.wcFilter = wc
    store.fetchJobs(wc || undefined)
  }, 400)
})

function isActive(job: WorkshopJob) {
  return store.activeJob?.Job === job.Job && store.activeJob?.Suffix === job.Suffix
}

function selectJob(job: WorkshopJob) {
  store.selectJob(job)
}


async function refresh() {
  const wc = filterWc.value != null ? String(filterWc.value).trim() : undefined
  await store.fetchJobs(wc || undefined)
}

onMounted(() => {
  if (store.jobs.length === 0) {
    store.fetchJobs()
  }
})
</script>

<style scoped>
.job-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.job-list__filter {
  display: flex;
  gap: var(--gap);
  padding: var(--pad);
  border-bottom: 1px solid var(--b2);
  flex-shrink: 0;
}

.job-list__filter-input {
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  padding: 10px 12px;
  color: var(--t1);
  font-family: var(--font);
  font-size: var(--fs);
  outline: none;
  min-height: 44px;
}

.job-list__filter-input:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.5);
  outline-offset: 1px;
}

.job-list__refresh {
  padding: 10px 12px;
  min-height: 44px;
  min-width: 44px;
}

.job-list__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--t3);
  font-size: var(--fs);
  padding: var(--pad);
}

.job-list__items {
  flex: 1;
  overflow-y: auto;
  padding: var(--gap);
}

/* Velké řádky pro iPad touch */
.job-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
  min-height: 72px;
  padding: 12px var(--pad);
  background: var(--surface);
  border: 1px solid var(--b2);
  border-radius: var(--r);
  margin-bottom: var(--gap);
  text-align: left;
  cursor: pointer;
  transition: background 120ms var(--ease), border-color 120ms var(--ease);
  color: var(--t1);
  font-family: var(--font);
}

.job-row:hover {
  background: var(--raised);
  border-color: var(--b3);
}

.job-row--active {
  background: var(--raised);
  border-color: var(--b3);
  box-shadow: inset 3px 0 0 var(--red);
}

.job-row:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.5);
  outline-offset: 2px;
}

.job-row__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.job-row__job {
  font-size: var(--fsh);
  font-weight: 600;
  color: var(--t1);
}

.job-row__wc {
  font-size: var(--fsm);
  font-weight: 500;
  color: var(--t3);
  background: var(--ground);
  padding: 2px 6px;
  border-radius: var(--rs);
}

.job-row__item {
  font-size: var(--fs);
  font-weight: 500;
  color: var(--t2);
}

.job-row__desc {
  font-size: var(--fsm);
  color: var(--t3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.job-row__meta {
  display: flex;
  gap: 12px;
  font-size: var(--fsm);
  color: var(--t3);
}

.job-row__done {
  color: var(--ok);
}
</style>
