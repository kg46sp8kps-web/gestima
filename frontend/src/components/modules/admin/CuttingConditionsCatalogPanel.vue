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
.cutting-conditions-panel { height: 100%; display: flex; flex-direction: column; padding: var(--space-3); gap: var(--space-3); }
.toolbar { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); }
.mode-selector { display: flex; gap: var(--space-1); background: var(--bg-surface); border-radius: var(--radius-md); padding: var(--space-0\.5); border: 1px solid var(--border-default); }
.mode-btn { padding: var(--space-1) var(--space-3); border: none; background: transparent; color: var(--text-secondary); font-size: var(--text-sm); font-weight: 600; cursor: pointer; border-radius: var(--radius-sm); transition: all var(--duration-fast); }
.mode-btn.active { background: var(--brand-subtle); color: var(--brand-text); border-color: var(--brand); }
.mode-btn:hover:not(.active) { background: var(--state-hover); }
.seed-btn { padding: var(--space-2) var(--space-4); border: 1px solid var(--border-default); background: var(--bg-surface); color: var(--text-primary); font-size: var(--text-sm); cursor: pointer; border-radius: var(--radius-md); transition: all var(--duration-fast); }
.seed-btn:hover { background: var(--state-hover); }
.seed-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.error-bar { padding: var(--space-2) var(--space-3); background: var(--palette-danger-light, rgba(244, 63, 94, 0.15)); color: var(--palette-danger); border-radius: var(--radius-md); font-size: var(--text-sm); }
.loading { text-align: center; padding: var(--space-6); color: var(--text-secondary); }
.table-wrapper { flex: 1; overflow: auto; border: 1px solid var(--border-default); border-radius: var(--radius-md); }
.pivot-table { width: max-content; min-width: 100%; border-collapse: collapse; font-size: var(--text-xs); }
.pivot-table th, .pivot-table td { padding: var(--space-1) var(--space-2); border: 1px solid var(--border-default); white-space: nowrap; }
.pivot-table thead th { background: var(--bg-surface); position: sticky; top: 0; z-index: 2; text-align: center; }
.sticky-col { position: sticky; left: 0; z-index: 3; background: var(--bg-surface); font-weight: 600; min-width: 120px; }
thead .sticky-col { z-index: 4; }
.material-name { font-weight: 500; color: var(--text-primary); }
.op-label { font-weight: 600; font-size: var(--text-xs); }
.op-fields { font-weight: 400; color: var(--text-secondary); font-size: 10px; }
.cell { cursor: pointer; text-align: center; transition: background var(--duration-fast); color: var(--text-primary); }
.cell:hover { background: var(--state-hover); }
.cell.modified { background: var(--palette-warning-light); }
</style>
