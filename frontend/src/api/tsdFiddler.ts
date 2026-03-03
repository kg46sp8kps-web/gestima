/**
 * TSD Fiddler — API client.
 *
 * Fiddler-verified START/END pairing with machine transactions.
 * Completely separate from old industream-tsd (Presunout flow).
 */

import { apiClient } from './client'

export interface TsdFiddlerStartRequest {
  job: string
  suffix?: string
  oper_num: string
  item?: string
  whse?: string
  kapacity_guid?: string
}

export interface TsdFiddlerEndWorkRequest extends TsdFiddlerStartRequest {
  qty_complete?: number
  qty_scrapped?: number
  oper_complete?: boolean
}

export interface TsdFiddlerResponse {
  status: string
  message: string
  stroj?: string | null
  wc?: string | null
  sp_results?: Record<string, unknown> | null
}

const BASE = '/tsd-fiddler'

/** Start Setup — Infor WrapperSp(TT=1) */
export async function startSetup(req: TsdFiddlerStartRequest): Promise<TsdFiddlerResponse> {
  const { data } = await apiClient.post<TsdFiddlerResponse>(`${BASE}/start-setup`, req)
  return data
}

/** End Setup + auto-Start Work — Infor InsWrapper(TT=2) + Kapacity + ValidateMachine + Wrapper(TT=3) + Mchtrx */
export async function endSetup(req: TsdFiddlerStartRequest): Promise<TsdFiddlerResponse> {
  const { data } = await apiClient.post<TsdFiddlerResponse>(`${BASE}/end-setup`, req)
  return data
}

/** Start Work — Infor ValidateMachine + Wrapper(TT=3) + Kapacity + Mchtrx(H) */
export async function startWork(req: TsdFiddlerStartRequest): Promise<TsdFiddlerResponse> {
  const { data } = await apiClient.post<TsdFiddlerResponse>(`${BASE}/start-work`, req)
  return data
}

/** End Work — Infor InsWrapper(TT=4) + Kapacity + MachineVal + DcSfcMchtrx(J) */
export async function endWork(req: TsdFiddlerEndWorkRequest): Promise<TsdFiddlerResponse> {
  const { data } = await apiClient.post<TsdFiddlerResponse>(`${BASE}/end-work`, req)
  return data
}
