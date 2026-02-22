import { ref } from 'vue'
import { defineStore } from 'pinia'
import { useUiStore } from './ui'
import * as opsApi from '@/api/operations'
import type { Operation, OperationCreate, OperationUpdate } from '@/types/operation'

export const useOperationsStore = defineStore('operations', () => {
  const ui = useUiStore()

  // Cache: partId → operations[]
  const byPartId = ref<Record<number, Operation[]>>({})
  const loading = ref(false)

  function forPart(partId: number): Operation[] {
    return byPartId.value[partId] ?? []
  }

  async function fetchByPartId(partId: number): Promise<void> {
    loading.value = true
    try {
      byPartId.value[partId] = await opsApi.getByPartId(partId)
    } catch {
      ui.showError('Chyba při načítání operací')
    } finally {
      loading.value = false
    }
  }

  async function createOp(payload: OperationCreate): Promise<Operation | null> {
    ui.startLoading()
    try {
      const op = await opsApi.create(payload)
      if (!byPartId.value[op.part_id]) byPartId.value[op.part_id] = []
      const list = byPartId.value[op.part_id]!
      list.push(op)
      list.sort((a, b) => a.seq - b.seq)
      byPartId.value[op.part_id] = list
      ui.showSuccess('Operace přidána')
      return op
    } catch {
      ui.showError('Chyba při vytváření operace')
      return null
    } finally {
      ui.stopLoading()
    }
  }

  async function updateOp(operationId: number, partId: number, payload: OperationUpdate): Promise<Operation | null> {
    ui.startLoading()
    try {
      const updated = await opsApi.update(operationId, payload)
      const list = byPartId.value[partId]
      if (list) {
        const idx = list.findIndex(o => o.id === operationId)
        if (idx >= 0) list[idx] = updated
        list.sort((a, b) => a.seq - b.seq)
      }
      ui.showSuccess('Operace uložena')
      return updated
    } catch {
      ui.showError('Chyba při ukládání operace')
      return null
    } finally {
      ui.stopLoading()
    }
  }

  async function removeOp(operationId: number, partId: number): Promise<boolean> {
    ui.startLoading()
    try {
      await opsApi.remove(operationId)
      const list = byPartId.value[partId]
      if (list) {
        byPartId.value[partId] = list.filter(o => o.id !== operationId)
      }
      ui.showSuccess('Operace odstraněna')
      return true
    } catch {
      ui.showError('Chyba při odstraňování operace')
      return false
    } finally {
      ui.stopLoading()
    }
  }

  function invalidatePartCache(partId: number) {
    delete byPartId.value[partId]
  }

  return {
    byPartId,
    loading,
    forPart,
    fetchByPartId,
    createOp,
    updateOp,
    removeOp,
    invalidatePartCache,
  }
})
