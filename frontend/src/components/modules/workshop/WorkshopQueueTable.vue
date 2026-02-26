<template>
  <div class="queue-table" data-testid="workshop-queue-table">
    <!-- Filtr pracoviště + refresh -->
    <div class="queue-table__filter">
      <Input
        v-model="filterWc"
        bare
        type="text"
        placeholder="Filtr pracoviště (WC)…"
        testid="queue-wc-filter"
        class="queue-table__filter-input"
      />
      <button
        class="btn-secondary queue-table__refresh"
        :disabled="store.loadingQueue"
        data-testid="queue-refresh"
        @click="refresh"
      >
        <RefreshCw :size="ICON_SIZE" />
      </button>
    </div>

    <!-- Loading -->
    <div v-if="store.loadingQueue" class="queue-table__empty">
      <Spinner text="Načítám frontu…" />
    </div>

    <!-- Empty -->
    <div v-else-if="store.queueItems.length === 0" class="queue-table__empty">
      <span>Žádné operace ve frontě</span>
    </div>

    <!-- Tabulka operací -->
    <div v-else class="queue-table__body">
      <table class="qt">
        <thead class="qt__head">
          <tr>
            <th class="qt__th">VP / Op</th>
            <th class="qt__th qt__th--wc">WC</th>
            <th class="qt__th">Díl</th>
            <th class="qt__th qt__th--desc">Popis</th>
            <th class="qt__th qt__th--num">Ks</th>
            <th class="qt__th qt__th--date">Plán od</th>
            <th class="qt__th qt__th--date">Plán do</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in store.queueItems"
            :key="`${item.Job}-${item.Suffix}-${item.OperNum}`"
            class="qt__row"
            :class="{ 'qt__row--active': isActive(item) }"
            :data-testid="`queue-row-${item.Job}-${item.OperNum}`"
            @click="store.selectQueueItem(item)"
          >
            <td class="qt__td">
              <span class="qt__job">{{ item.Job }}<span v-if="item.Suffix && item.Suffix !== '0'">/{{ item.Suffix }}</span></span>
              <span class="qt__oper">Op {{ item.OperNum }}</span>
            </td>
            <td class="qt__td qt__td--wc">{{ item.Wc }}</td>
            <td class="qt__td">{{ item.DerJobItem ?? '—' }}</td>
            <td class="qt__td qt__td--desc">{{ item.JobDescription ?? '—' }}</td>
            <td class="qt__td qt__td--num">
              <span>{{ item.QtyComplete != null ? Math.round(item.QtyComplete) : '?' }}</span>
              <span class="qt__qty-sep">/</span>
              <span>{{ item.JobQtyReleased != null ? Math.round(item.JobQtyReleased) : '?' }}</span>
            </td>
            <td class="qt__td qt__td--date">{{ formatInforDate(item.OpDatumSt) }}</td>
            <td class="qt__td qt__td--date">{{ formatInforDate(item.OpDatumSp) }}</td>
          </tr>
        </tbody>
      </table>
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
import type { WorkshopQueueItem } from '@/types/workshop'

const store = useWorkshopStore()
const filterWc = ref<string | number | null>(store.wcFilter)

// Debounce + server-side refetch při změně WC filtru
let _filterTimer: ReturnType<typeof setTimeout>
watch(filterWc, (newVal) => {
  clearTimeout(_filterTimer)
  _filterTimer = setTimeout(() => {
    const wc = newVal != null ? String(newVal).trim() : ''
    store.wcFilter = wc
    store.fetchQueue(wc || undefined)
  }, 400)
})

function isActive(item: WorkshopQueueItem) {
  return (
    store.activeQueueItem?.Job === item.Job &&
    store.activeQueueItem?.Suffix === item.Suffix &&
    store.activeQueueItem?.OperNum === item.OperNum
  )
}

async function refresh() {
  const wc = filterWc.value != null ? String(filterWc.value).trim() : undefined
  await store.fetchQueue(wc || undefined)
}

/** Formátuje datum z Infor (ISO string) na čitelný CZ formát "DD.MM. HH:MM" */
function formatInforDate(value: string | null | undefined): string {
  if (!value) return '—'
  try {
    const d = new Date(value)
    if (isNaN(d.getTime())) return '—'
    const day = d.getDate().toString().padStart(2, '0')
    const mon = (d.getMonth() + 1).toString().padStart(2, '0')
    const hh = d.getHours().toString().padStart(2, '0')
    const mm = d.getMinutes().toString().padStart(2, '0')
    return `${day}.${mon}. ${hh}:${mm}`
  } catch {
    return '—'
  }
}

onMounted(() => {
  if (store.queueItems.length === 0) {
    store.fetchQueue()
  }
})
</script>

<style scoped>
.queue-table {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* Filtr + refresh */
.queue-table__filter {
  display: flex;
  gap: var(--gap);
  padding: var(--pad);
  border-bottom: 1px solid var(--b2);
  flex-shrink: 0;
}

.queue-table__filter-input {
  flex: 1;
}

.queue-table__refresh {
  padding: 10px 12px;
  min-height: 44px;
  min-width: 44px;
}

/* Empty / loading */
.queue-table__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--t3);
  font-size: var(--fs);
  padding: var(--pad);
}

/* Tabulka */
.queue-table__body {
  flex: 1;
  overflow-y: auto;
  overflow-x: auto;
}

.qt {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font);
}

.qt__head {
  position: sticky;
  top: 0;
  background: var(--ground);
  z-index: 1;
}

.qt__th {
  padding: 8px var(--pad);
  font-size: var(--fss);
  font-weight: 600;
  color: var(--t3);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  text-align: left;
  border-bottom: 1px solid var(--b2);
  white-space: nowrap;
}

.qt__th--num {
  text-align: right;
}

.qt__th--date {
  min-width: 90px;
}

.qt__th--desc {
  min-width: 120px;
}

.qt__th--wc {
  min-width: 60px;
}

/* Řádky — velké touch cíle pro iPad */
.qt__row {
  cursor: pointer;
  transition: background 120ms var(--ease);
  border-bottom: 1px solid var(--b1);
}

.qt__row:hover {
  background: var(--surface);
}

.qt__row--active {
  background: var(--raised);
  box-shadow: inset 3px 0 0 var(--red);
}

.qt__row:focus-visible {
  outline: 2px solid rgba(255, 255, 255, 0.5);
  outline-offset: -2px;
}

.qt__td {
  padding: 12px var(--pad);
  font-size: var(--fsm);
  color: var(--t2);
  vertical-align: middle;
}

.qt__td--desc {
  color: var(--t3);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.qt__td--wc {
  font-size: var(--fss);
  color: var(--t3);
}

.qt__td--num {
  text-align: right;
  white-space: nowrap;
  color: var(--t1);
  font-weight: 500;
}

.qt__td--date {
  white-space: nowrap;
  font-size: var(--fss);
  color: var(--t3);
}

.qt__job {
  font-size: var(--fs);
  font-weight: 600;
  color: var(--t1);
  display: block;
}

.qt__oper {
  font-size: var(--fss);
  color: var(--t3);
  display: block;
  margin-top: 2px;
}

.qt__qty-sep {
  color: var(--t4);
  margin: 0 2px;
}
</style>
