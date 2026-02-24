/**
 * Infor Connection / Browser API Client
 *
 * API endpoints for testing connection, discovering IDOs, browsing IDO data.
 */

import { apiClient } from './client'
import type { InforIdoInfoResponse, InforIdoDataParams, InforIdoDataResponse } from '@/types/infor'

export async function testConnection(): Promise<Record<string, unknown>> {
  const { data } = await apiClient.get<Record<string, unknown>>('/infor/test-connection')
  return data
}

export async function discoverIdos(
  customNames?: string,
): Promise<{ found: string[]; not_found: string[] }> {
  const params = customNames ? { custom_names: customNames } : {}
  const { data } = await apiClient.get<{ found: string[]; not_found: string[] }>(
    '/infor/discover-idos',
    { params },
  )
  return data
}

export async function getIdoInfo(idoName: string): Promise<InforIdoInfoResponse> {
  const { data } = await apiClient.get<InforIdoInfoResponse>(`/infor/ido/${idoName}/info`)
  return data
}

export async function getIdoData(
  idoName: string,
  params: InforIdoDataParams,
): Promise<InforIdoDataResponse> {
  const { data } = await apiClient.get<InforIdoDataResponse>(`/infor/ido/${idoName}/data`, {
    params,
  })
  return data
}
