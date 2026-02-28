/** Machine Plan DnD — Pinia store */

import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as api from '@/api/machinePlanDnd'
import * as plannerApi from '@/api/productionPlanner'
import { useWorkshopStore } from './workshop'
import { useUiStore } from './ui'
import type { MachinePlanItem } from '@/types/workshop'
import type { MachinePlanOperationKey } from '@/api/machinePlanDnd'
import type { PriorityTier } from '@/types/production-planner'

export const useMachinePlanDndStore = defineStore('machinePlanDnd', () => {
  const ui = useUiStore()

  const selectedWc = ref('')
  const plannedItems = ref<MachinePlanItem[]>([])
  const unassignedItems = ref<MachinePlanItem[]>([])
  const loading = ref(false)
  const selectedItem = ref<MachinePlanItem | null>(null)
  // SWR state
  const lastFetched = ref<Date | null>(null)
  const isRevalidating = ref(false)
  /** Klíče (Job|Suffix|OperNum) položek přetažených DnD v této session */
  const dndMovedKeys = ref<Set<string>>(new Set())

  async function fetchPlan(wc: string) {
    selectedWc.value = wc
    // SWR: pokud máme data, ukazujeme revalidating místo full loading
    if (plannedItems.value.length > 0 || unassignedItems.value.length > 0) {
      isRevalidating.value = true
    } else {
      loading.value = true
    }
    try {
      const data = await api.getMachinePlanDnd(wc)
      plannedItems.value = data.planned
      unassignedItems.value = data.unassigned
      lastFetched.value = new Date()
    } catch {
      ui.showError('Nepodařilo se načíst plán stroje')
    } finally {
      loading.value = false
      isRevalidating.value = false
    }
  }

  async function fetchPlanIfStale(wc: string, staleMs = 30000) {
    if (selectedWc.value === wc && lastFetched.value && Date.now() - lastFetched.value.getTime() < staleMs) {
      return // data jsou fresh pro toto WC
    }
    await fetchPlan(wc)
  }

  async function reorder(newOrder: MachinePlanItem[]) {
    const oldPlanned = [...plannedItems.value]
    // Optimistic update
    plannedItems.value = newOrder

    const orderedKeys: MachinePlanOperationKey[] = newOrder.map((item) => ({
      job: item.Job,
      suffix: item.Suffix ?? '0',
      oper_num: item.OperNum,
    }))

    try {
      await api.reorderMachinePlan(selectedWc.value, orderedKeys)
    } catch {
      // Rollback
      plannedItems.value = oldPlanned
      ui.showError('Nepodařilo se uložit pořadí')
      await fetchPlan(selectedWc.value)
    }
  }

  async function moveToPlanned(item: MachinePlanItem) {
    // Optimistic: remove from unassigned, add to planned
    unassignedItems.value = unassignedItems.value.filter(
      (i) => !(i.Job === item.Job && i.Suffix === item.Suffix && i.OperNum === item.OperNum),
    )
    plannedItems.value.push(item)

    try {
      await api.addToPlan(selectedWc.value, item.Job, item.Suffix ?? '0', item.OperNum)
    } catch {
      ui.showError('Nepodařilo se přidat operaci do plánu')
      await fetchPlan(selectedWc.value)
    }
  }

  async function moveToUnassigned(item: MachinePlanItem) {
    // Optimistic: remove from planned, add to unassigned
    plannedItems.value = plannedItems.value.filter(
      (i) => !(i.Job === item.Job && i.Suffix === item.Suffix && i.OperNum === item.OperNum),
    )
    unassignedItems.value.push(item)

    try {
      await api.removeFromPlan(selectedWc.value, item.Job, item.Suffix ?? '0', item.OperNum)
    } catch {
      ui.showError('Nepodařilo se odebrat operaci z plánu')
      await fetchPlan(selectedWc.value)
    }
  }

  const TIER_CYCLE: PriorityTier[] = ['normal', 'urgent', 'hot']

  async function cycleTier(item: MachinePlanItem) {
    const current: PriorityTier = item.Tier ?? 'normal'
    const idx = TIER_CYCLE.indexOf(current)
    const next = TIER_CYCLE[(idx + 1) % TIER_CYCLE.length]!
    const suffix = item.Suffix ?? '0'

    // Optimistic update — only visual, no re-fetch
    item.Tier = next
    item.IsHot = next === 'hot'
    item.Priority = next === 'hot' ? 5 : next === 'urgent' ? 20 : 100

    try {
      await plannerApi.setTier(item.Job, suffix, next)
      // Re-fetch to get proper backend sort (hot items float to top)
      if (selectedWc.value) {
        await fetchPlan(selectedWc.value)
      }
    } catch {
      // Rollback
      item.Tier = current
      item.IsHot = current === 'hot'
      item.Priority = current === 'hot' ? 5 : current === 'urgent' ? 20 : 100
      ui.showError('Nepodařilo se změnit tier')
    }
  }

  function itemKey(item: MachinePlanItem): string {
    return `${item.Job}|${item.Suffix ?? '0'}|${item.OperNum}`
  }

  function markDndMoved(item: MachinePlanItem) {
    dndMovedKeys.value.add(itemKey(item))
    // Force reactivity (Set)
    dndMovedKeys.value = new Set(dndMovedKeys.value)
  }

  function isDndMoved(item: MachinePlanItem): boolean {
    return dndMovedKeys.value.has(itemKey(item))
  }

  function selectItem(item: MachinePlanItem | null) {
    selectedItem.value = item
    if (item) {
      const workshop = useWorkshopStore()
      workshop.selectQueueItem(item)
    }
  }

  return {
    selectedWc,
    plannedItems,
    unassignedItems,
    loading,
    selectedItem,
    lastFetched,
    isRevalidating,
    fetchPlan,
    fetchPlanIfStale,
    reorder,
    moveToPlanned,
    moveToUnassigned,
    cycleTier,
    dndMovedKeys,
    markDndMoved,
    isDndMoved,
    selectItem,
  }
})
