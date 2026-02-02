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
  customer_request_number: string | null
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
  article_number?: string | null
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
  customer_request_number?: string | null
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
  customer_request_number?: string | null
  valid_until?: string | null
  discount_percent?: number
  tax_percent?: number
  version: number
}

/**
 * Create new quote item payload
 * Note: unit_price is auto-loaded from frozen batch (read-only)
 */
export interface QuoteItemCreate {
  part_id: number
  quantity: number
  notes?: string
}

/**
 * Update existing quote item payload
 * Note: unit_price is read-only (comes from frozen batch)
 */
export interface QuoteItemUpdate {
  quantity?: number
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

// ============================================================================
// AI QUOTE REQUEST PARSING (ADR-028)
// ============================================================================

/**
 * Customer extracted from PDF by AI
 */
export interface CustomerExtraction {
  company_name: string
  contact_person: string | null
  email: string | null
  phone: string | null
  ico: string | null
  confidence: number
}

/**
 * Single item extracted from PDF by AI
 */
export interface ItemExtraction {
  article_number: string
  drawing_number?: string | null
  name: string
  quantity: number
  notes: string | null
  confidence: number
}

/**
 * Complete AI extraction result from PDF
 */
export interface QuoteRequestExtraction {
  customer: CustomerExtraction
  items: ItemExtraction[]
  customer_request_number: string | null
  valid_until: string | null
  notes: string | null
}

/**
 * Customer match result (after DB lookup)
 */
export interface CustomerMatch {
  // Extracted data
  company_name: string
  contact_person: string | null
  email: string | null
  phone: string | null
  ico: string | null

  // Match results
  partner_id: number | null
  partner_number: string | null
  partner_exists: boolean
  match_confidence: number
}

/**
 * Batch match result for pricing
 */
export interface BatchMatch {
  batch_id: number | null
  batch_quantity: number | null
  status: 'exact' | 'lower' | 'missing'
  unit_price: number
  line_total: number
  warnings: string[]
}

/**
 * Part match result (part + batch combined)
 */
export interface PartMatch {
  // Part info
  part_id: number | null
  part_number: string | null
  part_exists: boolean

  // Extracted data
  article_number: string
  name: string
  quantity: number
  notes: string | null

  // Batch matching
  batch_match: BatchMatch | null
}

/**
 * Complete quote request review (for UI verification)
 */
export interface QuoteRequestReview {
  customer: CustomerMatch
  items: PartMatch[]
  customer_request_number: string | null
  valid_until: string | null
  notes: string | null
  summary: {
    total_items: number
    unique_parts: number
    matched_parts: number
    new_parts: number
    missing_batches: number
  }
}

/**
 * Partner data for new partner creation
 */
export interface PartnerCreateData {
  company_name: string
  contact_person?: string | null
  email?: string | null
  phone?: string | null
  ico?: string | null
  dic?: string | null
  is_customer: boolean
  is_supplier: boolean
}

/**
 * Item for quote creation from AI parsing
 */
export interface QuoteFromRequestItem {
  // If part exists
  part_id?: number | null

  // If part doesn't exist (AI will create it)
  article_number: string
  drawing_number?: string | null
  name: string

  // Common fields
  quantity: number
  notes?: string | null
}

/**
 * Create quote from AI-parsed request
 */
export interface QuoteFromRequestCreate {
  // Partner (existing or new)
  partner_id?: number | null
  partner_data?: PartnerCreateData

  // Quote fields
  title: string
  customer_request_number?: string | null
  valid_until?: string | null
  notes?: string | null
  discount_percent?: number
  tax_percent?: number

  // Items (parts + quantities)
  items: QuoteFromRequestItem[]
}
