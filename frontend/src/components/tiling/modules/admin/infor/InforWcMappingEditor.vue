<script setup lang="ts">
/**
 * Work Center Mapping Editor
 *
 * Allows user to map Infor WC codes to Gestima WC numbers
 */

import { ref, onMounted } from 'vue'
import { getWcMapping, updateWcMapping } from '@/api/infor-jobs'
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
  <!-- eslint-disable vue/no-restricted-html-elements -->
  <div class="wc-mapping-editor">
    <div class="header">
      <h4>Work Center Mapping</h4>
      <p class="help-text">Mapování Infor WC kódů na Gestima WC čísla</p>
    </div>

    <div v-if="loading" class="loading-state">Načítání...</div>

    <div v-else class="content">
      <div class="toolbar">
        <button @click="addRow" class="btn-secondary">
          <Plus :size="ICON_SIZE" /> Přidat řádek
        </button>
        <button @click="saveMapping" :disabled="saving" class="btn-primary">
          <Save :size="ICON_SIZE" /> Uložit
        </button>
      </div>

      <div class="ot-wrap">
        <table class="ot">
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
                <span class="badge">
                  <span :class="getStatusText(row) === 'OK' ? 'badge-dot badge-dot-ok' : 'badge-dot badge-dot-warn'"></span>
                  {{ getStatusText(row) }}
                </span>
              </td>
              <td class="actions-cell">
                <button @click="removeRow(idx)" class="icon-btn icon-btn-sm icon-btn-danger">
                  <Trash2 :size="ICON_SIZE" />
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
  
}

.header h4 {
  font-size: var(--fsh);
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

.ot-wrap {
  overflow-y: auto;
  border: 1px solid var(--b2);
  border-radius: var(--r);
}

.status-cell {
  text-align: center;
}

.actions-cell {
  text-align: center;
  width: 60px;
}
</style>
