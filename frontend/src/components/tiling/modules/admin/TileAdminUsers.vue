<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as adminApi from '@/api/admin'
import type { AdminUser } from '@/types/admin-user'
import Spinner from '@/components/ui/Spinner.vue'

const users = ref<AdminUser[]>([])
const loading = ref(false)
const error = ref(false)

async function load() {
  loading.value = true
  error.value = false
  try {
    users.value = await adminApi.getUsers()
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
    <div v-if="loading" class="mod-placeholder">
      <Spinner size="sm" />
    </div>
    <div v-else-if="error" class="mod-placeholder">
      <div class="mod-dot err" />
      <span class="mod-label">Chyba při načítání</span>
    </div>
    <div v-else-if="!users.length" class="mod-placeholder">
      <div class="mod-dot" />
      <span class="mod-label">Žádní uživatelé</span>
    </div>
    <div v-else class="ot-wrap">
      <table class="ot">
        <thead>
          <tr>
            <th>Jméno</th>
            <th style="width:80px">Role</th>
            <th>E-mail</th>
            <th style="width:60px">Status</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="u in users"
            :key="u.id"
            :data-testid="`user-row-${u.id}`"
          >
            <td>
              <div class="user-name">{{ u.full_name || u.username }}</div>
              <div class="user-sub t4">{{ u.username }}</div>
            </td>
            <td>
              <span :class="['role-badge', `role-${u.role}`]">{{ u.role }}</span>
            </td>
            <td class="t4">{{ u.email ?? '—' }}</td>
            <td>
              <span v-if="u.is_active" class="badge">
                <span class="badge-dot ok" />Aktivní
              </span>
              <span v-else class="badge">
                <span class="badge-dot neutral" />Neaktivní
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.tab-content { display: flex; flex-direction: column; flex: 1; min-height: 0; }
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
.t4 { color: var(--t4); }
.user-name { font-weight: 500; color: var(--t1); }
.user-sub { font-size: 10px; margin-top: 1px; }
.role-badge {
  display: inline-block; font-family: var(--mono); font-size: 9px; font-weight: 600;
  padding: 1px 5px; border-radius: 99px; background: var(--b2); color: var(--t3);
  text-transform: uppercase; letter-spacing: 0.04em;
}
.role-badge.role-admin { background: var(--red-10); color: var(--red); }
.badge {
  display: inline-flex; align-items: center; gap: 3px; padding: 1px 5px;
  font-size: 10px; font-weight: 500; border-radius: 99px; background: var(--b1); color: var(--t2);
}
.badge-dot { width: 4px; height: 4px; border-radius: 50%; flex-shrink: 0; }
.badge-dot.ok { background: var(--ok); }
.badge-dot.neutral { background: var(--t4); }
</style>
