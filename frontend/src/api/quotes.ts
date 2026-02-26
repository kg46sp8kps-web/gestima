import { apiClient } from './client'
import type { QuoteListItem, QuoteDetail } from '@/types/quote'

interface QuoteCreatePayload {
  title?: string
  description?: string
  customer_request_number?: string
  request_date?: string
  offer_deadline?: string
  valid_until?: string
  delivery_terms?: string
  discount_percent?: number
  tax_percent?: number
  notes?: string
}

interface QuoteUpdatePayload {
  partner_id?: number
  title?: string
  description?: string
  customer_request_number?: string
  request_date?: string
  offer_deadline?: string
  valid_until?: string
  delivery_terms?: string
  discount_percent?: number
  tax_percent?: number
  notes?: string
  version: number
}

export async function getAll(status?: string): Promise<QuoteListItem[]> {
  const { data } = await apiClient.get<QuoteListItem[]>('/quotes/', {
    params: status ? { status } : undefined,
  })
  return data
}

export async function getDetail(quoteNumber: string): Promise<QuoteDetail> {
  const { data } = await apiClient.get<QuoteDetail>(`/quotes/${quoteNumber}`)
  return data
}

export async function create(payload: QuoteCreatePayload): Promise<QuoteDetail> {
  const { data } = await apiClient.post<QuoteDetail>('/quotes/', payload)
  return data
}

export async function update(quoteNumber: string, payload: QuoteUpdatePayload): Promise<QuoteDetail> {
  const { data } = await apiClient.put<QuoteDetail>(`/quotes/${quoteNumber}`, payload)
  return data
}

export async function sendQuote(quoteNumber: string): Promise<QuoteDetail> {
  const { data } = await apiClient.post<QuoteDetail>(`/quotes/${quoteNumber}/send`)
  return data
}

export async function approveQuote(quoteNumber: string): Promise<QuoteDetail> {
  const { data } = await apiClient.post<QuoteDetail>(`/quotes/${quoteNumber}/approve`)
  return data
}

export async function rejectQuote(quoteNumber: string): Promise<QuoteDetail> {
  const { data } = await apiClient.post<QuoteDetail>(`/quotes/${quoteNumber}/reject`)
  return data
}

export async function cloneQuote(quoteNumber: string): Promise<QuoteDetail> {
  const { data } = await apiClient.post<QuoteDetail>(`/quotes/${quoteNumber}/clone`)
  return data
}

export async function deleteQuote(quoteNumber: string): Promise<void> {
  await apiClient.delete(`/quotes/${quoteNumber}`)
}

export async function addItem(
  quoteNumber: string,
  partId: number,
  quantity: number,
  notes?: string,
): Promise<void> {
  await apiClient.post(`/quotes/${quoteNumber}/items`, { part_id: partId, quantity, notes })
}

export async function removeItem(itemId: number): Promise<void> {
  await apiClient.delete(`/quote_items/${itemId}`)
}

export async function downloadPdf(quoteNumber: string): Promise<void> {
  const response = await apiClient.get(`/quotes/${quoteNumber}/pdf`, {
    responseType: 'blob',
  })
  const url = URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `nabidka-${quoteNumber}.pdf`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
