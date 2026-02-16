import { apiClient } from './client'
import type { PurchasePriceAnalysisResponse, ApplyPriceRequest, ApplyPriceResponse, ApplyBoundariesRequest } from '@/types/purchase-prices'

export async function getPurchasePrices(yearFrom: number = 2024, yearTo?: number): Promise<PurchasePriceAnalysisResponse> {
  const response = await apiClient.get<PurchasePriceAnalysisResponse>('/infor/purchase-prices', {
    params: { year_from: yearFrom, year_to: yearTo ?? yearFrom }
  })
  return response.data
}

export async function applyPurchasePrices(updates: ApplyPriceRequest[]): Promise<ApplyPriceResponse> {
  const response = await apiClient.post<ApplyPriceResponse>('/infor/purchase-prices/apply', { updates })
  return response.data
}

export async function applyBoundaries(data: ApplyBoundariesRequest): Promise<ApplyPriceResponse> {
  const response = await apiClient.post<ApplyPriceResponse>('/infor/purchase-prices/apply-boundaries', data)
  return response.data
}

export async function refreshPurchasePriceCache(yearFrom: number = 2024): Promise<void> {
  await apiClient.post('/infor/purchase-prices/refresh', null, {
    params: { year_from: yearFrom }
  })
}
