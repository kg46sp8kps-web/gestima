/** Operator Terminal API */

import { apiClient } from './client'
import type { ActiveJob, OperatorStats, OperatorWorkcenter, TransactionAlert } from '@/types/operator'

/** Aktivní (rozběhnuté) práce operátora */
export async function getActiveJobs(): Promise<ActiveJob[]> {
  const { data } = await apiClient.get<ActiveJob[]>('/operator/active-jobs')
  return data
}

/** Statistiky operátora (dnešní/týdenní) */
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
