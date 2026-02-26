/** Gestima Dílna — API modul */

import { apiClient } from './client'
import type {
  WorkshopJob,
  WorkshopOperation,
  WorkshopMaterial,
  WorkshopTransaction,
  WorkshopTransactionCreate,
} from '@/types/workshop'

/** Načte otevřené výrobní zakázky z Inforu (Type=J, JobStat=R) */
export async function getOpenJobs(wc?: string, limit = 500): Promise<WorkshopJob[]> {
  const params: Record<string, string | number> = { limit }
  if (wc) params.wc = wc
  const res = await apiClient.get<WorkshopJob[]>('/workshop/jobs', { params })
  return res.data
}

/** Načte operace konkrétní zakázky (SLJobRoutes per-job) */
export async function getJobOperations(job: string, suffix = '0'): Promise<WorkshopOperation[]> {
  // job je query param (ne path) — Infor job čísla mohou obsahovat lomítka
  const res = await apiClient.get<WorkshopOperation[]>('/workshop/operations', {
    params: { job, suffix },
  })
  return res.data
}

/** Načte materiálovou spotřebu k operaci (IteCzTsdSLJobMatls) */
export async function getOperationMaterials(
  job: string,
  oper: string,
  suffix = '0',
): Promise<WorkshopMaterial[]> {
  // job a oper jsou query params — Infor job čísla mohou obsahovat lomítka
  const res = await apiClient.get<WorkshopMaterial[]>('/workshop/materials', {
    params: { job, oper, suffix },
  })
  return res.data
}

/** Uloží transakci do lokálního bufferu */
export async function createTransaction(data: WorkshopTransactionCreate): Promise<WorkshopTransaction> {
  const res = await apiClient.post<WorkshopTransaction>('/workshop/transactions', data)
  return res.data
}

/** Odešle transakci do Inforu */
export async function postTransaction(txId: number): Promise<WorkshopTransaction> {
  const res = await apiClient.post<WorkshopTransaction>(`/workshop/transactions/${txId}/post`)
  return res.data
}

/** Načte moje transakce */
export async function listMyTransactions(skip = 0, limit = 100): Promise<WorkshopTransaction[]> {
  const res = await apiClient.get<WorkshopTransaction[]>('/workshop/transactions', {
    params: { skip, limit },
  })
  return res.data
}
