<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { CheckIcon, XIcon } from 'lucide-vue-next'
import * as adminApi from '@/api/admin'
import type { MaterialNorm } from '@/types/admin-user'
import { useUiStore } from '@/stores/ui'
import Spinner from '@/components/ui/Spinner.vue'
import Input from '@/components/ui/Input.vue'
import InlineInput from '@/components/ui/InlineInput.vue'
import { ICON_SIZE_SM } from '@/config/design'

const ui = useUiStore()

const norms = ref<MaterialNorm[]>([])
const loading = ref(false)
const error = ref(false)
const search = ref('')

const editingId = ref<number | null>(null)
const editDraft = ref<{ w_nr: string | null; en_iso: string | null; csn: string | null; aisi: string | null; version: number } | null>(null)

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

function startEdit(n: MaterialNorm) {
  editingId.value = n.id
  editDraft.value = { w_nr: n.w_nr, en_iso: n.en_iso, csn: n.csn, aisi: n.aisi, version: n.version }
}

async function saveEdit() {
  const id = editingId.value
  const draft = editDraft.value
  if (!id || !draft) return
  editingId.value = null
  editDraft.value = null
  try {
    const updated = await adminApi.updateMaterialNorm(id, draft)
    const idx = norms.value.findIndex(n => n.id === id)
    if (idx !== -1) norms.value[idx] = updated
    ui.showSuccess('Norma uložena')
  } catch {
    ui.showError('Chyba při ukládání normy')
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
    <div class="srch-bar">
      <Input
        bare
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
            <th />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="n in filtered"
            :key="n.id"
            :data-testid="`norm-row-${n.id}`"
            :class="['row-clickable', { 'row-editing': editingId === n.id }]"
            @click="editingId !== n.id ? startEdit(n) : undefined"
            @keydown.capture="editingId === n.id ? onKeydown($event) : undefined"
          >
            <template v-if="editingId === n.id && editDraft">
              <td>
                <InlineInput
                  :modelValue="editDraft.w_nr"
                  @update:modelValue="editDraft.w_nr = ($event as string)?.toUpperCase() || null"
                  type="text"
                  class="ei-nm"
                  :data-testid="`norm-w-nr-input-${n.id}`"
                  @click.stop
                />
              </td>
              <td>
                <InlineInput
                  :modelValue="editDraft.en_iso"
                  @update:modelValue="editDraft.en_iso = ($event as string)?.toUpperCase() || null"
                  type="text"
                  class="ei-nm"
                  :data-testid="`norm-en-iso-input-${n.id}`"
                  @click.stop
                />
              </td>
              <td>
                <InlineInput
                  :modelValue="editDraft.csn"
                  @update:modelValue="editDraft.csn = ($event as string)?.toUpperCase() || null"
                  type="text"
                  class="ei-nm"
                  :data-testid="`norm-csn-input-${n.id}`"
                  @click.stop
                />
              </td>
              <td>
                <InlineInput
                  :modelValue="editDraft.aisi"
                  @update:modelValue="editDraft.aisi = ($event as string)?.toUpperCase() || null"
                  type="text"
                  class="ei-nm"
                  :data-testid="`norm-aisi-input-${n.id}`"
                  @click.stop
                />
              </td>
              <td class="t4">{{ n.material_group?.name ?? '—' }}</td>
              <td class="act-cell">
                <button
                  class="icon-btn icon-btn-brand icon-btn-sm"
                  data-testid="norm-save-btn"
                  title="Uložit (Enter)"
                  @click.stop="saveEdit"
                >
                  <CheckIcon :size="ICON_SIZE_SM" />
                </button>
                <button
                  class="icon-btn icon-btn-sm"
                  data-testid="norm-cancel-btn"
                  title="Zrušit (Esc)"
                  @click.stop="cancelEdit"
                >
                  <XIcon :size="ICON_SIZE_SM" />
                </button>
              </td>
            </template>
            <template v-else>
              <td class="">{{ n.w_nr ?? '—' }}</td>
              <td class="t3">{{ n.en_iso ?? '—' }}</td>
              <td class="t4">{{ n.csn ?? '—' }}</td>
              <td class="t4">{{ n.aisi ?? '—' }}</td>
              <td class="t4">{{ n.material_group?.name ?? '—' }}</td>
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
.srch-bar {
  display: flex; align-items: center; gap: 6px;
  padding: 5px var(--pad); border-bottom: 1px solid var(--b1); flex-shrink: 0;
}
.srch-inp {
  flex: 1; height: 28px; background: rgba(255,255,255,0.04); border: 1px solid var(--b2);
  border-radius: var(--rs); color: var(--t2); font-size: var(--fs);
  padding: 3px 6px; outline: none;
  transition: border-color 120ms var(--ease), background 120ms var(--ease), color 120ms var(--ease);
}
.srch-inp::placeholder { color: var(--t4); }
.srch-inp:focus { border-color: var(--b3); background: rgba(255,255,255,0.07); color: var(--t1); }
.srch-count { font-size: var(--fsm); color: var(--t4); white-space: nowrap; }
.mod-placeholder {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 8px; color: var(--t4);
}
.mod-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--b2); }
.mod-dot.err { background: var(--err); }
.mod-label { font-size: var(--fsm); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
.ot-wrap { flex: 1; overflow-y: auto; overflow-x: hidden; min-height: 0; }
.ot tbody tr.row-clickable { cursor: pointer; }
.ot tbody tr.row-clickable:hover td { background: var(--b1); }

.t3 { color: var(--t3); }
.t4 { color: var(--t4); }

/* Inline edit */
.row-editing td { background: var(--raised); border-bottom-color: var(--b3); }
.row-editing:hover td { background: var(--raised); }
/* visual styles come from InlineInput component */
.ei-nm { width: 100%; }
</style>
