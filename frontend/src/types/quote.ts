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
  request_date: string | null
  offer_deadline: string | null
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
  part_id: number | null
  part_number: string
  article_number?: string | null
  drawing_number?: string | null
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
  drawing_number: string | null
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

// ============================================================================
// V2: Quote From Request with Drawings + Technology (ADR-028 V2)
// ============================================================================

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
 * AI Vision analysis result for a single drawing PDF
 */
export interface DrawingAnalysis {
  filename: string
  drawing_number: string | null
  article_number: string | null
  material_hint: string | null
  dimensions_hint: string | null
  part_type: string // ROT / PRI / COMBINED
  complexity: string // simple / medium / complex
  estimated_time_min: number
  max_diameter_mm: number | null
  max_length_mm: number | null
  confidence: number
}

/**
 * Match between an uploaded drawing and a request item
 */
export interface DrawingMatch {
  drawing_index: number
  item_index: number | null
  match_method: string // ai_vision / filename / manual / none
  confidence: number
}

/**
 * Enhanced review data with drawing analysis (V2)
 */
export interface QuoteRequestReviewV2 {
  customer: CustomerMatch
  items: PartMatch[]
  customer_request_number: string | null
  request_date: string | null
  offer_deadline: string | null
  notes: string | null
  summary: {
    total_items: number
    unique_parts: number
    matched_parts: number
    new_parts: number
    missing_batches: number
  }
  drawing_analyses: DrawingAnalysis[]
  drawing_matches: DrawingMatch[]
}

/**
 * TimeVision estimation data carried from parse to create step
 */
export interface EstimationData {
  part_type: string
  complexity: string
  estimated_time_min: number
  max_diameter_mm: number | null
  max_length_mm: number | null
}

/**
 * Enhanced item for creating quote from request (V2)
 */
export interface QuoteFromRequestItemV2 {
  part_id: number | null
  article_number: string
  drawing_number: string | null
  name: string
  quantity: number
  notes: string | null
  drawing_index: number | null // index into drawing_files
  estimation: EstimationData | null
}

/**
 * V2: Create quote + parts + technology + batches from request
 */
export interface QuoteFromRequestCreateV2 {
  partner_id: number | null
  partner_data: PartnerCreateData | null
  items: QuoteFromRequestItemV2[]
  title: string
  customer_request_number: string | null
  request_date: string | null
  offer_deadline: string | null
  valid_until: string | null
  notes: string | null
  discount_percent: number
  tax_percent: number
}

/**
 * Result for a single part in quote creation
 */
export interface QuoteCreationPartResult {
  article_number: string
  part_number: string | null
  name: string
  is_new: boolean
  drawing_linked: boolean
  technology_generated: boolean
  batch_set_frozen: boolean
  unit_price: number
  warnings: string[]
}

/**
 * Complete result of quote-from-request V2 creation
 */
export interface QuoteCreationResult {
  quote_number: string
  quote_id: number
  partner_number: string | null
  partner_is_new: boolean
  parts: QuoteCreationPartResult[]
  parts_created: number
  parts_existing: number
  drawings_linked: number
  total_amount: number
  warnings: string[]
}
