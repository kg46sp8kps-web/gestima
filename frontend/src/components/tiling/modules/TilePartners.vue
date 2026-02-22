<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as partnersApi from '@/api/partners'
import type { Partner } from '@/types/partner'
import type { ContextGroup } from '@/types/workspace'
import Spinner from '@/components/ui/Spinner.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

defineProps<Props>()

const items = ref<Partner[]>([])
const loading = ref(false)
const error = ref(false)
const searchQuery = ref('')

const filtered = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return items.value
  return items.value.filter(p =>
    p.company_name.toLowerCase().includes(q) ||
    p.partner_number.includes(q) ||
    (p.ico ?? '').includes(q) ||
    (p.email ?? '').toLowerCase().includes(q) ||
    (p.city ?? '').toLowerCase().includes(q),
  )
})

async function load() {
  loading.value = true
  error.value = false
  try {
    items.value = await partnersApi.getAll()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="wpar">
    <!-- Loading -->
    <div v-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>

    <!-- Data (incl. empty) -->
    <template v-else>
      <!-- Search toolbar -->
      <div class="srch-bar">
        <input
          v-model="searchQuery"
          class="srch-inp"
          type="text"
          placeholder="Hledat partnera…"
          data-testid="partner-search-input"
        />
        <span class="srch-count">{{ filtered.length }} / {{ items.length }}</span>
      </div>

      <!-- Empty state -->
      <div v-if="!filtered.length" class="mod-placeholder">
        <div class="mod-dot" />
        <span class="mod-label">{{ searchQuery ? 'Žádné výsledky' : 'Žádní partneři' }}</span>
      </div>

      <!-- Table -->
      <div v-else class="ot-wrap">
        <table class="ot">
          <thead>
            <tr>
              <th style="width:82px">Číslo</th>
              <th>Firma</th>
              <th style="width:90px">Město</th>
              <th style="width:76px">IČO</th>
              <th style="width:30px">Typ</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="p in filtered"
              :key="p.id"
              :data-testid="`partner-row-${p.id}`"
            >
              <td class="mono t4">{{ p.partner_number }}</td>
              <td>
                <div class="firm-name">{{ p.company_name }}</div>
                <div v-if="p.email" class="firm-sub t4">{{ p.email }}</div>
              </td>
              <td class="t4">{{ p.city ?? '—' }}</td>
              <td class="mono t4">{{ p.ico ?? '—' }}</td>
              <td>
                <span v-if="p.is_customer" class="type-badge cust" title="Zákazník">Z</span>
                <span v-if="p.is_supplier" class="type-badge supp" title="Dodavatel">D</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wpar {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* ─── Placeholder ─── */
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

/* ─── Search bar ─── */
.srch-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
.srch-inp {
  flex: 1;
  background: var(--b1);
  border: 1px solid var(--b2);
  border-radius: var(--rs);
  color: var(--t1);
  font-size: var(--fs);
  padding: 3px 6px;
  outline: none;
}
.srch-inp::placeholder { color: var(--t4); }
.srch-inp:focus { border-color: var(--b3); }
.srch-count {
  font-size: 10px;
  color: var(--t4);
  white-space: nowrap;
  font-family: var(--mono);
}

/* ─── Table wrapper ─── */
.ot-wrap {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

/* ─── Table ─── */
.ot {
  width: 100%;
  border-collapse: collapse;
}
.ot thead {
  background: rgba(255,255,255,0.025);
  position: sticky;
  top: 0;
  z-index: 2;
}
.ot th {
  padding: 4px var(--pad);
  font-size: 10px;
  font-weight: 600;
  color: var(--t4);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  text-align: left;
  border-bottom: 1px solid var(--b2);
  white-space: nowrap;
}
.ot td {
  padding: 4px var(--pad);
  font-size: var(--fs);
  color: var(--t2);
  border-bottom: 1px solid rgba(255,255,255,0.025);
  vertical-align: middle;
}
.ot tbody tr:hover td { background: var(--b1); }
.mono { font-family: var(--mono); }
.t4 { color: var(--t4); }

.firm-name { font-weight: 500; color: var(--t1); }
.firm-sub { font-size: 10px; margin-top: 1px; }

/* ─── Type badges ─── */
.type-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: var(--rs);
  font-size: 9px;
  font-weight: 700;
  font-family: var(--mono);
  margin-right: 2px;
}
.type-badge.cust { background: var(--green-10); color: var(--green); }
.type-badge.supp { background: var(--b2); color: var(--t3); }
</style>
