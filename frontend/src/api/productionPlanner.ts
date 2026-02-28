/** Production Planner — API modul */

import { apiClient } from './client'
import type { PlannerData, PriorityTier } from '@/types/production-planner'

export async function getPlannerData(limit = 500): Promise<PlannerData> {
  const res = await apiClient.get<PlannerData>('/production-planner/data', {
    params: { limit },
  })
  return res.data
}

export async function setPriority(
  job: string,
  suffix: string,
  priority: number,
): Promise<{ job: string; suffix: string; priority: number; is_hot: boolean }> {
  const res = await apiClient.put('/production-planner/priority', {
    job,
    suffix,
    priority,
  })
  return res.data
}

export async function setFire(
  job: string,
  suffix: string,
  is_hot: boolean,
): Promise<{ job: string; suffix: string; priority: number; is_hot: boolean }> {
  const res = await apiClient.put('/production-planner/fire', {
    job,
    suffix,
    is_hot,
  })
  return res.data
}

export async function setTier(
  job: string,
  suffix: string,
  tier: PriorityTier,
): Promise<{ job: string; suffix: string; priority: number; is_hot: boolean }> {
  const res = await apiClient.put('/production-planner/tier', {
    job,
    suffix,
    tier,
  })
  return res.data
}
