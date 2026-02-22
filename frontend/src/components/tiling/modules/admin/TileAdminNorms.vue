<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as adminApi from '@/api/admin'
import type { MaterialNorm } from '@/types/admin-user'
import Spinner from '@/components/ui/Spinner.vue'

const norms = ref<MaterialNorm[]>([])
const loading = ref(false)
const error = ref(false)
const search = ref('')

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return norms.value
  return norms.value.filter(n =>
    (n.w_nr ?? '').toLowerCase().includes(q) ||
    (n.en_iso ?? '').toLowerCase().includes(q) ||
    (n.csn ?? '').toLowerCase().includes(q) ||
    (n.material_group?.name ?? '').toLowerCase().includes(q),
  )
})

async function load() {
  loading.value = true
  error.value = false
  try {
    norms.value = await adminApi.getMaterialNorms()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="tab-content">
    <div class="srch-bar">
      <input
        v-model="search"
        class="srch-inp"
        type="text"
        placeholder="Hledat normu…"
        data-testid="norms-search-input"
      />
      <span class="srch-count">{{ filtered.length }} / {{ norms.length }}</span>
    </div>

    <div v-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>
    <div v-else-if="!filtered.length" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">{{ search ? 'Žádné výsledky' : 'Žádné normy' }}</span>
    </div>
    <div v-else class="ot-wrap">
      <table class="ot">
        <thead>
          <tr>
            <th style="width:70px">W.Nr</th>
            <th style="width:80px">EN/ISO</th>
            <th style="width:80px">ČSN</th>
            <th style="width:60px">AISI</th>
            <th>Skupina</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="n in filtered"
            :key="n.id"
            :data-testid="`norm-row-${n.id}`"
          >
            <td class="mono">{{ n.w_nr ?? '—' }}</td>
            <td class="mono t3">{{ n.en_iso ?? '—' }}</td>
            <td class="mono t4">{{ n.csn ?? '—' }}</td>
            <td class="mono t4">{{ n.aisi ?? '—' }}</td>
            <td class="t4">{{ n.material_group?.name ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.tab-content { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.srch-bar {
  display: flex; align-items: center; gap: 6px;
  padding: 5px var(--pad); border-bottom: 1px solid var(--b1); flex-shrink: 0;
}
.srch-inp {
  flex: 1; background: var(--b1); border: 1px solid var(--b2);
  border-radius: var(--rs); color: var(--t1); font-size: var(--fs);
  padding: 3px 6px; outline: none;
}
.srch-inp::placeholder { color: var(--t4); }
.srch-inp:focus { border-color: var(--b3); }
.srch-count { font-size: 10px; color: var(--t4); white-space: nowrap; font-family: var(--mono); }
.mod-placeholder {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 8px; color: var(--t4);
}
.mod-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--b2); }
.mod-dot.err { background: var(--err); }
.mod-label { font-size: var(--fsl); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
.ot-wrap { flex: 1; overflow-y: auto; overflow-x: hidden; min-height: 0; }
.ot { width: 100%; border-collapse: collapse; }
.ot thead { background: rgba(255,255,255,0.025); position: sticky; top: 0; z-index: 2; }
.ot th {
  padding: 4px var(--pad); font-size: 10px; font-weight: 600; color: var(--t4);
  text-transform: uppercase; letter-spacing: 0.04em; text-align: left;
  border-bottom: 1px solid var(--b2); white-space: nowrap;
}
.ot td {
  padding: 4px var(--pad); font-size: var(--fs); color: var(--t2);
  border-bottom: 1px solid rgba(255,255,255,0.025); vertical-align: middle;
}
.ot tbody tr:hover td { background: var(--b1); }
.mono { font-family: var(--mono); }
.t3 { color: var(--t3); }
.t4 { color: var(--t4); }
</style>
