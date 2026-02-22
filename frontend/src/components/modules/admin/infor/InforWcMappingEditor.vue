<script setup lang="ts">
/**
 * Work Center Mapping Editor
 *
 * Allows user to map Infor WC codes to Gestima WC numbers
 */

import { ref, onMounted } from 'vue'
import { getWcMapping, updateWcMapping } from '@/api/infor-import'
import { useUiStore } from '@/stores/ui'
import { Plus, Trash2, Save } from 'lucide-vue-next'
import { ICON_SIZE } from '@/config/design'
import type { WcMapping } from '@/types/infor'

const uiStore = useUiStore()
const mapping = ref<WcMapping>({})
const loading = ref(false)
const saving = ref(false)

interface MappingRow {
  inforCode: string
  gestimaWc: string
}

const rows = ref<MappingRow[]>([])

onMounted(async () => {
  await loadMapping()
})

async function loadMapping() {
  loading.value = true
  try {
    mapping.value = await getWcMapping()
    rows.value = Object.entries(mapping.value).map(([inforCode, gestimaWc]) => ({
      inforCode,
      gestimaWc
    }))
  } catch (error: unknown) {
    uiStore.showError((error as Error).message || 'Chyba načtení WC mapping')
  } finally {
    loading.value = false
  }
}

function addRow() {
  rows.value.push({ inforCode: '', gestimaWc: '' })
}

function removeRow(index: number) {
  rows.value.splice(index, 1)
}

async function saveMapping() {
  saving.value = true
  try {
    const newMapping: WcMapping = {}
    rows.value.forEach(row => {
      if (row.inforCode.trim() && row.gestimaWc.trim()) {
        newMapping[row.inforCode.trim()] = row.gestimaWc.trim()
      }
    })
    await updateWcMapping(newMapping)
    mapping.value = newMapping
    uiStore.showSuccess('WC mapping uložen')
  } catch (error: unknown) {
    uiStore.showError((error as Error).message || 'Chyba uložení')
  } finally {
    saving.value = false
  }
}

function getStatusText(row: MappingRow): string {
  if (!row.inforCode.trim() || !row.gestimaWc.trim()) return 'Neúplné'
  return 'OK'
}
</script>

<template>
  <div class="wc-mapping-editor">
    <div class="header">
      <h4>Work Center Mapping</h4>
      <p class="help-text">Mapování Infor WC kódů na Gestima WC čísla</p>
    </div>

    <div v-if="loading" class="loading-state">Načítání...</div>

    <div v-else class="content">
      <div class="toolbar">
        <button @click="addRow" class="btn-ghost">
          <Plus :size="ICON_SIZE.STANDARD" /> Přidat řádek
        </button>
        <button @click="saveMapping" :disabled="saving" class="btn-ghost btn-primary">
          <Save :size="ICON_SIZE.STANDARD" /> Uložit
        </button>
      </div>

      <div class="table-wrapper">
        <table class="mapping-table">
          <thead>
            <tr>
              <th>Infor WC Code</th>
              <th>Gestima WC Number</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in rows" :key="idx">
              <td>
                <input v-model="row.inforCode" class="input" placeholder="např. WC01" />
              </td>
              <td>
                <input v-model="row.gestimaWc" class="input" placeholder="např. 1" />
              </td>
              <td class="status-cell">
                <span :class="['status-badge', getStatusText(row) === 'OK' ? 'ok' : 'incomplete']">
                  {{ getStatusText(row) }}
                </span>
              </td>
              <td class="actions-cell">
                <button @click="removeRow(idx)" class="btn-ghost btn-danger">
                  <Trash2 :size="ICON_SIZE.STANDARD" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="rows.length === 0" class="empty-state">
        <p>Žádné mapování. Přidejte řádek pomocí tlačítka "Přidat řádek".</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wc-mapping-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  background: var(--base);
}

.header h4 {
  font-size: 16px;
  font-weight: 600;
  color: var(--t1);
  margin: 0;
}

.help-text {
  font-size: var(--fs);
  color: var(--t3);
  margin-top: 4px;
}

.content {
  display: flex;
  flex-direction: column;
  gap: var(--pad);
}

.toolbar {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.table-wrapper {
  overflow: auto;
  border: 1px solid var(--b2);
  border-radius: var(--r);
}

.mapping-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs);
}

.mapping-table th {
  background: var(--surface);
  padding: 6px var(--pad);
  text-align: left;
  font-weight: 600;
  color: var(--t3);
  border-bottom: 1px solid var(--b2);
  position: sticky;
  top: 0;
}

.mapping-table td {
  padding: 6px var(--pad);
  border-bottom: 1px solid var(--b1);
}

.input {
  width: 100%;
  padding: 4px 6px;
  border: 1px solid var(--b2);
  background: var(--base);
  color: var(--t1);
  border-radius: var(--rs);
  font-size: var(--fs);
}

.input:focus {
  outline: none;
  border-color: var(--b3);
}

.status-cell {
  text-align: center;
}

.status-badge {
  display: inline-block;
  padding: 4px 6px;
  border-radius: var(--rs);
  font-size: var(--fs);
  font-weight: 600;
}

.status-badge.ok {
  background: rgba(52,211,153,0.1);
  color: var(--ok);
}

.status-badge.incomplete {
  background: rgba(251,191,36,0.1);
  color: var(--warn);
}

.actions-cell {
  text-align: center;
  width: 60px;
}

</style>
