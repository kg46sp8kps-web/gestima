<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as batchSetsApi from '@/api/batch-sets'
import type { BatchSet } from '@/types/batch-set'
import type { ContextGroup } from '@/types/workspace'
import Spinner from '@/components/ui/Spinner.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

defineProps<Props>()

const items = ref<BatchSet[]>([])
const loading = ref(false)
const error = ref(false)
const statusFilter = ref<'all' | 'draft' | 'frozen'>('all')

const filtered = computed(() => {
  if (statusFilter.value === 'all') return items.value
  return items.value.filter(s => s.status === statusFilter.value)
})

async function load() {
  loading.value = true
  error.value = false
  try {
    items.value = await batchSetsApi.getAll()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="wbs">
    <!-- Loading -->
    <div v-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>

    <!-- Data -->
    <template v-else>
      <!-- Toolbar -->
      <div class="srch-bar">
        <div class="flt-grp">
          <button
            :class="['ptab', statusFilter === 'all' ? 'on' : '']"
            data-testid="filter-all"
            @click="statusFilter = 'all'"
          >Vše</button>
          <button
            :class="['ptab', statusFilter === 'draft' ? 'on' : '']"
            data-testid="filter-draft"
            @click="statusFilter = 'draft'"
          >Draft</button>
          <button
            :class="['ptab', statusFilter === 'frozen' ? 'on' : '']"
            data-testid="filter-frozen"
            @click="statusFilter = 'frozen'"
          >Zmrazené</button>
        </div>
        <span class="srch-count">{{ filtered.length }} / {{ items.length }}</span>
      </div>

      <!-- Empty -->
      <div v-if="!filtered.length" class="mod-placeholder">
        <div class="mod-dot" />
        <span class="mod-label">{{ statusFilter !== 'all' ? 'Žádné výsledky' : 'Žádné dávkové sady' }}</span>
      </div>

      <!-- Table -->
      <div v-else class="ot-wrap">
        <table class="ot">
          <thead>
            <tr>
              <th style="width:82px">Číslo</th>
              <th>Název</th>
              <th style="width:58px">Dávek</th>
              <th style="width:60px">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="s in filtered"
              :key="s.id"
              :data-testid="`batch-set-row-${s.id}`"
            >
              <td class="t4">{{ s.set_number }}</td>
              <td>
                <div class="set-name">{{ s.name }}</div>
                <div v-if="s.part_id" class="set-sub t4">Díl #{{ s.part_id }}</div>
              </td>
              <td class="t4 r">{{ s.batch_count }}</td>
              <td>
                <span v-if="s.status === 'frozen'" class="badge frozen">
                  <span class="badge-dot neutral" />
                  Zmraz.
                </span>
                <span v-else class="badge draft">
                  <span class="badge-dot ok" />
                  Draft
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wbs {
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

.srch-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.flt-grp { display: flex; gap: 2px; }
.ptab { padding: 3px 7px; font-size: var(--fsx); font-weight: 500; color: var(--t4); background: transparent; border: none; border-radius: var(--rs); cursor: pointer; font-family: var(--font); }
.ptab:hover { color: var(--t3); }
.ptab.on { color: var(--t1); background: var(--b1); }
.srch-count {
  margin-left: auto;
  font-size: var(--fsm);
  color: var(--t4);
  white-space: nowrap;
}

.ot-wrap {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

.t4 { color: var(--t4); }

.set-name { font-weight: 500; color: var(--t1); }
.set-sub { font-size: var(--fsm); margin-top: 1px; }

.badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 5px;
  font-size: var(--fsm);
  font-weight: 500;
  border-radius: 99px;
  background: var(--b1);
  color: var(--t2);
}
.badge-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  flex-shrink: 0;
}
.badge-dot.ok { background: var(--ok); }
.badge-dot.neutral { background: var(--t4); }
</style>
