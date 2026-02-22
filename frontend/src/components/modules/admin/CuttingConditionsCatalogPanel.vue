<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { PivotResponse, PivotCell, PivotOperation, CuttingConditionUpdate } from '@/types/cutting-condition'
import { getCuttingConditionsPivot, updateCuttingCondition, seedCuttingConditions } from '@/api/cutting-conditions'
import CuttingConditionEditModal from './CuttingConditionEditModal.vue'

const pivotData = ref<PivotResponse | null>(null)
const currentMode = ref<string>('mid')
const loading = ref(false)
const error = ref<string | null>(null)
const modifiedCells = ref<Set<string>>(new Set())

const editModalVisible = ref(false)
const editCell = ref<PivotCell | null>(null)
const editOperation = ref<PivotOperation | null>(null)
const editMaterialName = ref('')
const editMaterialCode = ref('')

async function loadPivot() {
  loading.value = true
  error.value = null
  try {
    pivotData.value = await getCuttingConditionsPivot(currentMode.value)
  } catch (e: unknown) {
    const err = e as { message?: string }
    error.value = err?.message ?? 'Chyba při načítání dat'
  } finally {
    loading.value = false
  }
}

async function handleModeChange(mode: string) {
  currentMode.value = mode
  modifiedCells.value.clear()
  await loadPivot()
}

function openEdit(materialCode: string, op: PivotOperation) {
  if (!pivotData.value) return
  const cell = pivotData.value.cells[materialCode]?.[`${op.operation_type}/${op.operation}`]
  if (!cell) return
  editCell.value = cell
  editOperation.value = op
  editMaterialName.value = pivotData.value.material_names[materialCode] ?? materialCode
  editMaterialCode.value = materialCode
  editModalVisible.value = true
}

async function handleSave(data: CuttingConditionUpdate) {
  if (!editCell.value) return
  try {
    const updated = await updateCuttingCondition(editCell.value.id, data)
    if (pivotData.value && editOperation.value) {
      const key = `${editOperation.value.operation_type}/${editOperation.value.operation}`
      const cells = pivotData.value.cells[editMaterialCode.value]
      if (cells && cells[key]) {
        cells[key] = { ...cells[key], Vc: updated.Vc, f: updated.f, Ap: updated.Ap, notes: updated.notes, version: updated.version }
      }
      modifiedCells.value.add(`${editMaterialCode.value}/${key}`)
    }
    editModalVisible.value = false
  } catch (e: unknown) {
    const err = e as { message?: string }
    error.value = err?.message ?? 'Chyba při ukládání'
  }
}

async function handleSeed() {
  if (!confirm('Přepsat všechna data z katalogu? Všechny ruční úpravy budou ztraceny!')) return
  loading.value = true
  try {
    const result = await seedCuttingConditions()
    alert(`Naplněno ${result.count} záznamů z katalogu.`)
    modifiedCells.value.clear()
    await loadPivot()
  } catch (e: unknown) {
    const err = e as { message?: string }
    error.value = err?.message ?? 'Chyba při seedování'
  } finally {
    loading.value = false
  }
}

function formatCell(cell: PivotCell | undefined, op: PivotOperation): string {
  if (!cell) return '—'
  const parts: string[] = []
  for (const field of op.fields) {
    if (field === 'Vc' && cell.Vc != null) parts.push(String(cell.Vc))
    else if (field === 'f' && cell.f != null) parts.push(String(cell.f))
    else if (field === 'fz' && (cell.fz != null || cell.f != null)) parts.push(String(cell.fz ?? cell.f))
    else if (field === 'Ap' && cell.Ap != null) parts.push(String(cell.Ap))
    else parts.push('—')
  }
  return parts.join(' / ')
}

function isCellModified(materialCode: string, op: PivotOperation): boolean {
  return modifiedCells.value.has(`${materialCode}/${op.operation_type}/${op.operation}`)
}

onMounted(loadPivot)
</script>

<template>
  <div class="cutting-conditions-panel">
    <div class="toolbar">
      <div class="mode-selector">
        <button v-for="mode in ['low', 'mid', 'high']" :key="mode" :class="['mode-btn', { active: currentMode === mode }]" @click="handleModeChange(mode)">
          {{ mode.toUpperCase() }}
        </button>
      </div>
      <button class="seed-btn" @click="handleSeed" :disabled="loading">Seed z katalogu</button>
    </div>

    <div v-if="error" class="error-bar">{{ error }}</div>
    <div v-if="loading" class="loading">Načítám...</div>

    <div v-else-if="pivotData" class="table-wrapper">
      <table class="pivot-table">
        <thead>
          <tr>
            <th class="sticky-col">Materiál</th>
            <th v-for="op in pivotData.operations" :key="`${op.operation_type}/${op.operation}`">
              <div class="op-label">{{ op.label }}</div>
              <div class="op-fields">{{ op.operation_type === 'sawing' ? 'mm/min' : op.fields.join(' / ') }}</div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="mat in pivotData.materials" :key="mat">
            <td class="sticky-col material-name">{{ pivotData.material_names[mat] }}</td>
            <td v-for="op in pivotData.operations" :key="`${mat}/${op.operation_type}/${op.operation}`"
                :class="['cell', { modified: isCellModified(mat, op) }]" @click="openEdit(mat, op)">
              {{ formatCell(pivotData.cells[mat]?.[`${op.operation_type}/${op.operation}`], op) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else-if="!loading" class="empty-state">Žádná data. Klikněte na "Seed z katalogu" pro naplnění.</div>

    <CuttingConditionEditModal :visible="editModalVisible" :cell="editCell" :operation="editOperation"
                               :material-name="editMaterialName" @close="editModalVisible = false" @save="handleSave" />
  </div>
</template>

<style scoped>
.cutting-conditions-panel { height: 100%; display: flex; flex-direction: column; padding: var(--pad); gap: var(--pad); }
.toolbar { display: flex; align-items: center; justify-content: space-between; gap: var(--pad); }
.mode-selector { display: flex; gap: 4px; background: var(--surface); border-radius: var(--r); padding: 2px; border: 1px solid var(--b2); }
.mode-btn { padding: 4px var(--pad); border: none; background: transparent; color: var(--t3); font-size: var(--fs); font-weight: 600; cursor: pointer; border-radius: var(--rs); transition: all 100ms; }
.mode-btn.active { background: var(--red-10); color: rgba(229, 57, 53, 0.7); border-color: var(--red); }
.mode-btn:hover:not(.active) { background: var(--b1); }
.seed-btn { padding: 6px 12px; border: 1px solid var(--b2); background: var(--surface); color: var(--t1); font-size: var(--fs); cursor: pointer; border-radius: var(--r); transition: all 100ms; }
.seed-btn:hover { background: var(--b1); }
.seed-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.error-bar { padding: 6px var(--pad); background: rgba(248,113,113,0.15); color: var(--err); border-radius: var(--r); font-size: var(--fs); }
.loading { text-align: center; padding: 20px; color: var(--t3); }
.table-wrapper { flex: 1; overflow: auto; border: 1px solid var(--b2); border-radius: var(--r); }
.pivot-table { width: max-content; min-width: 100%; border-collapse: collapse; font-size: var(--fs); }
.pivot-table th, .pivot-table td { padding: 4px 6px; border: 1px solid var(--b2); white-space: nowrap; }
.pivot-table thead th { background: var(--surface); position: sticky; top: 0; z-index: 2; text-align: center; }
.sticky-col { position: sticky; left: 0; z-index: 3; background: var(--surface); font-weight: 600; min-width: 120px; }
thead .sticky-col { z-index: 4; }
.material-name { font-weight: 500; color: var(--t1); }
.op-label { font-weight: 600; font-size: var(--fs); }
.op-fields { font-weight: 400; color: var(--t3); font-size: var(--fs); }
.cell { cursor: pointer; text-align: center; transition: background 100ms; color: var(--t1); }
.cell:hover { background: var(--b1); }
.cell.modified { background: rgba(251,191,36,0.15); }
</style>
