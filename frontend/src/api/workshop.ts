/** Gestima Dílna — API modul */

import { apiClient } from './client'
import type { AxiosRequestConfig } from 'axios'
import type {
  WorkshopJob,
  WorkshopQueueItem,
  MachinePlanItem,
  WorkshopOperation,
  WorkshopMaterial,
  WorkshopMaterialIssueCreate,
  WorkshopMaterialIssueResult,
  WorkshopQueueSortBy,
  WorkshopOperationSortBy,
  WorkshopMaterialSortBy,
  WorkshopSortDir,
  WorkshopTransaction,
  WorkshopTransactionCreate,
  WorkshopOrderOverviewRow,
} from '@/types/workshop'

// ─── ETag cache (If-None-Match / 304 support) ─────────────────────────
const etagCache: Record<string, { etag: string; data: unknown }> = {}

/**
 * GET s ETag support: pošle If-None-Match, při 304 vrátí cached data.
 * `cacheKey` identifikuje endpoint (bez query params — ty se mění).
 */
async function getWithEtag<T>(url: string, config?: AxiosRequestConfig, cacheKey?: string): Promise<T> {
  const key = cacheKey ?? url
  const cached = etagCache[key]
  const headers: Record<string, string> = {}
  if (cached?.etag) {
    headers['If-None-Match'] = cached.etag
  }
  try {
    const res = await apiClient.get<T>(url, { ...config, headers: { ...config?.headers, ...headers } })
    const newEtag = res.headers?.['etag'] as string | undefined
    if (newEtag) {
      etagCache[key] = { etag: newEtag, data: res.data }
    }
    return res.data
  } catch (err: unknown) {
    const axiosErr = err as { response?: { status?: number } }
    if (axiosErr?.response?.status === 304 && cached) {
      return cached.data as T
    }
    throw err
  }
}

/** Načte frontu práce pro pracoviště — flat seznam operací (bez deduplikace) */
export async function getWcQueue(
  opts?: {
    wc?: string
    job?: string
    sort_by?: WorkshopQueueSortBy
    sort_dir?: WorkshopSortDir
    limit?: number
  },
): Promise<WorkshopQueueItem[]> {
  const params: Record<string, string | number> = {
    limit: opts?.limit ?? 200,
    sort_by: opts?.sort_by ?? 'OpDatumSt',
    sort_dir: opts?.sort_dir ?? 'asc',
  }
  if (opts?.wc) params.wc = opts.wc
  if (opts?.job) params.job = opts.job
  return getWithEtag<WorkshopQueueItem[]>('/workshop/queue', { params }, 'wc_queue')
}

/** Plán stroje — operace včetně zásobníku (R/F/S/W) */
export async function getMachinePlan(
  opts?: {
    wc?: string
    job?: string
    sort_by?: WorkshopQueueSortBy
    sort_dir?: WorkshopSortDir
    limit?: number
  },
): Promise<MachinePlanItem[]> {
  const params: Record<string, string | number> = {
    limit: opts?.limit ?? 500,
    sort_by: opts?.sort_by ?? 'OpDatumSt',
    sort_dir: opts?.sort_dir ?? 'asc',
  }
  if (opts?.wc) params.wc = opts.wc
  if (opts?.job) params.job = opts.job
  return getWithEtag<MachinePlanItem[]>('/workshop/machine-plan', { params }, 'machine_plan')
}

/** Načte otevřené výrobní zakázky z Inforu (Type=J, JobStat=R) */
export async function getOpenJobs(wc?: string, limit = 500): Promise<WorkshopJob[]> {
  const params: Record<string, string | number> = { limit }
  if (wc) params.wc = wc
  const res = await apiClient.get<WorkshopJob[]>('/workshop/jobs', { params })
  return res.data
}

/** Načte operace konkrétní zakázky (SLJobRoutes per-job) */
export async function getJobOperations(
  job: string,
  suffix = '0',
  sortBy: WorkshopOperationSortBy = 'OpDatumSt',
  sortDir: WorkshopSortDir = 'asc',
): Promise<WorkshopOperation[]> {
  // job je query param (ne path) — Infor job čísla mohou obsahovat lomítka
  const res = await apiClient.get<WorkshopOperation[]>('/workshop/operations', {
    params: { job, suffix, sort_by: sortBy, sort_dir: sortDir },
  })
  return res.data
}

/** Načte materiálovou spotřebu k operaci (IteCzTsdSLJobMatls) */
export async function getOperationMaterials(
  job: string,
  oper: string,
  suffix = '0',
  sortBy: WorkshopMaterialSortBy = 'Material',
  sortDir: WorkshopSortDir = 'asc',
): Promise<WorkshopMaterial[]> {
  // job a oper jsou query params — Infor job čísla mohou obsahovat lomítka
  const res = await apiClient.get<WorkshopMaterial[]>('/workshop/materials', {
    params: { job, oper, suffix, sort_by: sortBy, sort_dir: sortDir },
  })
  return res.data
}

export async function postMaterialIssue(data: WorkshopMaterialIssueCreate): Promise<WorkshopMaterialIssueResult> {
  const res = await apiClient.post<WorkshopMaterialIssueResult>('/workshop/material-issues', data)
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

/** Načte přehled zakázek pro dispečink (zakázka + VP + operace). */
export async function getOrdersOverview(opts?: {
  customer?: string
  due_from?: string
  due_to?: string
  search?: string
  limit?: number
}): Promise<WorkshopOrderOverviewRow[]> {
  const params: Record<string, string | number | boolean> = {
    limit: opts?.limit ?? 2000,
  }
  if (opts?.customer) params.customer = opts.customer
  if (opts?.due_from) params.due_from = opts.due_from
  if (opts?.due_to) params.due_to = opts.due_to
  if (opts?.search) params.search = opts.search
  return getWithEtag<WorkshopOrderOverviewRow[]>('/workshop/orders-overview', { params }, 'orders_overview')
}
