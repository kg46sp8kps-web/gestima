<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { CheckIcon, XIcon } from 'lucide-vue-next'
import { useUiStore } from '@/stores/ui'
import * as adminApi from '@/api/admin'
import type { AdminUser } from '@/types/admin-user'
import Spinner from '@/components/ui/Spinner.vue'
import { ICON_SIZE_SM } from '@/config/design'

const ui = useUiStore()

const users = ref<AdminUser[]>([])
const loading = ref(false)
const error = ref(false)

const editingId = ref<number | null>(null)
const editDraft = ref<{ email: string | null; role: string; is_active: boolean; version: number } | null>(null)

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

function startEdit(u: AdminUser) {
  editingId.value = u.id
  editDraft.value = { email: u.email, role: u.role, is_active: u.is_active, version: u.version }
}

async function saveEdit() {
  const id = editingId.value
  const draft = editDraft.value
  if (!id || !draft) return
  editingId.value = null
  editDraft.value = null
  try {
    const updated = await adminApi.updateUser(id, draft)
    const idx = users.value.findIndex(u => u.id === id)
    if (idx !== -1) users.value[idx] = updated
    ui.showSuccess('Uživatel uložen')
  } catch {
    ui.showError('Chyba při ukládání uživatele')
  }
}

function cancelEdit() {
  editingId.value = null
  editDraft.value = null
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') { e.preventDefault(); saveEdit() }
  if (e.key === 'Escape') { e.preventDefault(); cancelEdit() }
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
            <th style="width:80px">Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="u in users"
            :key="u.id"
            :data-testid="`user-row-${u.id}`"
            :class="{ 'row-editing': editingId === u.id, 'row-clickable': editingId !== u.id }"
            @click="editingId !== u.id ? startEdit(u) : undefined"
            @keydown.capture="editingId === u.id ? onKeydown($event) : undefined"
          >
            <td>
              <div class="user-name">{{ u.full_name || u.username }}</div>
              <div class="user-sub t4">{{ u.username }}</div>
            </td>
            <td>
              <template v-if="editingId === u.id && editDraft">
                <select
                  v-model="editDraft.role"
                  class="ei-sel"
                  :data-testid="`user-role-select-${u.id}`"
                  @click.stop
                >
                  <option value="admin">admin</option>
                  <option value="operator">operator</option>
                  <option value="viewer">viewer</option>
                </select>
              </template>
              <template v-else>
                <span :class="['role-badge', `role-${u.role}`]">{{ u.role }}</span>
              </template>
            </td>
            <td class="t4">
              <template v-if="editingId === u.id && editDraft">
                <input
                  v-model="editDraft.email"
                  type="text"
                  class="ei ei-wide"
                  :data-testid="`user-email-input-${u.id}`"
                  @click.stop
                />
              </template>
              <template v-else>
                {{ u.email ?? '—' }}
              </template>
            </td>
            <td>
              <template v-if="editingId === u.id && editDraft">
                <select
                  v-model="editDraft.is_active"
                  class="ei-sel"
                  :data-testid="`user-status-select-${u.id}`"
                  @click.stop
                >
                  <option :value="true">Aktivní</option>
                  <option :value="false">Neaktivní</option>
                </select>
              </template>
              <template v-else>
                <span v-if="u.is_active" class="badge">
                  <span class="badge-dot ok" />Aktivní
                </span>
                <span v-else class="badge">
                  <span class="badge-dot neutral" />Neaktivní
                </span>
              </template>
            </td>
            <template v-if="editingId === u.id && editDraft">
              <td class="act-cell">
                <button
                  class="icon-btn icon-btn-brand icon-btn-sm"
                  data-testid="user-save-btn"
                  title="Uložit (Enter)"
                  @click.stop="saveEdit"
                >
                  <CheckIcon :size="ICON_SIZE_SM" />
                </button>
                <button
                  class="icon-btn icon-btn-sm"
                  data-testid="user-cancel-btn"
                  title="Zrušit (Esc)"
                  @click.stop="cancelEdit"
                >
                  <XIcon :size="ICON_SIZE_SM" />
                </button>
              </td>
            </template>
            <template v-else>
              <td />
            </template>
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
.ot tbody tr.row-clickable { cursor: pointer; }
.ot tbody tr.row-clickable:hover td { background: var(--b1); }
.t4 { color: var(--t4); }
.user-name { font-weight: 500; color: var(--t1); }
.user-sub { font-size: var(--fsm); margin-top: 1px; }
.role-badge {
  display: inline-block; font-size: var(--fss); font-weight: 600;
  padding: 1px 5px; border-radius: 99px; background: var(--b2); color: var(--t3);
  text-transform: uppercase; letter-spacing: 0.04em;
}
.role-badge.role-admin { background: var(--red-10); color: var(--red); }
.badge {
  display: inline-flex; align-items: center; gap: 3px; padding: 1px 5px;
  font-size: var(--fsm); font-weight: 500; border-radius: 99px; background: var(--b1); color: var(--t2);
}
.badge-dot { width: 4px; height: 4px; border-radius: 50%; flex-shrink: 0; }
.badge-dot.ok { background: var(--ok); }
.badge-dot.neutral { background: var(--t4); }

/* Inline edit */
.row-editing td { background: var(--raised); border-bottom-color: var(--b3); }
.row-editing:hover td { background: var(--raised); }
.ei {
  background: var(--surface); border: 1px solid var(--b3); border-radius: var(--rs);
  color: var(--t1); font-size: var(--fs); padding: 2px 4px; outline: none;
}
.ei:focus { border-color: rgba(255,255,255,0.3); }
.ei-wide { width: 100%; }
.ei-sel {
  background: var(--surface); border: 1px solid var(--b3); border-radius: var(--rs);
  color: var(--t1); font-size: var(--fs); padding: 2px 4px; outline: none; cursor: pointer;
}
.ei-sel:focus { border-color: rgba(255,255,255,0.3); }
</style>
