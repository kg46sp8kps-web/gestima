<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePartnersStore } from '@/stores/partners'
import type { ContextGroup } from '@/types/workspace'
import Spinner from '@/components/ui/Spinner.vue'
import Input from '@/components/ui/Input.vue'

interface Props {
  leafId: string
  ctx: ContextGroup
}

defineProps<Props>()

const store = usePartnersStore()
const searchQuery = ref('')

const filtered = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return store.items
  return store.items.filter(p =>
    p.company_name.toLowerCase().includes(q) ||
    p.partner_number.includes(q) ||
    (p.ico ?? '').includes(q) ||
    (p.email ?? '').toLowerCase().includes(q) ||
    (p.city ?? '').toLowerCase().includes(q),
  )
})

onMounted(() => store.fetchIfNeeded())
</script>

<template>
  <div class="wpar">
    <!-- Loading -->
    <div v-if="store.loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>

    <!-- Data (incl. empty) -->
    <template v-else>
      <!-- Search toolbar -->
      <div class="srch-bar">
        <Input
          v-model="searchQuery"
          bare
          type="text"
          placeholder="Hledat partnera…"
          testid="partner-search-input"
          class="srch-inp"
        />
        <span class="srch-count">{{ filtered.length }} / {{ store.items.length }}</span>
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
              <td class="t4">{{ p.partner_number }}</td>
              <td>
                <div class="firm-name">{{ p.company_name }}</div>
                <div v-if="p.email" class="firm-sub t4">{{ p.email }}</div>
              </td>
              <td class="t4">{{ p.city ?? '—' }}</td>
              <td class="t4">{{ p.ico ?? '—' }}</td>
              <td class="type-cell">
                <span v-if="p.is_customer" class="badge" title="Zákazník">
                  <span class="badge-dot badge-dot-ok" />Z
                </span>
                <span v-if="p.is_supplier" class="badge" title="Dodavatel">
                  <span class="badge-dot badge-dot-neutral" />D
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

.mod-label { font-size: var(--fsm); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }

/* ─── Search bar ─── */
.srch-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px var(--pad);
  border-bottom: 1px solid var(--b1);
  flex-shrink: 0;
}
/* .srch-inp layout: visual styles come from Input component's .input-ctrl */
.srch-inp { flex: 1; }
.srch-count {
  font-size: var(--fsm);
  color: var(--t4);
  white-space: nowrap;
}

/* ─── Table wrapper ─── */
.ot-wrap {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}

/* ─── Table ─── */

.t4 { color: var(--t4); }

.firm-name { font-weight: 500; color: var(--t1); }
.firm-sub { font-size: var(--fsm); margin-top: 1px; }

/* Type badges use global .badge + .badge-dot-* from design-system.css */
.type-cell { display: flex; gap: 3px; }
</style>
