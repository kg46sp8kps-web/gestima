/**
 * TSD Mongoose — API client.
 *
 * Session-based TSD reporting via Mongoose/IPS protocol.
 * Reuses TsdFiddler request/response types (same Infor SP interface).
 */

import { apiClient } from './client'
import type { TsdFiddlerStartRequest, TsdFiddlerEndWorkRequest, TsdFiddlerResponse } from './tsdFiddler'

const BASE = '/tsd'

/** Start Setup — WrapperSp(TT=1) via IPS session */
export async function startSetup(req: TsdFiddlerStartRequest): Promise<TsdFiddlerResponse> {
  const { data } = await apiClient.post<TsdFiddlerResponse>(`${BASE}/start-setup`, req)
  return data
}

/** End Setup + auto-Start Work — WrapperSp(TT=2) + start_work via IPS session */
export async function endSetup(req: TsdFiddlerStartRequest): Promise<TsdFiddlerResponse> {
  const { data } = await apiClient.post<TsdFiddlerResponse>(`${BASE}/end-setup`, req)
  return data
}

/** Start Work — ValidateMachine + Wrapper(TT=3) + Kapacity + Mchtrx(H) */
export async function startWork(req: TsdFiddlerStartRequest): Promise<TsdFiddlerResponse> {
  const { data } = await apiClient.post<TsdFiddlerResponse>(`${BASE}/start-work`, req)
  return data
}

/** End Work — InsWrapper(TT=4) + Kapacity + MachineVal + DcSfcMchtrx(J) */
export async function endWork(req: TsdFiddlerEndWorkRequest): Promise<TsdFiddlerResponse> {
  const { data } = await apiClient.post<TsdFiddlerResponse>(`${BASE}/end-work`, req)
  return data
}
