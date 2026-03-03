/** Operator Terminal API */

import { apiClient } from './client'
import type {
  ActiveJob,
  NormDetailRow,
  NormPeriod,
  NormSummary,
  OperatorStats,
  OperatorWorkcenter,
  TransactionAlert,
} from '@/types/operator'

/** Aktivní (rozběhnuté) práce operátora */
export async function getActiveJobs(): Promise<ActiveJob[]> {
  const { data } = await apiClient.get<ActiveJob[]>('/operator/active-jobs')
  return data
}

/** Statistiky operátora (dnešní/týdenní/měsíční) */
export async function getStats(): Promise<OperatorStats> {
  const { data } = await apiClient.get<OperatorStats>('/operator/stats')
  return data
}

/** Dostupná pracoviště s počtem operací */
export async function getWorkcenters(): Promise<OperatorWorkcenter[]> {
  const { data } = await apiClient.get<OperatorWorkcenter[]>('/operator/workcenters')
  return data
}

/** Nevyřešené transakce (pending/posting/failed) */
export async function getTransactionAlerts(limit = 30): Promise<TransactionAlert[]> {
  const { data } = await apiClient.get<TransactionAlert[]>('/operator/transaction-alerts', {
    params: { limit },
  })
  return data
}

/** Retry odeslání transakce do Inforu */
export async function retryTransaction(txId: number) {
  const { data } = await apiClient.post(`/workshop/transactions/${txId}/post`)
  return data
}

export interface NormQueryParams {
  period?: NormPeriod
  date_from?: string  // YYYY-MM-DD
  date_to?: string    // YYYY-MM-DD
}

/** Agregované plnění norem (pro dashboard dlaždice) */
export async function getNormSummary(params: NormQueryParams = {}): Promise<NormSummary> {
  const { data } = await apiClient.get<NormSummary>('/operator/norm-summary', { params })
  return data
}

/** Per-operace detail plnění norem (pro drill-down) */
export async function getNormDetails(params: NormQueryParams = {}): Promise<NormDetailRow[]> {
  const { data } = await apiClient.get<NormDetailRow[]>('/operator/norm-details', { params })
  return data
}
