import { apiClient } from './client'
import type {
  BalancePivotResponse,
  TurnoverResponse,
  DashboardOverviewResponse,
  DashboardCostsResponse,
  DashboardMachinesResponse,
  DashboardRevenueResponse,
  DashboardBalanceSheetResponse,
} from '@/types/accounting'

export async function getAccountingBalances(rok: number = 2026): Promise<BalancePivotResponse> {
  const response = await apiClient.get<BalancePivotResponse>('/accounting/balances', {
    params: { rok },
  })
  return response.data
}

export async function getAccountingTurnovers(rok: number = 2026): Promise<TurnoverResponse> {
  const response = await apiClient.get<TurnoverResponse>('/accounting/turnovers', {
    params: { rok },
  })
  return response.data
}

export async function refreshAccountingCache(rok: number = 2026): Promise<void> {
  await apiClient.post('/accounting/refresh', null, { params: { rok } })
}

// Dashboard aggregation endpoints
export async function getDashboardOverview(rok: number): Promise<DashboardOverviewResponse> {
  const response = await apiClient.get<DashboardOverviewResponse>('/accounting/dashboard/overview', { params: { rok } })
  return response.data
}

export async function getDashboardCosts(rok: number): Promise<DashboardCostsResponse> {
  const response = await apiClient.get<DashboardCostsResponse>('/accounting/dashboard/costs', { params: { rok } })
  return response.data
}

export async function getDashboardMachines(rok: number): Promise<DashboardMachinesResponse> {
  const response = await apiClient.get<DashboardMachinesResponse>('/accounting/dashboard/machines', { params: { rok } })
  return response.data
}

export async function getDashboardRevenue(rok: number): Promise<DashboardRevenueResponse> {
  const response = await apiClient.get<DashboardRevenueResponse>('/accounting/dashboard/revenue', { params: { rok } })
  return response.data
}

export async function getDashboardBalanceSheet(rok: number): Promise<DashboardBalanceSheetResponse> {
  const response = await apiClient.get<DashboardBalanceSheetResponse>('/accounting/dashboard/balance-sheet', { params: { rok } })
  return response.data
}
