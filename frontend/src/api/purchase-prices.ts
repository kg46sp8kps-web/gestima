/**
 * Infor Purchase Price Analysis API Client
 *
 * API endpoints for analyzing purchase prices from Infor SLPoItems,
 * applying prices to PriceTiers, and managing tier boundaries.
 */

import { apiClient } from './client'
import type {
  PurchasePriceAnalysisResponse,
  ApplyPriceRequest,
  ApplyPriceResponse,
  ApplyBoundariesRequest,
} from '@/types/purchase-prices'

export async function getPurchasePrices(
  yearFrom: number,
  yearTo?: number,
): Promise<PurchasePriceAnalysisResponse> {
  const params: Record<string, number> = { year_from: yearFrom }
  if (yearTo !== undefined) params.year_to = yearTo
  const { data } = await apiClient.get<PurchasePriceAnalysisResponse>(
    '/infor/purchase-prices',
    { params },
  )
  return data
}

export async function applyPurchasePrices(
  updates: ApplyPriceRequest[],
): Promise<ApplyPriceResponse> {
  const { data } = await apiClient.post<ApplyPriceResponse>(
    '/infor/purchase-prices/apply',
    { updates },
  )
  return data
}

export async function refreshPurchasePriceCache(yearFrom: number): Promise<void> {
  await apiClient.post('/infor/purchase-prices/refresh', null, {
    params: { year_from: yearFrom },
  })
}

export async function applyBoundaries(
  payload: ApplyBoundariesRequest,
): Promise<ApplyPriceResponse> {
  const { data } = await apiClient.post<ApplyPriceResponse>(
    '/infor/purchase-prices/apply-boundaries',
    payload,
  )
  return data
}
