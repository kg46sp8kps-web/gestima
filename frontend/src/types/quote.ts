/**
 * Quote types - matching backend Quote and QuoteItem models
 */

/**
 * Quote status - matches backend QuoteStatus enum
 */
export type QuoteStatus = 'draft' | 'sent' | 'approved' | 'rejected'

/**
 * Base Quote interface
 */
export interface Quote {
  id: number
  quote_number: string
  partner_id: number | null
  title: string
  description: string
  status: QuoteStatus
  valid_until: string | null
  sent_at: string | null
  approved_at: string | null
  rejected_at: string | null
  subtotal: number
  discount_percent: number
  discount_amount: number
  tax_percent: number
  tax_amount: number
  total: number
  currency: string
  version: number
  created_at: string
  updated_at: string
}

/**
 * Quote item (line item)
 */
export interface QuoteItem {
  id: number
  quote_id: number
  seq: number
  part_id: number | null
  part_number: string
  part_name: string
  quantity: number
  unit_price: number
  line_total: number
  notes: string
  version: number
}

/**
 * Quote with items and partner (from /quotes/{quote_number} detail)
 */
export interface QuoteWithItems extends Quote {
  items: QuoteItem[]
  partner?: {
    partner_number: string
    company_name: string
  }
}

/**
 * Create new quote payload
 */
export interface QuoteCreate {
  partner_id?: number | null
  title: string
  description?: string
  valid_until?: string | null
  discount_percent?: number
  tax_percent?: number
}

/**
 * Update existing quote payload (DRAFT only)
 */
export interface QuoteUpdate {
  partner_id?: number | null
  title?: string
  description?: string
  valid_until?: string | null
  discount_percent?: number
  tax_percent?: number
  version: number
}

/**
 * Create new quote item payload
 */
export interface QuoteItemCreate {
  part_id: number
  quantity: number
  unit_price?: number // Optional - auto-loaded from frozen batch
  notes?: string
}

/**
 * Update existing quote item payload
 */
export interface QuoteItemUpdate {
  quantity?: number
  unit_price?: number
  notes?: string
  version: number
}

/**
 * Quote list response (from /quotes)
 */
export interface QuotesListResponse {
  quotes: Quote[]
  total: number
  skip: number
  limit: number
}
