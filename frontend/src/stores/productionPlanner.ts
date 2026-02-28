/** Production Planner — Pinia store */

import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as api from '@/api/productionPlanner'
import { useUiStore } from './ui'
import type { PlannerVpRow, PriorityTier, WcLane } from '@/types/production-planner'

const TIER_CYCLE: PriorityTier[] = ['normal', 'urgent', 'hot']
const TIER_PRIORITY: Record<PriorityTier, number> = { hot: 5, urgent: 20, frozen: 50, normal: 100 }

export const useProductionPlannerStore = defineStore('productionPlanner', () => {
  const ui = useUiStore()

  const vps = ref<PlannerVpRow[]>([])
  const wcLanes = ref<WcLane[]>([])
  const timeRange = ref<{ min_date: string; max_date: string }>({
    min_date: '',
    max_date: '',
  })
  const loading = ref(false)

  async function fetchData(limit = 500) {
    loading.value = true
    try {
      const data = await api.getPlannerData(limit)
      vps.value = data.vps
      wcLanes.value = data.wc_lanes ?? []
      timeRange.value = data.time_range
    } catch {
      ui.showError('Nepodařilo se načíst data plánovače výroby')
    } finally {
      loading.value = false
    }
  }

  async function setPriority(job: string, suffix: string, priority: number) {
    // Optimistic update
    const vp = vps.value.find((v) => v.job === job && v.suffix === suffix)
    const oldPriority = vp?.priority
    if (vp) vp.priority = priority

    try {
      await api.setPriority(job, suffix, priority)
    } catch {
      if (vp && oldPriority !== undefined) vp.priority = oldPriority
      ui.showError('Nepodařilo se uložit prioritu')
    }
  }

  async function setFire(job: string, suffix: string, is_hot: boolean) {
    // Optimistic: set this one only (multi-hot allowed)
    const vp = vps.value.find((v) => v.job === job && v.suffix === suffix)
    const oldHot = vp?.is_hot
    if (vp) vp.is_hot = is_hot

    try {
      await api.setFire(job, suffix, is_hot)
    } catch {
      if (vp && oldHot !== undefined) vp.is_hot = oldHot
      ui.showError('Nepodařilo se nastavit flag')
    }
  }

  async function setTier(job: string, suffix: string, tier: PriorityTier) {
    const vp = vps.value.find((v) => v.job === job && v.suffix === suffix)
    const oldTier = vp?.tier
    const oldPriority = vp?.priority
    const oldHot = vp?.is_hot
    if (vp) {
      vp.tier = tier
      vp.priority = TIER_PRIORITY[tier]
      vp.is_hot = tier === 'hot'
    }

    try {
      await api.setTier(job, suffix, tier)
    } catch {
      if (vp) {
        if (oldTier !== undefined) vp.tier = oldTier
        if (oldPriority !== undefined) vp.priority = oldPriority
        if (oldHot !== undefined) vp.is_hot = oldHot
      }
      ui.showError('Nepodařilo se nastavit tier')
    }
  }

  function cycleTier(job: string, suffix: string) {
    const vp = vps.value.find((v) => v.job === job && v.suffix === suffix)
    if (!vp) return
    const idx = TIER_CYCLE.indexOf(vp.tier ?? 'normal')
    const next = TIER_CYCLE[(idx + 1) % TIER_CYCLE.length]!
    setTier(job, suffix, next)
  }

  return {
    vps,
    wcLanes,
    timeRange,
    loading,
    fetchData,
    setPriority,
    setFire,
    setTier,
    cycleTier,
  }
})
