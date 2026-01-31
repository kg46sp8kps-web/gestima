/**
 * Quotes API - All quote-related endpoints
 */

import { apiClient } from './client'
import type {
  Quote,
  QuoteWithItems,
  QuoteCreate,
  QuoteUpdate,
  QuoteItemCreate,
  QuoteItemUpdate,
  QuotesListResponse,
  QuoteStatus
} from '@/types/quote'

/**
 * Get all quotes with pagination and optional status filter
 * NOTE: Backend returns Quote[] directly, not { quotes, total }
 */
export async function getQuotes(
  skip = 0,
  limit = 100,
  status?: QuoteStatus
): Promise<QuotesListResponse> {
  const params: any = { skip, limit }
  if (status) params.status = status

  const response = await apiClient.get<Quote[]>('/quotes/', { params })

  // Backend returns array directly, transform to expected format
  return {
    quotes: response.data,
    total: response.data.length, // Note: no pagination from backend yet
    skip,
    limit
  }
}

/**
 * Get single quote by quote_number (with items and partner)
 */
export async function getQuote(quoteNumber: string): Promise<QuoteWithItems> {
  const response = await apiClient.get<QuoteWithItems>(`/quotes/${quoteNumber}`)
  return response.data
}

/**
 * Create new quote
 */
export async function createQuote(data: QuoteCreate): Promise<Quote> {
  const response = await apiClient.post<Quote>('/quotes/', data)
  return response.data
}

/**
 * Update existing quote (DRAFT only - backend validates)
 */
export async function updateQuote(
  quoteNumber: string,
  data: QuoteUpdate
): Promise<Quote> {
  const response = await apiClient.put<Quote>(`/quotes/${quoteNumber}`, data)
  return response.data
}

/**
 * Delete quote
 */
export async function deleteQuote(quoteNumber: string): Promise<void> {
  await apiClient.delete(`/quotes/${quoteNumber}`)
}

// ============================================================================
// WORKFLOW ACTIONS
// ============================================================================

/**
 * Send quote (DRAFT -> SENT)
 */
export async function sendQuote(
  quoteNumber: string
): Promise<{ message: string; version: number }> {
  const response = await apiClient.post<{ message: string; version: number }>(
    `/quotes/${quoteNumber}/send`
  )
  return response.data
}

/**
 * Approve quote (SENT -> APPROVED)
 */
export async function approveQuote(
  quoteNumber: string
): Promise<{ message: string; version: number }> {
  const response = await apiClient.post<{ message: string; version: number }>(
    `/quotes/${quoteNumber}/approve`
  )
  return response.data
}

/**
 * Reject quote (SENT -> REJECTED)
 */
export async function rejectQuote(
  quoteNumber: string
): Promise<{ message: string; version: number }> {
  const response = await apiClient.post<{ message: string; version: number }>(
    `/quotes/${quoteNumber}/reject`
  )
  return response.data
}

/**
 * Clone quote (create copy as new DRAFT)
 */
export async function cloneQuote(quoteNumber: string): Promise<Quote> {
  const response = await apiClient.post<Quote>(`/quotes/${quoteNumber}/clone`)
  return response.data
}

// ============================================================================
// QUOTE ITEMS
// ============================================================================

/**
 * Add item to quote (auto-recalcs totals)
 */
export async function addQuoteItem(
  quoteNumber: string,
  data: QuoteItemCreate
): Promise<{ message: string; item_id: number; version: number }> {
  const response = await apiClient.post<{
    message: string
    item_id: number
    version: number
  }>(`/quotes/${quoteNumber}/items`, data)
  return response.data
}

/**
 * Update quote item (auto-recalcs totals)
 */
export async function updateQuoteItem(
  itemId: number,
  data: QuoteItemUpdate
): Promise<{ message: string; version: number }> {
  const response = await apiClient.put<{ message: string; version: number }>(
    `/quote_items/${itemId}`,
    data
  )
  return response.data
}

/**
 * Delete quote item (auto-recalcs totals)
 */
export async function deleteQuoteItem(
  itemId: number
): Promise<{ message: string; version: number }> {
  const response = await apiClient.delete<{ message: string; version: number }>(
    `/quote_items/${itemId}`
  )
  return response.data
}
