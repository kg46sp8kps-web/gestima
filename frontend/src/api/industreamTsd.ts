/**
 * Industream TSD — API client.
 *
 * Clean START/END pairing with machine transactions (2.har verified).
 */

import { apiClient } from './client'

export interface TsdStartRequest {
  job: string
  suffix?: string
  oper_num: string
  wc?: string
  item?: string
  whse?: string
}

export interface TsdEndWorkRequest extends TsdStartRequest {
  qty_complete?: number
  qty_scrapped?: number
  oper_complete?: boolean
  job_complete?: boolean
}

export interface TsdResponse {
  status: string
  message: string
  actual_hours?: number
  stroj?: string
  wc?: string
}

const BASE = '/industream-tsd'

/** Start Setup — WrapperSp(TT=1) + local tx */
export async function startSetup(req: TsdStartRequest): Promise<TsdResponse> {
  const { data } = await apiClient.post<TsdResponse>(`${BASE}/start-setup`, req)
  return data
}

/** End Setup + auto-Start Work — WrapperSp(TT=2) → full start_work flow */
export async function endSetup(req: TsdStartRequest): Promise<TsdResponse> {
  const { data } = await apiClient.post<TsdResponse>(`${BASE}/end-setup`, req)
  return data
}

/** Start Work — ValidateMachine + Wrapper(TT=3) + Kapacity + Mchtrx */
export async function startWork(req: TsdStartRequest): Promise<TsdResponse> {
  const { data } = await apiClient.post<TsdResponse>(`${BASE}/start-work`, req)
  return data
}

/** End Work — InsWrapper(TT=4) + Kapacity + MachineVal + DcSfcMchtrx */
export async function endWork(req: TsdEndWorkRequest): Promise<TsdResponse> {
  const { data } = await apiClient.post<TsdResponse>(`${BASE}/end-work`, req)
  return data
}
