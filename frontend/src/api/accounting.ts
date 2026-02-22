import { apiClient } from './client'
import type { DashboardOverview } from '@/types/accounting'

export async function getDashboardOverview(rok: number): Promise<DashboardOverview> {
  const { data } = await apiClient.get<DashboardOverview>('/accounting/dashboard/overview', {
    params: { rok },
  })
  return data
}
