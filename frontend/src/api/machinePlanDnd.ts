/** Machine Plan DnD — API modul */

import { apiClient } from './client'
import type { MachinePlanItem } from '@/types/workshop'

export interface MachinePlanDndResponse {
  planned: MachinePlanItem[]
  unassigned: MachinePlanItem[]
}

export interface MachinePlanOperationKey {
  job: string
  suffix: string
  oper_num: string
}

export async function getMachinePlanDnd(wc: string, limit = 500): Promise<MachinePlanDndResponse> {
  const res = await apiClient.get<MachinePlanDndResponse>('/machine-plan-dnd/plan', {
    params: { wc, limit },
  })
  return res.data
}

export async function reorderMachinePlan(wc: string, orderedKeys: MachinePlanOperationKey[]): Promise<{ updated: number }> {
  const res = await apiClient.patch<{ updated: number }>('/machine-plan-dnd/reorder', {
    wc,
    ordered_keys: orderedKeys,
  })
  return res.data
}

export async function addToPlan(
  wc: string,
  job: string,
  suffix: string,
  oper_num: string,
  position?: number,
): Promise<Record<string, unknown>> {
  const res = await apiClient.post('/machine-plan-dnd/entries', {
    wc,
    job,
    suffix,
    oper_num,
    position: position ?? null,
  })
  return res.data
}

export async function removeFromPlan(
  wc: string,
  job: string,
  suffix: string,
  oper_num: string,
): Promise<{ removed: boolean }> {
  const res = await apiClient.delete<{ removed: boolean }>('/machine-plan-dnd/entries', {
    data: { wc, job, suffix, oper_num },
  })
  return res.data
}
